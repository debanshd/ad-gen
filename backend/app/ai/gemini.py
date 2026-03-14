import json
import logging

from google import genai
from google.genai import types

from app.ai.prompts import (
    PROMPT_REWRITE_TEMPLATE,
    SCRIPT_SYSTEM_INSTRUCTION,
    SCRIPT_USER_PROMPT_TEMPLATE,
    STORYBOARD_QC_SYSTEM_INSTRUCTION,
    STORYBOARD_QC_USER_PROMPT,
    VIDEO_QC_SYSTEM_INSTRUCTION,
    VIDEO_QC_USER_PROMPT,
    build_narrative_arc,
)
from app.ai.retry import async_retry
from app.config import Settings
from app.utils.json_parser import parse_json_response

logger = logging.getLogger(__name__)

ALL_SAFETY_OFF = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.OFF,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.OFF,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.OFF,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.OFF,
    ),
]


class GeminiService:
    def __init__(self, client: genai.Client, settings: Settings):
        self.client = client
        self.settings = settings

    @async_retry(retries=3)
    async def generate_script(
        self,
        product_name: str,
        specs: str,
        image_bytes: bytes,
        scene_count: int = 3,
        target_duration: int = 30,
        ad_tone: str = "energetic",
        model_id: str | None = None,
        max_words: int = 25,
        custom_instructions: str = "",
        brand_dna: dict | None = None,
    ) -> dict:
        """Generate video script using Gemini with structured JSON output.

        Args:
            model_id: Optional model override. Falls back to settings.gemini_model.
            max_words: Maximum dialogue words per scene.
        """
        user_prompt = SCRIPT_USER_PROMPT_TEMPLATE.format(
            product_name=product_name,
            specs=specs,
            scene_count=scene_count,
            target_duration=target_duration,
            narrative_arc=build_narrative_arc(scene_count, target_duration),
            ad_tone=ad_tone,
            max_words=max_words,
            brand_dna=json.dumps(brand_dna, indent=2) if brand_dna else "Standard commercial brand identity",
        )

        if custom_instructions:
            user_prompt += f"\n\nADDITIONAL CREATIVE DIRECTION FROM CLIENT:\n{custom_instructions}"

        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        text_part = types.Part.from_text(text=user_prompt)

        response = await self.client.aio.models.generate_content(
            model=model_id or self.settings.gemini_model,
            contents=[image_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=SCRIPT_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return parse_json_response(response.text)

    @async_retry(retries=3)
    async def extract_brand_dna(self, scraped_text: str) -> dict:
        """Extract BrandDNA (tone, demographic, messaging) from scraped text using Flash."""
        prompt = (
            "Analyze the following website text and extract the brand's DNA. "
            "Focus on their tone of voice, who they are targeting, and their core value proposition. "
            "Return ONLY valid JSON with no additional text.\n\n"
            "Text from website:\n"
            f"{scraped_text[:5000]}\n\n"
            "JSON Format:\n"
            '{"tone_of_voice": "e.g. bold, inspiring, technical", '
            '"target_demographic": "e.g. professional athletes, gen-z, corporate leaders", '
            '"core_messaging": "e.g. excellence through innovation, community-first streetwear"}'
        )

        text_part = types.Part.from_text(text=prompt)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[text_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=ALL_SAFETY_OFF,
                temperature=0.7,
            ),
        )

        return parse_json_response(response.text)

    @async_retry(retries=3)
    async def analyze_product_image(self, image_bytes: bytes) -> dict:
        """Extract product name and specifications from an image using Flash model."""
        prompt = (
            "Analyze this product image and extract the following information. "
            "Return ONLY valid JSON with no additional text.\n\n"
            '{"product_name": "The product name", '
            '"specifications": "Key specifications formatted as key: value lines"}'
        )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        text_part = types.Part.from_text(text=prompt)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[image_part, text_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=ALL_SAFETY_OFF,
                temperature=0.5,
            ),
        )

        return parse_json_response(response.text)

    @async_retry(retries=3)
    async def qc_storyboard(
        self,
        avatar_bytes: bytes,
        product_bytes: bytes,
        storyboard_bytes: bytes,
    ) -> dict:
        """QC storyboard using Gemini 3 Flash for faster evaluation."""
        avatar_part = types.Part.from_bytes(data=avatar_bytes, mime_type="image/png")
        product_part = types.Part.from_bytes(
            data=product_bytes, mime_type="image/png"
        )
        storyboard_part = types.Part.from_bytes(
            data=storyboard_bytes, mime_type="image/png"
        )
        text_part = types.Part.from_text(text=STORYBOARD_QC_USER_PROMPT)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[avatar_part, product_part, storyboard_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=STORYBOARD_QC_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return parse_json_response(response.text)

    @async_retry(retries=3)
    async def analyze_storyboard_with_instruction(
        self,
        avatar_bytes: bytes,
        product_bytes: bytes,
        storyboard_bytes: bytes,
        system_instruction: str,
        user_prompt: str,
    ) -> str:
        """Generic storyboard analysis with specific instructions (Multi-Agent)."""
        if self.settings.mock_ai_calls:
            import json
            if "Director" in system_instruction:
                return json.dumps({"verdict": "PASS", "reasoning": "The composition is visually striking, using professional lighting that highlights the subject well."})
            elif "Brand" in system_instruction:
                return json.dumps({"verdict": "FAIL", "reasoning": "The product label appears slightly distorted in the background, which could confuse customers."})
            else: # Orchestrator
                return json.dumps({
                    "avatar_validation": {"score": 92, "reason": "Avatar fidelity is high; matches reference perfectly."},
                    "product_validation": {"score": 65, "reason": "Product label distortion noted by Brand Manager requires correction."},
                    "composition_quality": {"score": 88, "reason": "Cinematic framing is excellent."},
                    "overall_verdict": "FAIL"
                })

        avatar_part = types.Part.from_bytes(data=avatar_bytes, mime_type="image/png")
        product_part = types.Part.from_bytes(data=product_bytes, mime_type="image/png")
        storyboard_part = types.Part.from_bytes(data=storyboard_bytes, mime_type="image/png")
        text_part = types.Part.from_text(text=user_prompt)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[avatar_part, product_part, storyboard_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return response.text.strip()

    @async_retry(retries=3)
    async def analyze_video_with_instruction(
        self, video_uri: str, system_instruction: str, user_prompt: str = "Evaluate this video content."
    ) -> str:
        """Analyze video using Gemini 3 Flash with a custom system instruction.
        
        Returns the raw text response (useful for agents sharing 'thoughts').
        """
        if self.settings.mock_ai_calls:
            import json
            # Simulate a disagreement: Director PASS, Brand FAIL (occasionally)
            if "DIRECTOR" in system_instruction:
                return json.dumps({
                    "verdict": "PASS",
                    "reasoning": "The motion is exceptionally fluid. Cinematic lighting remains stable with no flickering in the background."
                })
            elif "BRAND" in system_instruction:
                return json.dumps({
                    "verdict": "FAIL",
                    "reasoning": "The product logo on the shoe appears to warp slightly between seconds 2 and 4. This is a critical brand fidelity issue."
                })
            else: # Orchestrator
                return json.dumps({
                    "technical_distortion": {"score": 9, "reasoning": "Mock tech pass"},
                    "cinematic_imperfections": {"score": 8, "reasoning": "Mock cinematic pass"},
                    "avatar_consistency": {"score": 9, "reasoning": "Mock avatar pass"},
                    "product_consistency": {"score": 5, "reasoning": "Logo warping detected by Brand Manager"},
                    "temporal_coherence": {"score": 9, "reasoning": "Mock temporal pass"},
                    "hand_body_integrity": {"score": 8, "reasoning": "Mock hand pass"},
                    "brand_text_accuracy": {"score": 4, "reasoning": "Logo fidelity is compromised"},
                    "overall_verdict": "FAIL",
                    "revised_prompt": "Crystal clear, sharp product logo on the AeroGlide shoe, ultra-stable textures, high-fidelity branding."
                })

        video_part = types.Part.from_uri(
            file_uri=video_uri, mime_type="video/mp4"
        )
        text_part = types.Part.from_text(text=user_prompt)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[video_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return response.text.strip()

    @async_retry(retries=3)
    async def qc_video(
        self, video_uri: str, reference_image_uri: str
    ) -> dict:
        """QC video using Gemini 3 Flash.

        Accepts GCS URIs for the video and reference product image.
        """
        image_part = types.Part.from_uri(
            file_uri=reference_image_uri, mime_type="image/png"
        )
        video_part = types.Part.from_uri(
            file_uri=video_uri, mime_type="video/mp4"
        )
        text_part = types.Part.from_text(text=VIDEO_QC_USER_PROMPT)

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=[image_part, video_part, text_part],
            config=types.GenerateContentConfig(
                system_instruction=VIDEO_QC_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return parse_json_response(response.text)

    @async_retry(retries=3)
    async def rewrite_prompt(
        self, original_prompt: str, qc_feedback: str
    ) -> str:
        """Rewrite a generation prompt based on QC feedback using Gemini 3 Flash."""
        prompt_text = PROMPT_REWRITE_TEMPLATE.format(
            original_prompt=original_prompt,
            qc_feedback=qc_feedback,
        )

        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_flash_model,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                safety_settings=ALL_SAFETY_OFF,
                temperature=1.0,
            ),
        )

        return response.text.strip()
