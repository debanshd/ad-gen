import asyncio
import json
import os
import sys
import time
from pathlib import Path
from pydantic import ValidationError
from google import genai

# Add backend to path so we can import app
sys.path.append(str(Path(__file__).parent.parent))

from app.ai.gemini import GeminiService
from app.ai import prompts
from app.models.script import VideoScript
from app.models.qc import VideoQCReport
from app.models.brand import BrandDNA
from app.utils.json_parser import parse_json_response
from app.config import get_settings

async def evaluate_script_prompt(gemini_svc: GeminiService):
    print("\n--- Testing SCRIPT_USER_PROMPT_TEMPLATE ---")
    
    brand_dna = BrandDNA(
        tone_of_voice="Professional, innovative, and slightly futuristic",
        target_demographic="Tech-savvy professionals and entrepreneurs",
        core_messaging="Empowering productivity through seamless AI integration"
    )
    
    # Format the prompt with dummy data
    user_prompt = prompts.SCRIPT_USER_PROMPT_TEMPLATE.format(
        target_duration=30,
        product_name="AeroGlide Pro",
        specs="Lightweight, neon Volt green, ZoomX foam, carbon fiber plate",
        brand_dna=json.dumps(brand_dna.model_dump(), indent=2),
        ad_tone="High-energy cinematic",
        scene_count=3,
        narrative_arc=prompts.build_narrative_arc(3, 30),
        max_words=25
    )
    
    start_time = time.time()
    try:
        response = await gemini_svc.client.aio.models.generate_content(
            model=gemini_svc.settings.gemini_flash_model,
            contents=user_prompt,
            config={"system_instruction": prompts.SCRIPT_SYSTEM_INSTRUCTION}
        )
        latency = time.time() - start_time
        raw_text = response.text
        parsed = parse_json_response(raw_text)
        
        # Assert Pydantic model
        script = VideoScript(**parsed)
        print("🟢 PASS: Script generated and parsed successfully")
        return {"name": "Script Generation", "status": "PASS", "latency": latency, "type": "zero-shot"}
    except Exception as e:
        latency = time.time() - start_time
        print(f"🔴 FAIL: {str(e)}")
        return {"name": "Script Generation", "status": "FAIL", "latency": latency, "type": "zero-shot"}

async def evaluate_qc_prompts(gemini_svc: GeminiService):
    print("\n--- Testing QC Agents ---")
    results = []
    
    # 1. Director Agent
    print("Testing Director Agent...")
    start_time = time.time()
    try:
        response = await gemini_svc.client.aio.models.generate_content(
            model=gemini_svc.settings.gemini_flash_model,
            contents="Evaluate this video: [Video Description: A shoe is held steadily, but the fingers morph slightly near the end.]",
            config={"system_instruction": prompts.DIRECTOR_AGENT_INSTRUCTION}
        )
        latency = time.time() - start_time
        parsed = parse_json_response(response.text)
        assert "verdict" in parsed and "reasoning" in parsed
        print("🟢 PASS: Director Agent returned valid JSON verdict")
        results.append({"name": "Director QC", "status": "PASS", "latency": latency, "type": "multi-agent"})
    except Exception as e:
        latency = time.time() - start_time
        print(f"🔴 FAIL (Director): {str(e)}")
        results.append({"name": "Director QC", "status": "FAIL", "latency": latency, "type": "multi-agent"})

    # 2. Brand Agent
    print("Testing Brand Agent...")
    start_time = time.time()
    try:
        response = await gemini_svc.client.aio.models.generate_content(
            model=gemini_svc.settings.gemini_flash_model,
            contents="Evaluate this video: [Video Description: The Nike swoosh looks perfect, and the brand colors are accurate.]",
            config={"system_instruction": prompts.BRAND_AGENT_INSTRUCTION}
        )
        latency = time.time() - start_time
        parsed = parse_json_response(response.text)
        assert "verdict" in parsed and "reasoning" in parsed
        print("🟢 PASS: Brand Agent returned valid JSON verdict")
        results.append({"name": "Brand QC", "status": "PASS", "latency": latency, "type": "multi-agent"})
    except Exception as e:
        latency = time.time() - start_time
        print(f"🔴 FAIL (Brand): {str(e)}")
        results.append({"name": "Brand QC", "status": "FAIL", "latency": latency, "type": "multi-agent"})

    # 3. Orchestrator
    print("Testing Orchestrator...")
    start_time = time.time()
    try:
        orchestrator_prompt = (
            "Director Feedback: {'verdict': 'FAIL', 'reasoning': 'Hand distortion'}\n"
            "Brand Feedback: {'verdict': 'PASS', 'reasoning': 'Product looks good'}\n"
            "Finalize the VideoQCReport."
        )
        response = await gemini_svc.client.aio.models.generate_content(
            model=gemini_svc.settings.gemini_flash_model,
            contents=orchestrator_prompt,
            config={"system_instruction": prompts.ORCHESTRATOR_AGENT_INSTRUCTION}
        )
        latency = time.time() - start_time
        parsed = parse_json_response(response.text)
        # Assert VideoQCReport model
        report = VideoQCReport(**parsed)
        print("🟢 PASS: Orchestrator generated valid VideoQCReport")
        results.append({"name": "Orchestrator QC", "status": "PASS", "latency": latency, "type": "multi-agent"})
    except Exception as e:
        latency = time.time() - start_time
        print(f"🔴 FAIL (Orchestrator): {str(e)}")
        results.append({"name": "Orchestrator QC", "status": "FAIL", "latency": latency, "type": "multi-agent"})

    return results

