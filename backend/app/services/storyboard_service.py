import asyncio
import logging
from typing import Callable

from app.ai.gemini_image import GeminiImageService
from app.ai.prompts import STORYBOARD_PROMPT_TEMPLATE
from app.config import Settings
from app.models.script import Scene
from app.models.storyboard import StoryboardResponse, StoryboardResult
from app.services.qc_service import QCService
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)


class StoryboardService:
    def __init__(
        self,
        gemini_image: GeminiImageService,
        qc: QCService,
        storage: LocalStorage,
        settings: Settings,
    ):
        self.gemini_image = gemini_image
        self.qc = qc
        self.storage = storage
        self.settings = settings

    async def generate_storyboard(
        self,
        run_id: str,
        scenes: list[Scene],
        on_progress: Callable | None = None,
        image_model: str | None = None,
        aspect_ratio: str = "9:16",
        qc_threshold: int | None = None,
        max_regen_attempts: int | None = None,
        include_composition_qc: bool = True,
        custom_prompts: dict[int, str] | None = None,
        image_size: str = "2K",
    ) -> StoryboardResponse:
        """Generate storyboard images for all scenes with QC feedback loop."""
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_scenes)

        async def process_scene(scene: Scene) -> StoryboardResult:
            async with semaphore:
                custom_prompt = (custom_prompts or {}).get(scene.scene_number)
                return await self._process_single_scene(
                    run_id,
                    scene,
                    len(scenes),
                    on_progress,
                    image_model=image_model,
                    aspect_ratio=aspect_ratio,
                    qc_threshold=qc_threshold,
                    max_regen_attempts=max_regen_attempts,
                    include_composition_qc=include_composition_qc,
                    custom_prompt=custom_prompt,
                    image_size=image_size,
                )

        tasks = [process_scene(scene) for scene in scenes]
        results = await asyncio.gather(*tasks)

        # Sort by scene_number
        sorted_results = sorted(results, key=lambda r: r.scene_number)

        return StoryboardResponse(results=sorted_results)

    async def _process_single_scene(
        self,
        run_id: str,
        scene: Scene,
        total_scenes: int,
        on_progress: Callable | None,
        image_model: str | None = None,
        aspect_ratio: str = "9:16",
        qc_threshold: int | None = None,
        max_regen_attempts: int | None = None,
        include_composition_qc: bool = True,
        custom_prompt: str | None = None,
        image_size: str = "2K",
    ) -> StoryboardResult:
        """Process a single scene with QC and regeneration loop."""
        if self.settings.mock_ai_calls:
            await asyncio.sleep(2)
            product_path = self._find_product_image(run_id)
            image_url = self.storage.to_url_path(str(self.storage.get_path(run_id, product_path)))
            
            # Save a placeholder
            self.storage.save_bytes(
                run_id=run_id,
                filename="storyboard.png",
                data=self.storage.load_bytes(run_id, product_path),
                subdir=f"scenes/scene_{scene.scene_number}",
            )

            # Enable multi-agent debate even in mock mode for demo "excitement"
            dummy_qc = await self.qc.mock_multi_agent_evaluate_storyboard(run_id)

            result = StoryboardResult(
                scene_number=scene.scene_number,
                image_path=image_url,
                qc_report=dummy_qc,
                regen_attempts=0,
                prompt_used="Mock Prompt",
            )
            if on_progress:
                on_progress({
                    "scene_number": scene.scene_number,
                    "event": "scene_completed",
                    "result": result.model_dump(),
                })
            return result

        effective_max_regen = max_regen_attempts if max_regen_attempts is not None else self.settings.max_regen_attempts

        # Load reference images
        avatar_bytes = self.storage.load_bytes(run_id, "avatar_selected.png")
        product_path = self._find_product_image(run_id)
        product_bytes = self.storage.load_bytes(run_id, product_path)

        # Build initial prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = STORYBOARD_PROMPT_TEMPLATE.format(
                scene_number=scene.scene_number,
                total_scenes=total_scenes,
                shot_type=scene.shot_type,
                camera_movement=scene.camera_movement,
                visual_background=scene.visual_background,
                lighting=scene.lighting,
                avatar_action=scene.avatar_action,
                avatar_emotion=scene.avatar_emotion,
                product_visual_integration=scene.product_visual_integration,
                aspect_ratio=aspect_ratio,
            )

        best_image_bytes: bytes | None = None
        best_qc_report = None
        best_prompt = prompt
        regen_attempts = 0

        for attempt in range(effective_max_regen + 1):
            image_bytes = await self.gemini_image.generate_storyboard_image(
                prompt=prompt,
                avatar_bytes=avatar_bytes,
                product_bytes=product_bytes,
                image_model=image_model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )

            qc_report = await self.qc.multi_agent_evaluate_storyboard(
                avatar_bytes=avatar_bytes,
                product_bytes=product_bytes,
                storyboard_bytes=image_bytes,
                original_prompt=prompt,
            )

            # Check if this attempt passes
            is_passing = self.qc.storyboard_passes_qc(
                qc_report,
                threshold=qc_threshold,
                include_composition=include_composition_qc,
            )

            # Update best if first attempt, better score, or it's a pass
            if (
                best_qc_report is None 
                or is_passing 
                or (
                    qc_report.avatar_validation.score + qc_report.product_validation.score
                    > best_qc_report.avatar_validation.score + best_qc_report.product_validation.score
                )
            ):
                best_image_bytes = image_bytes
                best_qc_report = qc_report
                best_prompt = prompt

            if is_passing:
                logger.info("Scene %d passed QC on attempt %d", scene.scene_number, attempt + 1)
                break

            if attempt < effective_max_regen:
                regen_attempts += 1
                logger.info("Scene %d failed QC, regenerating...", scene.scene_number)
                prompt = await self.qc.rewrite_prompt(prompt, qc_report)
                if on_progress:
                    on_progress({"scene_number": scene.scene_number, "event": "regen_attempt", "attempt": regen_attempts})

        image_path = self.storage.save_bytes(
            run_id=run_id,
            filename="storyboard.png",
            data=best_image_bytes,
            subdir=f"scenes/scene_{scene.scene_number}",
        )

        result = StoryboardResult(
            scene_number=scene.scene_number,
            image_path=self.storage.to_url_path(image_path),
            qc_report=best_qc_report,
            regen_attempts=regen_attempts,
            prompt_used=best_prompt,
        )

        if on_progress:
            on_progress({"scene_number": scene.scene_number, "event": "scene_completed", "result": result.model_dump()})

        return result

    async def regenerate_single_scene(self, **kwargs) -> StoryboardResult:
        return await self._process_single_scene(**kwargs)

    def _find_product_image(self, run_id: str) -> str:
        for ext in ("png", "jpg", "webp"):
            path = self.storage.get_path(run_id, f"product_image.{ext}")
            if path.exists():
                return f"product_image.{ext}"
        raise FileNotFoundError(f"No product image found for run {run_id}")
