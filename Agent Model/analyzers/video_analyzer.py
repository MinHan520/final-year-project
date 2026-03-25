import cv2
import numpy as np
from .base import BaseAnalyzer, DiagnosticReport, Finding


class VideoAnalyzer(BaseAnalyzer):
    """Analyzes videos for common AI-generation artifacts."""

    SAMPLE_FPS = 2  # Analyze 2 frames per second for performance

    def analyze(self, video_path: str, progress_callback=None) -> DiagnosticReport:
        report = DiagnosticReport(media_type="video")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            report.findings.append(Finding(
                category="Error",
                description="Could not open video file for analysis.",
                severity="high",
            ))
            return report

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps / self.SAMPLE_FPS))
        duration = total_frames / fps if fps > 0 else 0

        # Sample frames
        frames = []
        timestamps = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                frames.append(frame)
                timestamps.append(frame_idx / fps)
                if progress_callback:
                    progress_callback(min(frame_idx / max(total_frames, 1), 1.0))
            frame_idx += 1
        cap.release()

        if len(frames) < 2:
            report.findings.append(Finding(
                category="Error",
                description="Video is too short to perform temporal analysis.",
                severity="low",
            ))
            return report

        report.findings.extend(self._check_temporal_consistency(frames, timestamps))
        report.findings.extend(self._check_motion(frames, timestamps))
        report.findings.extend(self._check_face_consistency(frames, timestamps))
        report.findings.extend(self._check_background_stability(frames, timestamps))

        if progress_callback:
            progress_callback(1.0)

        return report

    # ------------------------------------------------------------------
    # Temporal consistency (flickering / instability)
    # ------------------------------------------------------------------
    def _check_temporal_consistency(
        self, frames: list[np.ndarray], timestamps: list[float]
    ) -> list[Finding]:
        findings = []
        ssim_scores = []

        for i in range(len(frames) - 1):
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)

            # Resize to same dimensions if needed
            h = min(gray1.shape[0], gray2.shape[0])
            w = min(gray1.shape[1], gray2.shape[1])
            gray1 = cv2.resize(gray1, (w, h))
            gray2 = cv2.resize(gray2, (w, h))

            # Compute simple structural similarity via normalized correlation
            score = float(cv2.matchTemplate(
                gray1, gray2, cv2.TM_CCOEFF_NORMED
            )[0][0])
            ssim_scores.append(score)

        if not ssim_scores:
            return findings

        scores = np.array(ssim_scores)
        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))

        # Find frames with sudden drops
        flickering_frames = []
        for i, s in enumerate(scores):
            if s < mean_score - 2 * std_score and s < 0.85:
                flickering_frames.append((i, timestamps[i], s))

        if flickering_frames:
            worst = min(flickering_frames, key=lambda x: x[2])
            findings.append(Finding(
                category="Temporal Inconsistency",
                description=(
                    f"Detected {len(flickering_frames)} frame(s) with sudden visual changes. "
                    f"Objects may appear to flicker, morph, or change texture between frames. "
                    f"The most severe drop occurs around the {worst[1]:.1f}s mark "
                    f"(similarity: {worst[2]:.2f})."
                ),
                severity="high" if len(flickering_frames) > 3 else "medium",
                location=f"Around {worst[1]:.1f}s",
            ))

        # Overall instability
        if std_score > 0.1:
            findings.append(Finding(
                category="Temporal Inconsistency",
                description=(
                    f"Frame-to-frame visual stability is unusually variable "
                    f"(std: {std_score:.3f}). AI-generated videos often exhibit "
                    f"inconsistent rendering quality across frames."
                ),
                severity="medium",
            ))

        return findings

    # ------------------------------------------------------------------
    # Motion anomalies via optical flow
    # ------------------------------------------------------------------
    def _check_motion(
        self, frames: list[np.ndarray], timestamps: list[float]
    ) -> list[Finding]:
        findings = []
        flow_magnitudes = []

        for i in range(min(len(frames) - 1, 30)):  # Cap at 30 pairs
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)

            h = min(gray1.shape[0], gray2.shape[0], 480)
            w = min(gray1.shape[1], gray2.shape[1], 640)
            gray1 = cv2.resize(gray1, (w, h))
            gray2 = cv2.resize(gray2, (w, h))

            flow = cv2.calcOpticalFlowFarneback(
                gray1, gray2, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
            )
            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            flow_magnitudes.append(magnitude)

        if not flow_magnitudes:
            return findings

        # Check for spatially incoherent motion
        incoherent_frames = []
        for i, mag in enumerate(flow_magnitudes):
            h, w = mag.shape
            quadrants = [
                mag[: h // 2, : w // 2],
                mag[: h // 2, w // 2 :],
                mag[h // 2 :, : w // 2],
                mag[h // 2 :, w // 2 :],
            ]
            q_means = [float(np.mean(q)) for q in quadrants]
            q_std = float(np.std(q_means))
            overall_mean = float(np.mean(mag))

            if overall_mean > 1.0 and q_std > overall_mean * 0.8:
                incoherent_frames.append((i, timestamps[i]))

        if incoherent_frames:
            t = incoherent_frames[0][1]
            findings.append(Finding(
                category="Motion Anomaly",
                description=(
                    f"Detected {len(incoherent_frames)} frame(s) with spatially incoherent motion. "
                    f"Different image regions move in conflicting directions or at conflicting "
                    f"speeds, suggesting unnatural physics. First occurrence near {t:.1f}s."
                ),
                severity="medium",
                location=f"Starting around {t:.1f}s",
            ))

        # Check for unnaturally smooth/uniform motion
        all_stds = [float(np.std(m)) for m in flow_magnitudes]
        if all_stds and np.mean(all_stds) < 0.5 and np.mean([np.mean(m) for m in flow_magnitudes]) > 0.5:
            findings.append(Finding(
                category="Motion Anomaly",
                description=(
                    "Motion across frames is unnaturally uniform, suggesting subjects glide "
                    "rather than exhibit natural, varied movement. AI-generated videos often "
                    "produce overly smooth motion that lacks natural jitter and variation."
                ),
                severity="low",
            ))

        return findings

    # ------------------------------------------------------------------
    # Face consistency across frames
    # ------------------------------------------------------------------
    def _check_face_consistency(
        self, frames: list[np.ndarray], timestamps: list[float]
    ) -> list[Finding]:
        findings = []
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        face_sizes = []
        face_positions = []
        face_frames = []

        for i, frame in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            if len(faces) > 0:
                # Track the largest face
                largest = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest
                face_sizes.append(w * h)
                face_positions.append((x + w / 2, y + h / 2))
                face_frames.append(i)

        if len(face_sizes) < 3:
            return findings

        # Check for erratic face size jumps
        sizes = np.array(face_sizes, dtype=np.float32)
        size_diffs = np.abs(np.diff(sizes)) / np.maximum(sizes[:-1], 1)
        large_jumps = np.sum(size_diffs > 0.3)

        if large_jumps > 2:
            idx = int(np.argmax(size_diffs))
            t = timestamps[face_frames[idx]] if face_frames[idx] < len(timestamps) else 0
            findings.append(Finding(
                category="Facial Inconsistency",
                description=(
                    f"Face size changes erratically across {large_jumps} transitions. "
                    f"The face appears to grow or shrink unnaturally, which is common in "
                    f"AI-generated videos where facial features are regenerated per-frame."
                ),
                severity="medium",
                location=f"Most notable around {t:.1f}s",
            ))

        # Check for position jitter
        positions = np.array(face_positions)
        pos_diffs = np.sqrt(np.sum(np.diff(positions, axis=0) ** 2, axis=1))
        jitter = float(np.std(pos_diffs))
        if jitter > 20:
            findings.append(Finding(
                category="Facial Inconsistency",
                description=(
                    f"Face position jitters significantly across frames (jitter score: {jitter:.1f}). "
                    f"In natural video, head position changes smoothly. AI generation can cause "
                    f"the face to 'jump' or 'snap' between positions."
                ),
                severity="medium",
            ))

        return findings

    # ------------------------------------------------------------------
    # Background stability
    # ------------------------------------------------------------------
    def _check_background_stability(
        self, frames: list[np.ndarray], timestamps: list[float]
    ) -> list[Finding]:
        findings = []
        if len(frames) < 5:
            return findings

        # Use background subtractor
        bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=len(frames), varThreshold=50, detectShadows=False
        )

        fg_ratios = []
        for frame in frames:
            small = cv2.resize(frame, (320, 240))
            mask = bg_sub.apply(small)
            fg_ratio = float(np.mean(mask > 0))
            fg_ratios.append(fg_ratio)

        if not fg_ratios:
            return findings

        ratios = np.array(fg_ratios)
        # Skip early frames as background model is still learning
        if len(ratios) > 10:
            stable_ratios = ratios[5:]
            mean_fg = float(np.mean(stable_ratios))
            std_fg = float(np.std(stable_ratios))

            if mean_fg > 0.4:
                findings.append(Finding(
                    category="Background Warping",
                    description=(
                        f"A large portion of the background changes across frames "
                        f"(avg {mean_fg * 100:.0f}% of pixels change). In AI-generated videos, "
                        f"the background often warps, bends, or shifts as the foreground "
                        f"subject moves."
                    ),
                    severity="high" if mean_fg > 0.6 else "medium",
                ))

            # Check for sudden background changes
            bg_spikes = []
            for i in range(1, len(stable_ratios)):
                if stable_ratios[i] - stable_ratios[i - 1] > 0.2:
                    bg_spikes.append(timestamps[min(i + 5, len(timestamps) - 1)])

            if len(bg_spikes) > 2:
                findings.append(Finding(
                    category="Background Warping",
                    description=(
                        f"Detected {len(bg_spikes)} sudden background shifts. "
                        f"The background appears to warp or restructure itself abruptly, "
                        f"which is a telltale sign of AI video generation."
                    ),
                    severity="high",
                    location=f"First occurrence near {bg_spikes[0]:.1f}s",
                ))

        return findings
