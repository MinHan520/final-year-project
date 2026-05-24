"""SHAP explainability agent.

Splits the original ``generate_shap_explanation`` into compute + render so
the orchestrator can decide whether to ship the matplotlib figure (PNG bytes)
to the frontend or persist it to media storage. The PartitionExplainer with
superpixel masking is model-agnostic — it only needs the AIDE detector's
``_predict_from_numpy`` callable.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from ..schemas import SHAPResult
from .aide_detector import AIDEDetectorAgent

logger = logging.getLogger(__name__)


class SHAPExplainerAgent:
    """Compute a SHAP heatmap for a single image using a held detector."""

    def __init__(self, detector: AIDEDetectorAgent) -> None:
        self.detector = detector

    def explain(
        self,
        image_path: str | Path,
        max_evals: int = 200,
    ) -> SHAPResult:
        try:
            import shap
            import numpy as np
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from PIL import Image

            image = Image.open(image_path).convert("RGB").resize((256, 256), Image.BICUBIC)
            image_np = np.array(image)

            masker = shap.maskers.Image("inpaint_telea", image_np.shape)
            explainer = shap.PartitionExplainer(
                self.detector._predict_from_numpy, masker
            )

            shap_values = explainer(
                np.expand_dims(image_np, axis=0),
                max_evals=max_evals,
            )

            # values shape: (1, H, W, 3, 2) — class index 1 is "AI-generated"
            sv = shap_values.values[0, :, :, :, 1]
            sv_gray = sv.mean(axis=2)

            fig, ax = plt.subplots(1, 1, figsize=(6, 6))
            ax.imshow(image_np)
            vmax = float(np.abs(sv_gray).max()) or 1.0
            im = ax.imshow(sv_gray, cmap="bwr", alpha=0.55, vmin=-vmax, vmax=vmax)
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label("SHAP value (red = AI, blue = Real)", fontsize=9)
            ax.set_title("SHAP Explainability Heatmap", fontsize=12, fontweight="bold")
            ax.axis("off")
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
            plt.close(fig)

            return SHAPResult(
                heatmap_png_b64=base64.b64encode(buf.getvalue()).decode("ascii"),
                max_evals=max_evals,
                success=True,
            )
        except RuntimeError as e:
            msg = str(e).lower()
            if "out of memory" in msg:
                err = "Out of memory during SHAP. Try CPU or a smaller image."
            else:
                err = f"SHAP runtime error: {e}"
            logger.warning(err)
            return SHAPResult(
                heatmap_png_b64="", max_evals=max_evals, success=False, error=err
            )
        except Exception as e:
            logger.exception("SHAP failed")
            return SHAPResult(
                heatmap_png_b64="", max_evals=max_evals, success=False, error=str(e)
            )
