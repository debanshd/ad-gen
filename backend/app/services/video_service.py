import asyncio
import logging
import random
import shutil
from pathlib import Path
from typing import Callable

from app.ai.prompts import VIDEO_PROMPT_TEMPLATE_IMAGE, VIDEO_PROMPT_TEMPLATE_REFERENCE
from app.ai.veo import VeoService
from app.config import Settings
from app.models.script import AvatarProfile, Scene
from app.models.storyboard import StoryboardResult
from app.models.qc import VideoQCReport
from app.models.video import VideoResponse, VideoResult, VideoVariant
from app.services.qc_service import QCService
from app.storage.gcs import GCSStorage
from app.storage.local import LocalStorage
from app.utils.ffmpeg import extract_last_frame

logger = logging.getLogger(__name__)


class VideoService:
    def __init__(
        self,
        veo: VeoService,
        gcs: GCSStorage,
        qc: QCService,
        storage: LocalStorage,
        settings: Settings,
    ):
        self.veo = veo
        self.gcs = gcs
        self.qc = qc
        self.storage = storage
        self.settings = settings

    async def generate_videos(
        self,
        run_id: str,
        scenes_data: list[StoryboardResult],
        script_scenes: list[Scene],
        avatar_profile: AvatarProfile,
        on_progress: Callable | None = None,
        num_variants: int | None = None,
        seed: int | None = None,
        resolution: str = "720p",
        veo_model: str | None = None,
        aspect_ratio: str = "9:16",
        duration_seconds: int = 8,
        compression_quality: str = "optimized",
        qc_threshold: int | None = None,
        max_qc_regen_attempts: int = 2,
        use_reference_images: bool = True,
        negative_prompt_extra: str = "",
        generate_audio: bool = True,
    ) -> VideoResponse:
        """Generate video variants for all scenes with QC and auto-selection."""
        if seed is None:
            seed = random.randint(0, 2**31)

        effective_variants = num_variants or self.settings.max_video_variants
        scene_lookup = {s.scene_number: s for s in script_scenes}
        sorted_scenes = sorted(scenes_data, key=lambda s: s.scene_number)
        results: list[VideoResult] = []
        prev_last_frame_gcs: str | None = None

        for sb_result in sorted_scenes:
            scene = scene_lookup[sb_result.scene_number]
            result = await self._process_single_scene(
                run_id=run_id,
                sb_result=sb_result,
                scene=scene,
                avatar_profile=avatar_profile,
                on_progress=on_progress,
                num_variants=effective_variants,
                seed=seed,
                resolution=resolution,
                veo_model=veo_model,
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                compression_quality=compression_quality,
                qc_threshold=qc_threshold,
                max_qc_regen_attempts=max_qc_regen_attempts,
                use_reference_images=use_reference_images,
                negative_prompt_extra=negative_prompt_extra,
                prev_scene_last_frame_gcs=prev_last_frame_gcs,
                generate_audio=generate_audio,
            )
            results.append(result)

            try:
                selected_video_local = str(self.storage.get_path(
                    run_id,
                    f"variant_{result.selected_index}.mp4",
                    subdir=f"scenes/scene_{sb_result.scene_number}/video_variants",
                ))
                last_frame_local = str(self.storage.get_path(
                    run_id,
                    "last_frame.png",
                    subdir=f"scenes/scene_{sb_result.scene_number}",
                ))
                if Path(selected_video_local).exists():
                    await extract_last_frame(selected_video_local, last_frame_local)
                
                # In mock mode, we skip the real GCS upload for the last frame
                if not self.settings.mock_ai_calls:
                    gcs_path = f"pipeline/{run_id}/scenes/scene_{sb_result.scene_number}/last_frame.png"
                    prev_last_frame_gcs = await asyncio.to_thread(self.gcs.upload_file, last_frame_local, gcs_path)
            except Exception as exc:
                logger.warning("Failed to extract last frame: %s", exc)
                prev_last_frame_gcs = None

        return VideoResponse(results=results)

    async def _process_single_scene(
        self,
        run_id: str,
        sb_result: StoryboardResult,
        scene: Scene,
        avatar_profile: AvatarProfile,
        on_progress: Callable | None,
        num_variants: int | None = None,
        seed: int | None = None,
        resolution: str = "720p",
        veo_model: str | None = None,
        aspect_ratio: str = "9:16",
        duration_seconds: int = 8,
        compression_quality: str = "optimized",
        qc_threshold: int | None = None,
        max_qc_regen_attempts: int = 2,
        use_reference_images: bool = True,
        negative_prompt_extra: str = "",
        prev_scene_last_frame_gcs: str | None = None,
        generate_audio: bool = True,
        previous_qc_report: VideoQCReport | None = None,
    ) -> VideoResult:
        """Process a single scene: mock bypass or real generation."""
        scene_num = sb_result.scene_number
        effective_variants = num_variants or self.settings.max_video_variants

        # Construct prompt early so it's available for QC (both mock and real)
        voice_style = scene.voice_style or avatar_profile.voice_style or avatar_profile.tone_of_voice
        detailed_desc = scene.detailed_avatar_description or avatar_profile.visual_description
        template = VIDEO_PROMPT_TEMPLATE_REFERENCE if use_reference_images else VIDEO_PROMPT_TEMPLATE_IMAGE
        prompt = template.format(
            detailed_avatar_description=detailed_desc,
            visual_background=scene.visual_background,
            lighting=scene.lighting,
            shot_type=scene.shot_type,
            avatar_action=scene.avatar_action,
            avatar_emotion=scene.avatar_emotion,
            camera_movement=scene.camera_movement,
            product_visual_integration=scene.product_visual_integration,
            voice_style=voice_style,
            script_dialogue=scene.script_dialogue,
            sound_design=scene.sound_design,
            audio_continuity=scene.audio_continuity or "",
        )

        if previous_qc_report:
            prompt = await self.qc.rewrite_video_prompt(prompt, previous_qc_report)

        if self.settings.mock_ai_calls:
            logger.info("VIDEO GENERATION IN MOCK MODE")
            await asyncio.sleep(5)
            
            mock_source = self.storage.base_dir / "6gp0s595xs8" / "scenes" / "scene_1" / "video_variants" / "variant_0.mp4"
            
            variants = []
            for i in range(effective_variants):
                lp = self.storage.get_path(run_id, f"variant_{i}.mp4", subdir=f"scenes/scene_{scene_num}/video_variants")
                lp.parent.mkdir(parents=True, exist_ok=True)
                if mock_source.exists():
                    shutil.copy2(str(mock_source), str(lp))
                variants.append(VideoVariant(index=i, video_path=self.storage.to_url_path(str(lp))))
            
            selected_lp = self.storage.get_path(run_id, "selected_video.mp4", subdir=f"scenes/scene_{scene_num}")
            if mock_source.exists():
                shutil.copy2(str(mock_source), str(selected_lp))
                
            qc_tasks = []
            import os
            use_debate = os.getenv("USE_AGENT_DEBATE") == "true"
            for i in range(len(variants)):
                if use_debate:
                    qc_tasks.append(self.qc.multi_agent_evaluate_video(
                        video_uri="gs://mock/video.mp4", 
                        reference_uri="gs://mock/image.png",
                        original_prompt=prompt
                    ))
                else:
                    qc_tasks.append(self.qc.qc_video(
                        video_uri="gs://mock/video.mp4", 
                        reference_uri="gs://mock/image.png"
                    ))
            
            qc_results = await asyncio.gather(*qc_tasks, return_exceptions=True)
            for i, result in enumerate(qc_results):
                if not isinstance(result, Exception):
                    variants[i].qc_report = result

            result = VideoResult(
                scene_number=scene_num,
                variants=variants,
                selected_index=0,
                selected_video_path=self.storage.to_url_path(str(selected_lp)),
                regen_attempts=0,
                prompt_used="Mock Prompt",
            )
            if on_progress:
                on_progress({"scene_number": scene_num, "event": "video_completed", "result": result.model_dump()})
            return result

        # --- REAL GENERATION ---
        storyboard_local = str(self.storage.get_path(run_id, "storyboard.png", subdir=f"scenes/scene_{scene_num}"))
        gcs_storyboard_path = f"pipeline/{run_id}/scenes/scene_{scene_num}/storyboard.png"
        product_filename = self._find_product_image(run_id)
        product_local = str(self.storage.get_path(run_id, product_filename))
        gcs_product_path = f"pipeline/{run_id}/product_image.png"
        avatar_local = str(self.storage.get_path(run_id, "avatar_selected.png"))
        gcs_avatar_path = f"pipeline/{run_id}/avatar_selected.png"

        storyboard_gcs_uri, product_gcs_uri, avatar_gcs_uri = await asyncio.gather(
            asyncio.to_thread(self.gcs.upload_file, storyboard_local, gcs_storyboard_path),
            asyncio.to_thread(self.gcs.upload_file, product_local, gcs_product_path),
            asyncio.to_thread(self.gcs.upload_file, avatar_local, gcs_avatar_path),
        )

        asset_image_uris = [avatar_gcs_uri, product_gcs_uri]
        if prev_scene_last_frame_gcs:
            asset_image_uris.append(prev_scene_last_frame_gcs)

        if previous_qc_report:
            # Note: already handled above, but keeping for real flow logic if needed or just skip
            pass

        scene_negative = scene.negative_elements or ""
        if negative_prompt_extra:
            scene_negative = f"{scene_negative}, {negative_prompt_extra}" if scene_negative else negative_prompt_extra

        output_gcs_uri = self.gcs.get_veo_output_uri(run_id) + f"scene_{scene_num}/"
        video_gcs_uris = await self.veo.generate_videos(
            prompt=prompt,
            reference_image_uri=storyboard_gcs_uri,
            output_gcs_uri=output_gcs_uri,
            num_variants=effective_variants,
            seed=seed,
            resolution=resolution,
            negative_prompt_extra=scene_negative,
            asset_image_uris=asset_image_uris,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            compression_quality=compression_quality,
            veo_model=veo_model,
            generate_audio=generate_audio,
        )

        local_paths = []
        for i in range(len(video_gcs_uris)):
            lp = self.storage.get_path(run_id, f"variant_{i}.mp4", subdir=f"scenes/scene_{scene_num}/video_variants")
            lp.parent.mkdir(parents=True, exist_ok=True)
            local_paths.append(lp)

        await asyncio.gather(*(asyncio.to_thread(self.gcs.download_to_local, uri, str(lp)) for uri, lp in zip(video_gcs_uris, local_paths)))
        variants = [VideoVariant(index=i, video_path=self.storage.to_url_path(str(lp))) for i, lp in enumerate(local_paths)]

        qc_tasks = []
        import os
        use_debate = os.getenv("USE_AGENT_DEBATE") == "true"
        for i in range(len(variants)):
            if use_debate:
                qc_tasks.append(self.qc.multi_agent_evaluate_video(
                    video_uri=video_gcs_uris[i], 
                    reference_uri=product_gcs_uri,
                    original_prompt=prompt
                ))
            else:
                qc_tasks.append(self.qc.qc_video(
                    video_uri=video_gcs_uris[i], 
                    reference_uri=product_gcs_uri
                ))
        
        qc_results = await asyncio.gather(*qc_tasks, return_exceptions=True)
        for i, result in enumerate(qc_results):
            if not isinstance(result, Exception):
                variants[i].qc_report = result

        selected_idx = self.qc.select_best_video_variant(variants)
        source_local = str(self.storage.get_path(run_id, f"variant_{selected_idx}.mp4", subdir=f"scenes/scene_{scene_num}/video_variants"))
        selected_path = self.storage.save_file(run_id=run_id, filename="selected_video.mp4", source_path=source_local, subdir=f"scenes/scene_{scene_num}")

        result = VideoResult(
            scene_number=scene_num,
            variants=variants,
            selected_index=selected_idx,
            selected_video_path=self.storage.to_url_path(selected_path),
            regen_attempts=0,
            prompt_used=prompt,
        )
        if on_progress:
            on_progress({"scene_number": scene_num, "event": "video_completed", "result": result.model_dump()})
        return result

    async def regenerate_single_scene(self, **kwargs) -> VideoResult:
        return await self._process_single_scene(**kwargs)

    async def select_variant(self, run_id: str, scene_number: int, variant_index: int) -> str:
        source_local = str(self.storage.get_path(run_id, f"variant_{variant_index}.mp4", subdir=f"scenes/scene_{scene_number}/video_variants"))
        selected_path = self.storage.save_file(run_id=run_id, filename="selected_video.mp4", source_path=source_local, subdir=f"scenes/scene_{scene_number}")
        return self.storage.to_url_path(selected_path)

    def _find_product_image(self, run_id: str) -> str:
        for ext in ("png", "jpg", "webp"):
            path = self.storage.get_path(run_id, f"product_image.{ext}")
            if path.exists():
                return f"product_image.{ext}"
        raise FileNotFoundError(f"No product image found for run {run_id}")
