import logging
logging.basicConfig(level=logging.DEBUG)

from backend.app.config import get_settings
from backend.app.agents.aide_detector import AIDEDetectorAgent

settings = get_settings()
print("Settings loaded")

import sys
import os
from pathlib import Path

print("Calling ensure_legacy_aide_on_path")
from backend.app.agents.aide_detector import _ensure_legacy_aide_on_path
_ensure_legacy_aide_on_path()

print("Importing torch")
import torch
print("Importing transforms")
from torchvision import transforms
print("Importing models.AIDE")
from models.AIDE import AIDE
print("Importing data.dct")
from data.dct import DCT_base_Rec_Module

print("Instantiating AIDE")
model = AIDE(
    resnet_path=str(settings.aide_resnet_path),
    convnext_path=str(settings.aide_convnext_path),
)
print("AIDE instantiated")
