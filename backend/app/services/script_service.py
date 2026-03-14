import json
import logging
import uuid
from pathlib import Path

import httpx

from app.ai.gemini import GeminiService
from app.config import Settings
from app.models.script import (
    AvatarProfile,
    Scene,
    ScriptRequest,
    ScriptResponse,
    ScriptUpdateRequest,
    VideoScript,
)
from app.storage.local import LocalStorage

logger = logging.getLogger(__name__)


class ScriptService:
    def __init__(self, gemini: GeminiService, storage: LocalStorage, settings: Settings):
        self.gemini = gemini
        self.storage = storage
        self.settings = settings

    async def generate_script(self, request: ScriptRequest) -> ScriptResponse:
        """Generate a video script from product details and image.

        1. Generate unique run_id
        2. Load product image (local path or HTTP download)
        3. Save product image locally
        4. Call Gemini to generate script
        5. Parse into VideoScript model
        6. Save script.json
        7. Return ScriptResponse
        """
        run_id = request.run_id or uuid.uuid4().hex[:12]

        if self.settings.mock_ai_calls:
            import asyncio
            import shutil
            
            logger.info("SCRIPT GENERATION IN MOCK MODE")
            await asyncio.sleep(2)
            
            # Load product image details if possible
            samples_path = Path(self.settings.output_dir) / "samples" / "samples.json"
            product_image_url = str(request.image_url)
            product_name = request.product_name
            
            sample_source = None
            if samples_path.exists():
                with open(samples_path, "r") as f:
                    samples_data = json.load(f)
                    for s in samples_data:
                        if s["product_name"].lower() in product_name.lower():
                            product_image_url = s["image_url"]
                            # e.g. /output/samples/running_shoes.png -> samples/running_shoes.png
                            if "/output/" in product_image_url:
                                rel_path = product_image_url.split("/output/")[-1]
                                sample_source = self.storage.base_dir / rel_path
                            break

            # IMPORTANT: Physically save/copy product image to run directory so StoryboardService finds it
            if sample_source and sample_source.exists():
                dest_path = self.storage.get_path(run_id, "product_image.png")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(sample_source), str(dest_path))
                product_image_url = self.storage.to_url_path(str(dest_path))
            elif Path(str(request.image_url)).exists():
                # If they provided a local file, copy it
                ext = Path(str(request.image_url)).suffix.lstrip(".") or "png"
                dest_path = self.storage.get_path(run_id, f"product_image.{ext}")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(request.image_url), str(dest_path))
                product_image_url = self.storage.to_url_path(str(dest_path))

            scenes = [
                Scene(
                    scene_number=i + 1,
                    duration_seconds=8,
                    scene_type="ad",
                    shot_type="medium",
                    camera_movement="dolly",
                    lighting="cinematic",
                    visual_background="Studio",
                    avatar_action="talking",
                    avatar_emotion="excited",
                    product_visual_integration="close-up",
                    script_dialogue=f"Scene {i+1} dialogue for {product_name}",
                    sound_design="Background beat"
                ) for i in range(request.scene_count)
            ]
            script = VideoScript(
                video_title=f"Mock: {product_name}",
                avatar_profile=AvatarProfile(
                    gender="neutral", age_range="25-30", attire="business casual", 
                    tone_of_voice="friendly", visual_description="A modern AI spokesperson"
                ),
                scenes=scenes
            )
            
            return ScriptResponse(
                run_id=run_id,
                product_image_path=product_image_url,
                script=script,
            )

        image_url = str(request.image_url)

        # Load image bytes — local /output/ path or HTTP download
        if image_url.startswith("/output/"):
            local_path = Path(self.settings.output_dir).resolve() / image_url.removeprefix("/output/")
            image_bytes = local_path.read_bytes()
            ext = local_path.suffix.lstrip(".")
            if ext not in ("png", "jpg", "jpeg", "webp"):
                ext = "png"
        else:
            headers = {"User-Agent": "GenflowAdStudio/2.0"}
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=headers) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                image_bytes = resp.content

            content_type = resp.headers.get("content-type", "image/png")
            ext = "png"
            if "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif "webp" in content_type:
                ext = "webp"

        # Save product image
        product_image_path = self.storage.save_bytes(
            run_id=run_id,
            filename=f"product_image.{ext}",
            data=image_bytes,
        )

        # Compute target duration from scene count (Veo generates 8s clips)
        target_duration = request.scene_count * 8

        # Generate script via Gemini
        raw_script = await self.gemini.generate_script(
            product_name=request.product_name,
            specs=request.specifications,
            image_bytes=image_bytes,
            scene_count=request.scene_count,
            target_duration=target_duration,
            ad_tone=request.ad_tone,
            model_id=request.gemini_model,
            max_words=request.max_dialogue_words_per_scene,
            custom_instructions=request.custom_instructions,
            brand_dna=request.brand_dna.model_dump() if request.brand_dna else None,
        )

        # Parse into VideoScript model
        avatar_profile = AvatarProfile(**raw_script["avatar_profile"])
        scenes = [Scene(**s) for s in raw_script["scenes"]]
        script = VideoScript(
            video_title=raw_script["video_title"],
            total_duration=raw_script.get("total_duration", target_duration),
            avatar_profile=avatar_profile,
            scenes=scenes,
        )

        # Save script.json
        script_json = script.model_dump()
        self.storage.save_bytes(
            run_id=run_id,
            filename="script.json",
            data=json.dumps(script_json, indent=2).encode("utf-8"),
        )

        logger.info("Script generated for run_id=%s, title=%s", run_id, script.video_title)

        return ScriptResponse(
            run_id=run_id,
            product_image_path=self.storage.to_url_path(product_image_path),
            script=script,
        )

    async def update_script(self, run_id: str, script: VideoScript) -> ScriptResponse:
        """Persist an edited script back to disk."""
        script_json = script.model_dump()
        self.storage.save_bytes(
            run_id=run_id,
            filename="script.json",
            data=json.dumps(script_json, indent=2).encode("utf-8"),
        )
        logger.info("Script updated for run_id=%s", run_id)

        # Build path to product image — it was saved during generate_script
        run_dir = Path(self.settings.output_dir) / run_id
        product_image_path = ""
        for ext in ("png", "jpg", "webp"):
            candidate = run_dir / f"product_image.{ext}"
            if candidate.exists():
                product_image_path = self.storage.to_url_path(str(candidate))
                break

        return ScriptResponse(
            run_id=run_id,
            product_image_path=product_image_path,
            script=script,
        )
