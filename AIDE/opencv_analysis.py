import cv2
import numpy as np


def extract_features(image_path: str):
    """
    Extract three forensic visualizations from an image:
      1. Noise residual map (high-frequency isolation)
      2. Laplacian edge gradient map
      3. Error Level Analysis (ELA) compression heatmap

    Returns three RGB numpy arrays suitable for st.image().
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # --- 1. Noise Residual ---
    blurred = cv2.medianBlur(gray, 5)
    noise = cv2.subtract(gray, blurred)
    # Normalize to full 0-255 range for visibility
    noise_norm = cv2.normalize(noise, None, 0, 255, cv2.NORM_MINMAX)
    noise_rgb = cv2.cvtColor(noise_norm, cv2.COLOR_GRAY2RGB)

    # --- 2. Edge Gradient (Laplacian) ---
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    lap_abs = np.uint8(np.clip(np.abs(laplacian), 0, 255))
    edge_rgb = cv2.applyColorMap(lap_abs, cv2.COLORMAP_INFERNO)
    edge_rgb = cv2.cvtColor(edge_rgb, cv2.COLOR_BGR2RGB)

    # --- 3. Error Level Analysis (ELA) ---
    # Re-compress at quality 90 and compare to original
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    _, enc_buf = cv2.imencode(".jpg", img_bgr, encode_param)
    recompressed = cv2.imdecode(enc_buf, cv2.IMREAD_COLOR)

    ela_diff = cv2.absdiff(img_bgr, recompressed)
    # Amplify differences for visibility (scale x 20, clamp at 255)
    ela_amplified = np.clip(ela_diff.astype(np.float32) * 20, 0, 255).astype(np.uint8)
    ela_gray = cv2.cvtColor(ela_amplified, cv2.COLOR_BGR2GRAY)
    ela_heatmap = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)
    ela_rgb = cv2.cvtColor(ela_heatmap, cv2.COLOR_BGR2RGB)

    return noise_rgb, edge_rgb, ela_rgb