def generate_markdown_report(all_results):
    total_tests = len(all_results)
    passes = len([r for r in all_results if r["status"] == "PASS"])
    prompt_adherence = (passes / total_tests) * 100
    
    zero_shot_tests = [r for r in all_results if r["type"] == "zero-shot"]
    zero_shot_passes = len([r for r in zero_shot_tests if r["status"] == "PASS"])
    zero_shot_rate = (zero_shot_passes / len(zero_shot_tests)) * 100 if zero_shot_tests else 0
    
    multi_agent_tests = [r for r in all_results if r["type"] == "multi-agent"]
    multi_agent_passes = len([r for r in multi_agent_tests if r["status"] == "PASS"])
    multi_agent_rate = (multi_agent_passes / len(multi_agent_tests)) * 100 if multi_agent_tests else 0
    
    avg_latency = sum([r["latency"] for r in all_results]) / total_tests
    
    table = [
        "# Prompt Reliability Evaluation Results (CAIS 2026)",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Prompt Adherence % | {prompt_adherence:.1f}% |",
        f"| Zero-Shot Pass Rate | {zero_shot_rate:.1f}% |",
        f"| Multi-Agent Pass Rate | {multi_agent_rate:.1f}% |",
        f"| Average Latency | {avg_latency:.2f}s |",
        "",
        "## Detailed Results",
        "",
        "| Agent / Prompt | Status | Latency | Type |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    for r in all_results:
        status_icon = "🟢 PASS" if r["status"] == "PASS" else "🔴 FAIL"
        table.append(f"| {r['name']} | {status_icon} | {r['latency']:.2f}s | {r['type']} |")
    
    filepath = Path(__file__).parent.parent.parent / "EVALUATION_RESULTS.md"
    filepath.write_text("\n".join(table))
    print(f"\n✅ Evaluation report generated at {filepath}")

async def main():
    print("🚀 Starting Prompt Reliability Evaluation...")
    
    settings = get_settings()
    client = genai.Client(
        vertexai=True,
        project=settings.project_id,
        location=settings.region,
    )
    gemini_svc = GeminiService(client=client, settings=settings)
    
    all_results = []
    
    script_result = await evaluate_script_prompt(gemini_svc)
    all_results.append(script_result)
    
    qc_results = await evaluate_qc_prompts(gemini_svc)
    all_results.extend(qc_results)
    
    generate_markdown_report(all_results)
    
    passes = len([r for r in all_results if r["status"] == "PASS"])
    if passes < len(all_results):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
