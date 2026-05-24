from backend.app.config import get_settings
from backend.app.agents.aide_detector import AIDEDetectorAgent
import asyncio

async def test():
    settings = get_settings()
    print("Settings loaded")
    agent = await asyncio.to_thread(
        AIDEDetectorAgent,
        checkpoint_path=settings.aide_checkpoint_path,
        device="cpu",
        resnet_path=settings.aide_resnet_path,
        convnext_path=settings.aide_convnext_path
    )
    print("Agent loaded")

if __name__ == "__main__":
    asyncio.run(test())
