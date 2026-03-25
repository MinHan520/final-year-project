import tempfile
import os
import numpy as np
import cv2
from PIL import Image
import streamlit as st


def load_image(uploaded_file) -> np.ndarray:
    """Convert a Streamlit UploadedFile to an OpenCV BGR numpy array."""
    pil_image = Image.open(uploaded_file).convert("RGB")
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_array


def load_video(uploaded_file) -> str:
    """Save a Streamlit UploadedFile to a temp path and return the path.

    OpenCV's VideoCapture requires a file path, not bytes.
    """
    suffix = os.path.splitext(uploaded_file.name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.read())
    tmp.close()
    return tmp.name


def cleanup_temp(path: str) -> None:
    """Remove a temporary file if it exists."""
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass
