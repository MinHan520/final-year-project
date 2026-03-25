import cv2
import numpy as np
from .base import BaseAnalyzer, DiagnosticReport, Finding


class ImageAnalyzer(BaseAnalyzer):
    """Analyzes images for common AI-generation artifacts."""

    def analyze(self, image: np.ndarray) -> DiagnosticReport:
        report = DiagnosticReport(media_type="image")
        report.findings.extend(self._check_face_symmetry(image))
        report.findings.extend(self._check_lighting(image))
        report.findings.extend(self._check_structure(image))
        report.findings.extend(self._check_frequency(image))
        report.findings.extend(self._check_color(image))
        report.findings.extend(self._check_text_regions(image))
        return report

    # ------------------------------------------------------------------
    # Face symmetry
    # ------------------------------------------------------------------
    def _check_face_symmetry(self, image: np.ndarray) -> list[Finding]:
        findings = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for i, (x, y, w, h) in enumerate(faces):
            face_roi = gray[y : y + h, x : x + w]
            left_half = face_roi[:, : w // 2]
            right_half = cv2.flip(face_roi[:, w // 2 :], 1)

            # Ensure same dimensions
            min_w = min(left_half.shape[1], right_half.shape[1])
            left_half = left_half[:, :min_w]
            right_half = right_half[:, :min_w]

            diff = cv2.absdiff(left_half, right_half)
            mean_diff = float(np.mean(diff))

            if mean_diff > 25:
                severity = "high" if mean_diff > 40 else "medium"
                findings.append(Finding(
                    category="Anatomical Error",
                    description=(
                        f"Face #{i + 1} shows notable asymmetry between left and right halves "
                        f"(difference score: {mean_diff:.1f}). AI-generated faces often have "
                        f"mismatched features such as uneven eyes, ears, or jawlines."
                    ),
                    severity=severity,
                    location=f"Face region at ({x}, {y})",
                ))

        return findings

    # ------------------------------------------------------------------
    # Lighting / shadow consistency
    # ------------------------------------------------------------------
    def _check_lighting(self, image: np.ndarray) -> list[Finding]:
        findings = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        h, w = gray.shape

        # Compute gradient direction using Sobel
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=5)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=5)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        angle = np.arctan2(grad_y, grad_x)

        # Only consider strong gradients (likely edges / shadows)
        threshold = np.percentile(magnitude, 75)
        strong_mask = magnitude > threshold

        # Divide into quadrants and compute dominant gradient direction
        quadrant_dirs = []
        for qy in range(2):
            for qx in range(2):
                y_s, y_e = qy * h // 2, (qy + 1) * h // 2
                x_s, x_e = qx * w // 2, (qx + 1) * w // 2
                q_mask = strong_mask[y_s:y_e, x_s:x_e]
                q_angle = angle[y_s:y_e, x_s:x_e]
                if np.sum(q_mask) > 100:
                    dominant = float(np.median(q_angle[q_mask]))
                    quadrant_dirs.append(dominant)

        if len(quadrant_dirs) >= 3:
            spread = float(np.std(quadrant_dirs))
            if spread > 0.8:
                findings.append(Finding(
                    category="Physics / Lighting Error",
                    description=(
                        f"Light gradient directions are inconsistent across image quadrants "
                        f"(spread: {spread:.2f} rad). This suggests shadows or lighting coming "
                        f"from multiple conflicting directions, a common AI rendering artifact."
                    ),
                    severity="medium" if spread < 1.2 else "high",
                ))

        return findings

    # ------------------------------------------------------------------
    # Structural coherence (smooth vs. detailed patches)
    # ------------------------------------------------------------------
    def _check_structure(self, image: np.ndarray) -> list[Finding]:
        findings = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        h, w = gray.shape
        patch_size = 32
        variances = []

        for y in range(0, h - patch_size, patch_size):
            for x in range(0, w - patch_size, patch_size):
                patch = gray[y : y + patch_size, x : x + patch_size]
                variances.append(float(np.var(patch)))

        if not variances:
            return findings

        variances = np.array(variances)
        low_var = np.percentile(variances, 10)
        high_var = np.percentile(variances, 90)

        if high_var > 0 and low_var / high_var < 0.01 and np.mean(variances < 5) > 0.15:
            findings.append(Finding(
                category="Structural Error",
                description=(
                    "The image contains regions that are unnaturally smooth (near-zero texture) "
                    "adjacent to highly detailed areas. This 'AI smoothing' artifact occurs when "
                    "generative models fail to maintain consistent detail levels across the image."
                ),
                severity="medium",
            ))

        # Check for repetitive texture patterns
        edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
        edge_density = float(np.mean(edges > 0))
        if edge_density < 0.02:
            findings.append(Finding(
                category="Structural Error",
                description=(
                    "The image has very low edge density, suggesting overly smooth or "
                    "'painted' surfaces that lack natural texture detail."
                ),
                severity="low",
            ))

        return findings

    # ------------------------------------------------------------------
    # Frequency domain analysis
    # ------------------------------------------------------------------
    def _check_frequency(self, image: np.ndarray) -> list[Finding]:
        findings = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # 2D FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log1p(np.abs(f_shift))

        h, w = magnitude_spectrum.shape
        cy, cx = h // 2, w // 2

        # Compute radial power spectrum
        max_radius = min(cy, cx)
        radial_power = []
        for r in range(1, max_radius, 2):
            y_coords, x_coords = np.ogrid[-cy:h - cy, -cx:w - cx]
            mask = (x_coords**2 + y_coords**2 >= r**2) & (
                x_coords**2 + y_coords**2 < (r + 2) ** 2
            )
            if np.sum(mask) > 0:
                radial_power.append(float(np.mean(magnitude_spectrum[mask])))

        if len(radial_power) > 10:
            rp = np.array(radial_power)
            # Check for unusual drop-off in high frequencies
            low_freq_power = float(np.mean(rp[: len(rp) // 3]))
            high_freq_power = float(np.mean(rp[2 * len(rp) // 3 :]))

            if low_freq_power > 0 and high_freq_power / low_freq_power < 0.3:
                findings.append(Finding(
                    category="Frequency Anomaly",
                    description=(
                        "The image's frequency spectrum shows an unusually steep drop-off in "
                        "high-frequency content. Natural photographs typically retain more "
                        "high-frequency noise and detail. AI-generated images often exhibit "
                        "this 'spectral gap' due to the generation process."
                    ),
                    severity="medium",
                ))

            # Check for periodic spikes (GAN fingerprint)
            rp_detrended = rp - np.convolve(rp, np.ones(5) / 5, mode="same")
            spikes = np.abs(rp_detrended) > 2 * np.std(rp_detrended)
            if np.sum(spikes) > 3:
                findings.append(Finding(
                    category="Frequency Anomaly",
                    description=(
                        "Periodic spikes detected in the frequency spectrum. This pattern "
                        "is characteristic of GAN-based image generation, where the upsampling "
                        "process leaves repeating frequency fingerprints."
                    ),
                    severity="high",
                ))

        return findings

    # ------------------------------------------------------------------
    # Color consistency
    # ------------------------------------------------------------------
    def _check_color(self, image: np.ndarray) -> list[Finding]:
        findings = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].astype(np.float32)

        # Check for unnaturally uniform saturation
        sat_std = float(np.std(saturation))
        if sat_std < 15:
            findings.append(Finding(
                category="Color Anomaly",
                description=(
                    f"The image has unusually uniform color saturation (std: {sat_std:.1f}). "
                    f"Natural images typically show more variation in color intensity. "
                    f"AI models sometimes produce overly consistent coloring."
                ),
                severity="low",
            ))

        # Check for color banding in gradients
        value = hsv[:, :, 2].astype(np.float32)
        gradient = np.abs(np.diff(value, axis=1))
        # Count columns where gradient suddenly jumps (banding)
        col_means = np.mean(gradient, axis=0)
        jumps = np.sum(col_means > np.mean(col_means) + 3 * np.std(col_means))
        if jumps > 5:
            findings.append(Finding(
                category="Color Anomaly",
                description=(
                    "Color banding detected in gradient regions. Instead of smooth transitions, "
                    "there are visible bands of discrete color levels, which can occur in "
                    "AI-generated images due to limited color palette generation."
                ),
                severity="medium",
            ))

        return findings

    # ------------------------------------------------------------------
    # Text region detection
    # ------------------------------------------------------------------
    def _check_text_regions(self, image: np.ndarray) -> list[Finding]:
        findings = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Use MSER to detect text-like regions
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        # Filter for text-like regions (elongated, small bounding boxes)
        text_candidates = 0
        for region in regions:
            x, y, w, h = cv2.boundingRect(region)
            aspect = w / max(h, 1)
            area = w * h
            if 0.1 < aspect < 10 and 100 < area < 5000:
                text_candidates += 1

        if text_candidates > 20:
            findings.append(Finding(
                category="Typographical Error",
                description=(
                    f"Detected {text_candidates} text-like regions in the image. "
                    f"AI-generated images frequently contain text that appears legible at "
                    f"first glance but dissolves into gibberish, malformed characters, or "
                    f"nonsensical words upon closer inspection."
                ),
                severity="medium",
                location="Multiple regions across the image",
            ))

        return findings
