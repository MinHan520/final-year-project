"""AIDE mixture-of-experts deepfake detector agent.

Wraps the existing AIDEDetectorBackend (PyTorch + DCT pipeline) with a typed
interface returning Pydantic models. The model is loaded once on construction
and reused across calls — callers should hold a long-lived instance.

The original AIDE model code (models.AIDE, data.dct) lives in the legacy AIDE
repo. This agent imports from there for now via a configurable path; once the
backend stabilises we can vendor the model code into this project.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from ..schemas import AIDEResult, SHAPResult

logger = logging.getLogger(__name__)


def _ensure_legacy_aide_on_path() -> None:
    """Make the original AIDE repo importable so we can reuse models.AIDE etc.

    Looks for a sibling ``AIDE`` directory next to the React Project root.
    Override with the AIDE_REPO_PATH env var.
    """
    override = os.environ.get("AIDE_REPO_PATH")
    candidates = []
    if override:
        candidates.append(Path(override))
    here = Path(__file__).resolve()
    candidates.append(here.parents[3].parent / "AIDE")

    for candidate in candidates:
        if (candidate / "models" / "AIDE.py").exists() or (
            candidate / "models" / "AIDE" / "__init__.py"
        ).exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return
        if (candidate / "models").exists() and (candidate / "data").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return

    logger.warning(
        "Could not locate legacy AIDE repo for model imports. "
        "Set AIDE_REPO_PATH or place the AIDE folder next to React Project/."
    )


class AIDEDetectorAgent:
    """Persistent AIDE detector — load once, reuse for many predictions."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        device: Optional[str] = None,
        resnet_path: str | Path = "pretrained_ckpts/resnet50.pth",
        convnext_path: str | Path = "pretrained_ckpts/open_clip_pytorch_model.bin",
    ) -> None:
        _ensure_legacy_aide_on_path()

        import torch
        from torchvision import transforms
        from models.AIDE import AIDE
        from data.dct import DCT_base_Rec_Module

        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        logger.info("Initializing AIDE on device: %s", self.device)

        self.model = AIDE(
            resnet_path=str(resnet_path),
            convnext_path=str(convnext_path),
        )

        ckpt = Path(checkpoint_path)
        if not ckpt.exists():
            raise FileNotFoundError(f"AIDE checkpoint missing at {ckpt}")

        state_dict = torch.load(str(ckpt), map_location=self.device)
        if "model" in state_dict:
            self.model.load_state_dict(state_dict["model"])
        elif "state_dict" in state_dict:
            self.model.load_state_dict(state_dict["state_dict"])
        else:
            self.model.load_state_dict(state_dict)

        self.model.to(self.device)
        self.model.eval()

        self.dct_module = DCT_base_Rec_Module()

        self._torch = torch
        self.transform_before = transforms.Compose([transforms.ToTensor()])
        self.transform_final = transforms.Compose(
            [
                transforms.Resize(
                    (256, 256),
                    interpolation=transforms.InterpolationMode.BICUBIC,
                ),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

    def _stacked_input(self, image):
        """Build the 5-stream tensor expected by the AIDE forward pass."""
        torch = self._torch
        tensor_init = self.transform_before(image).to(self.device)
        with torch.no_grad():
            x_minmin, x_maxmax, x_minmin1, x_maxmax1 = self.dct_module(tensor_init)
            x_0 = self.transform_final(tensor_init)
            x_minmin = self.transform_final(x_minmin)
            x_maxmax = self.transform_final(x_maxmax)
            x_minmin1 = self.transform_final(x_minmin1)
            x_maxmax1 = self.transform_final(x_maxmax1)
            return torch.stack(
                [x_minmin, x_maxmax, x_minmin1, x_maxmax1, x_0], dim=0
            ).unsqueeze(0)

    def predict(self, image_path: str | Path) -> AIDEResult:
        """Single forward pass, returns probability of AI generation."""
        from PIL import Image

        torch = self._torch
        try:
            image = Image.open(image_path).convert("RGB")
            input_tensor = self._stacked_input(image)
            with torch.no_grad():
                logits = self.model(input_tensor)
                probs = torch.softmax(logits, dim=1)
                probability = float(probs[0, 1].item())
            return AIDEResult(score=probability, success=True)
        except Exception as e:
            logger.exception("AIDE inference failed on %s", image_path)
            return AIDEResult(score=-1.0, success=False, error=str(e))

    def _predict_from_numpy(self, images_np):
        """SHAP hook: takes (N, H, W, 3) uint8 numpy, returns (N, 2) probs."""
        import numpy as np
        from PIL import Image

        torch = self._torch
        results = []
        for i in range(images_np.shape[0]):
            img = Image.fromarray(images_np[i].astype(np.uint8))
            input_tensor = self._stacked_input(img)
            with torch.no_grad():
                logits = self.model(input_tensor)
                probs = torch.softmax(logits, dim=1)
            results.append(probs[0].detach().cpu().numpy())
        return np.array(results)
