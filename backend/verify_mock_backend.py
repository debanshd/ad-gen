import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path("/Users/debanshu/.gemini/jetski/playground/genflow-ad-studio/backend")
sys.path.append(str(backend_path))

from app.config import Settings
from app.models.script import ScriptRequest
from app.services.script_service import ScriptService
from app.services.avatar_service import AvatarService
from app.services.storyboard_service import StoryboardService
from app.services.video_service import VideoService
from app.services.stitch_service import StitchService
from app.storage.local import LocalStorage
from app.services.qc_service import QCService
from app.ai.gemini import GeminiService

# Mock dependencies as needed or use real ones if they are simple
async def main():
    print("--- Starting Backend-Only Mock Verification ---")
    
    # Force mock mode
    os.environ["MOCK_AI_CALLS"] = "true"
    settings = Settings(mock_ai_calls=True)
    storage = LocalStorage(settings.output_dir)
    
    # Initialize services with placeholders for complex deps
    gemini_svc = GeminiService(client=None, settings=settings)
    qc_svc = QCService(gemini=gemini_svc, settings=settings)
    script_svc = ScriptService(gemini=gemini_svc, storage=storage, settings=settings)
    avatar_svc = AvatarService(gemini_image=None, imagen=None, storage=storage, settings=settings)
    storyboard_svc = StoryboardService(gemini_image=None, qc=qc_svc, storage=storage, settings=settings)
    video_svc = VideoService(veo=None, gcs=None, qc=qc_svc, storage=storage, settings=settings)
    stitch_svc = StitchService(storage=storage)

    # 1. Test Script
    print("\n1. Testing Script Generation...")
    req = ScriptRequest(
        product_name="AeroGlide Pro Running Shoes",
        specifications="Lightweight, ZoomX foam",
        scene_count=3,
        image_url="http://localhost:8000/output/samples/running_shoes.png"
    )
    script_resp = await script_svc.generate_script(req)
    run_id = script_resp.run_id
    print(f"   Success! run_id: {run_id}")
    print(f"   Product image saved: {script_resp.product_image_path}")

    # 2. Test Avatar
    print("\n2. Testing Avatar Generation...")
    avatar_resp = await avatar_svc.generate_avatars(run_id, script_resp.script.avatar_profile)
    print(f"   Success! Generated {len(avatar_resp.variants)} variants")
    
    print("   Selecting avatar variant 0...")
    selected_avatar_url = await avatar_svc.select_avatar(run_id, 0)
    print(f"   Success! Selected avatar: {selected_avatar_url}")

    # 3. Test Storyboard
    print("\n3. Testing Storyboard Generation...")
    sb_resp = await storyboard_svc.generate_storyboard(run_id, script_resp.script.scenes)
    print(f"   Success! Generated {len(sb_resp.results)} scenes")
    print(f"   Result 0 image: {sb_resp.results[0].image_path}")
    print(f"   QC Report (Mock): {sb_resp.results[0].qc_report}")

    # 4. Test Video
    print("\n4. Testing Video Generation...")
    video_resp = await video_svc.generate_videos(
        run_id=run_id,
        scenes_data=sb_resp.results,
        script_scenes=script_resp.script.scenes,
        avatar_profile=script_resp.script.avatar_profile
    )
    print(f"   Success! Generated {len(video_resp.results)} video scenes")
    print(f"   Video Result 0: {video_resp.results[0].selected_video_path}")

    # 5. Test Stitch
    print("\n5. Testing Stitching...")
    final_video_url = await stitch_svc.stitch_videos(run_id)
    print(f"   Success! Final video: {final_video_url}")

    # 6. Test Multi-Agent Debate Mode
    print("\n6. Testing Multi-Agent Debate QC...")
    os.environ["USE_AGENT_DEBATE"] = "true"
    debate_report = await qc_svc.multi_agent_evaluate_video(
        video_uri="gs://mock/video.mp4",
        reference_uri="gs://mock/image.png",
        original_prompt="A professional commercial for running shoes."
    )
    print(f"   Success! Overall Verdict: {debate_report.overall_verdict}")
    print(f"   Debate Log Size: {len(debate_report.debate_log)}")
    for entry in debate_report.debate_log:
        print(f"   - {entry['agent']}: {entry['thought'][:60]}...")

    print("\n--- Backend-Only Mock Verification COMPLETED! ---")

if __name__ == "__main__":
    asyncio.run(main())
