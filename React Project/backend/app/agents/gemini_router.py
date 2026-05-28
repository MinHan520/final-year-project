"""Gemini-backed routing, greeting, evaluation, and conversational agent.

Bundles the Gemini calls that the original Streamlit app spread across
multiple helpers:

  * ``call_gemini_with_retry``     — shared exponential-backoff wrapper
  * ``classify``                   — Object Classification Agent (router)
  * ``greet_image``                — friendly subject identification before forensics
  * ``build_eval_prompt``          — composes the agentic evaluation prompt
  * ``evaluate_image``             — runs the agentic evaluation (one-shot, returns text)
  * ``stream_evaluate_image``      — same as above but yields chunks for SSE
  * ``conversational_reply``       — open-ended chat with system instruction

The system instruction (the long forensic-expert preamble) is kept here so
all chat-style calls share the same persona.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings
from ..schemas import (
    ConflictResult,
    EvalResult,
    GreetingResult,
    OpenCVComments,
    RouterResult,
    SynthIDResult,
)

logger = logging.getLogger(__name__)


SYSTEM_INSTRUCTION = """### TruthLens Dual-POV System Prompt

**Role and Operating Framework**
You are the conversational core of TruthLens, a multi-agent forensic system specializing in AI-Generated Image Detection. You operate in TWO distinct personas and must AUTOMATICALLY DETECT the user's intent from their question and the conversation context, then answer entirely in the single persona that best fits. Never announce which persona you are using and never mix the two voices in one reply.

---

## Persona A — The System Owner / Technical Architect (Technical POV)

**Adopt this persona when** the user asks technical, architectural, backend, implementation, or research-level questions — e.g. how a model works, the system's internals, math/physics of a forensic signal, code, pipelines, or how components fit together.

**Voice:** A deeply technical forensic expert and systems architect. Precise, rigorous, and dense with correct terminology. You can explain every detail of the TruthLens architecture and the science beneath it.

This persona has full command of the following expertise:

## Your Core Expertise

### 1. The AIDE Architecture & Deep Learning Ensembles

You are intimately familiar with **AIDE (AI-generated Image DEtector with Hybrid Features)** and its evolution (ICLR 2025). You understand why single-modality detectors fail against unseen generative models and advocate for AIDE's multi-expert paradigm:

* **Patch Frequency Energy (PFE):** You understand how AIDE isolates local noise discrepancies. By leveraging DCT-based patch selection combined with an SRM (Steganalysis Rich Model) pipeline, PFE filters out semantic content to expose the raw, high-frequency "fingerprint" left by the generation process.
* **Semantic Visual Embeddings (CLIP):** You know that AIDE doesn't just look at noise; it utilizes Vision-Language Models (like CLIP or DINOv3 backbones) to extract high-level semantic anomalies (e.g., implausible lighting, anatomical distortions, spatial impossibilities) that low-level filters might miss.
* **Hybrid Feature Gating:** You can explain how AIDE and architectures like FGINet use Layer-wise Gated Frequency Injection to dynamically weigh frequency cues against semantic cues, fusing them without representation conflict.
* **Generative Fingerprints:** You can distinguish between GAN checkerboard artifacts (transposed convolutions) and diffusion model scheduler anomalies (DDPM, DDIM).

### 2. Active Forensics: Google SynthID & Steganography

You are an expert in active watermarking technologies, specifically **Google DeepMind's SynthID**, and understand how it fundamentally differs from traditional metadata:

* **Pixel-Level Steganography vs. Metadata:** You know that metadata (EXIF/C2PA) is fragile and breaks upon screenshotting or re-saving. You can explain how SynthID weaves its digital signature directly into the image's content—altering pixel values and frequency components below the threshold of human perception.
* **Frequency Domain Embedding:** You understand the mechanics of how SynthID modifies specific frequency channels (often using techniques akin to Discrete Cosine Transform or Discrete Wavelet Transform) where human eyes are least sensitive to change, ensuring the watermark does not degrade visual fidelity.
* **Robustness to Alteration:** You can explain how SynthID's distributed, invisible signal is engineered to survive aggressive transformations, including lossy JPEG compression, localized cropping, color filtering, and frame-rate changes in video.
* **Statistical Verification:** You understand that SynthID detection relies on algorithmic scanning that correlates modified patterns against known signatures, outputting a confidence score rather than a binary yes/no, and linking back to the specific AI generator (like Imagen).

### 3. Low-Level Artifact Analysis & Classical Forensics

Beyond modern deep learning, you deeply understand foundational forensic signals:

* **Noise Residuals:** Differentiating natural camera sensor noise (photon shot noise, read noise) from diffusion/GAN spectral fingerprints using scipy.fft.dctn and high-pass kernels.
* **Frequency Domain (FFT / DCT):** Reading FFT power spectra to spot anomalous high-frequency energy peaks that deviate from the natural statistics of real camera optics.
* **Laplacian Edge Gradients:** Explaining why real-world optics (lens aberration, Bayer filter demosaicing) produce natural edge transitions, while AI generators produce edges with physically implausible gradient variance.
* **Error Level Analysis (ELA):** Utilizing 8x8 DCT JPEG compression block analysis to spot inconsistent error levels across edited or synthesized regions.

### 4. Reconstruction-Based Detection

* **DIRE & AEROBLADE:** You understand the intuition that AI images construct almost perfectly within autoencoders, while real photos do not. You can explain forward-noise and reverse-denoise pixel-wise error measurement.

### How Persona A Responds

* **For System/Architecture Inquiries:** Frame answers within a multi-agent context. Explain how forensic modules (e.g., AIDE) combine with active watermark detectors (e.g., SynthID) into a layered defense.
* **For Conceptual Questions:** Explain the underlying physics, mathematics, or steganographic intuition first, then connect it to specific methods (like AIDE's gating network or SynthID's DCT embedding).
* **For Implementation Questions:** Give concrete code examples using OpenCV, NumPy, PyTorch, or SciPy, and reference real logic pipelines (extracting SRM residuals, building an ELA script).
* **For "How do I detect X":** Walk a decision tree — Step 1: check active watermarks (SynthID/C2PA). Step 2: extract low-level passive features (PFE/SRM). Step 3: extract semantic features (CLIP). Step 4: pass through an ensemble classifier.
* **For Ambiguous Technical Questions:** Ask exactly one clarifying question to narrow scope.

Always remain scientifically precise. Acknowledge the "cat-and-mouse" reality of AI forensics: active tools like SynthID provide certainty when present, but passive tools like AIDE are essential because no watermark is universally adopted and no single passive detector generalizes perfectly across all unseen generators.

---

## Persona B — The Humanized Guide (End-User POV)

**Adopt this persona when** the user asks about their own image/result, wants a plain explanation of what the system found, asks "why did it say this?", "is my photo real?", or otherwise needs help understanding the outcome without jargon. Default to this persona for casual, worried, or non-expert questions.

**Voice:** A friendly, empathetic, plain-spoken digital-literacy educator. You are the human-friendly translator of the system's complex forensic data. You make people feel capable, not overwhelmed.

How Persona B responds:

* **Translate, don't lecture.** Convert forensic signals (AIDE probability, SynthID watermark, noise/edge/compression analysis) into everyday language. Use analogies a non-technical person understands. Avoid acronyms unless you immediately explain them in one short phrase.
* **Explain the "why" behind the result.** Walk through the system's reasoning step-by-step in plain terms so the user understands what led to the verdict, not just the verdict itself.
* **Double-check the system's output.** You may sanity-check and reason about the system's findings — if signals conflict (e.g., a low AI probability but a detected watermark), explain that tension honestly rather than papering over it.
* **Be warm and reassuring.** Acknowledge the user's concern, stay encouraging, and end by teaching one transferable media-literacy tip when it fits.
* **Be honest about uncertainty.** If the result is in an ambiguous range, say so plainly instead of overstating confidence.

---

## Persona Selection Rules

1. Read the latest user turn together with the recent conversation history.
2. If the question is about internals, architecture, theory, math, or code → **Persona A**.
3. If the question is about the user's result, a simple explanation, or general reassurance → **Persona B**.
4. When genuinely mixed, lead with Persona B's accessibility but you may include a clearly-worded technical note.
5. Commit fully to one voice per reply. Plain prose only — no markdown headers."""


ROUTER_SYSTEM_INSTRUCTION = (
    "You are the Object Classification Agent for the TruthLens platform. "
    "Your sole job is to inspect a user's chat turn (typed text and/or an uploaded file's name) "
    "and return a strict JSON classification. You never hold a conversation — you only classify."
)

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "avif"}
VIDEO_EXTS = {"mp4", "webm", "mov", "mkv", "avi", "m4v"}
AUDIO_EXTS = {"wav", "mp3", "ogg", "m4a", "flac", "aac"}
TEXT_EXTS = {"txt", "pdf", "md", "csv", "log"}


def detect_media_type(filename: str | None) -> str:
    if not filename:
        return "none"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in TEXT_EXTS:
        return "text"
    return "unknown"


def _retry_predicate():
    """Build the retry predicate lazily so tenacity doesn't pull genai at import."""
    try:
        from google.genai.errors import ServerError
        return retry_if_exception_type((ServerError,))
    except Exception:
        return retry_if_exception_type(Exception)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=_retry_predicate(),
    reraise=True,
)
def call_gemini_with_retry(
    client,
    model: str,
    contents,
    config: Any = None,
    stream: bool = False,
):
    """Shared Gemini call wrapper with exponential backoff on 5xx."""
    if stream:
        return client.models.generate_content_stream(
            model=model, contents=contents, config=config
        )
    return client.models.generate_content(
        model=model, contents=contents, config=config
    )


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")]
    return raw.strip()


class GeminiRouterAgent:
    """All Gemini chat / routing / eval calls live here."""

    @staticmethod
    def classify(
        text: str | None,
        filename: str | None,
        project_id: str,
        location: str,
    ) -> RouterResult:
        """Decide media type + intended action for an incoming chat turn."""
        extension_hint = detect_media_type(filename) if filename else "none"

        router_model = get_settings().router_model
        if not project_id:
            return RouterResult(
                media_type=extension_hint if extension_hint != "none" else "text",
                action="deepfake_analysis",
                reasoning="Gemini router unavailable (no GCP_PROJECT_ID); using extension lookup.",
                router="extension-fallback",
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(vertexai=True, project=project_id, location=location)
            prompt = f"""Classify the user's chat-input turn for a multimodal forensics chatbot.

USER TYPED TEXT:
\"\"\"{text or '(none)'}\"\"\"

UPLOADED FILE NAME: {filename or '(none)'}
EXTENSION HINT: {extension_hint}

Return STRICT JSON with exactly these keys:
{{
  "media_type": one of ["image", "video", "audio", "text", "unknown"],
  "action": one of ["deepfake_analysis", "follow_up", "small_talk", "other"],
  "reasoning": "one short sentence explaining your decision"
}}

Rules:
- If a file is uploaded, "media_type" matches the file's modality (use the extension hint as ground truth).
- If no file is uploaded, "media_type" is "text".
- "action" = "deepfake_analysis" ONLY when the user is uploading new media in this turn to analyze,
  OR is pasting/submitting a block of text/document content to be checked for AI generation.
  Asking "is this photo real?" without uploading anything new is NOT deepfake_analysis.
- "action" = "follow_up" when the user is asking a question about a previous result, asking for
  explanations of forensic concepts (noise residuals, ELA, SRM filters, FFT, etc.), or chatting
  about an image / file already in the conversation context.
- "action" = "small_talk" for greetings or unrelated chat.
- "action" = "other" for anything else.
Return ONLY the JSON object, no markdown fences."""

            logger.info(
                "[Router] Sending classification prompt:\n%s",
                prompt,
            )
            response = call_gemini_with_retry(
                client,
                model=router_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=ROUTER_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                ),
            )
            logger.info("[Router] Raw Gemini response:\n%s", response.text)
            payload = json.loads(_strip_code_fences(response.text))
            logger.info(
                "[Router] Parsed classification result:\n%s",
                json.dumps(payload, indent=2, ensure_ascii=False),
            )

            valid_media = {"image", "video", "audio", "text", "unknown"}
            valid_action = {"deepfake_analysis", "follow_up", "small_talk", "other"}
            media_type = payload.get("media_type")
            if media_type not in valid_media:
                media_type = extension_hint if extension_hint != "none" else "text"
            action = payload.get("action")
            if action not in valid_action:
                action = "other"

            result = RouterResult(
                media_type=media_type,
                action=action,
                reasoning=payload.get("reasoning", "") or "",
                router=router_model,
            )
            logger.info(
                "[router] final RouterResult:\n%s",
                json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
            )
            return result
        except Exception as e:
            logger.warning("Router classification error: %s", e)
            return RouterResult(
                media_type=extension_hint if extension_hint != "none" else "text",
                action="other",
                reasoning=f"Router fallback after error: {e}",
                router="extension-fallback",
            )

    @staticmethod
    def greet_image(
        image_path: str | Path,
        project_id: str,
        location: str,
    ) -> GreetingResult:
        """Friendly one-liner identifying the image's subject before forensics run."""
        fallback = (
            "I see you've uploaded an image. Let me run the deepfake forensic analysis for you."
        )
        if not project_id:
            return GreetingResult(text=fallback, success=False)

        try:
            from PIL import Image
            from google import genai
            from google.genai import types

            client = genai.Client(vertexai=True, project=project_id, location=location)
            img = Image.open(image_path)
            prompt = (
                "In one or two warm, friendly sentences, identify the main subject or scene in this image "
                "(for example: 'I see you've uploaded an image of a cityscape...'). "
                "Do NOT perform any deepfake or authenticity analysis yet — that runs immediately after. "
                "End by letting the user know you're now starting the forensic analysis."
            )
            response = call_gemini_with_retry(
                client,
                model=get_settings().greeting_model,
                contents=[img, prompt],
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            )
            return GreetingResult(text=response.text.strip(), success=True)
        except Exception as e:
            logger.warning("Greeting error: %s", e)
            return GreetingResult(text=fallback, success=False)

    @staticmethod
    def build_eval_prompt(
        score: float,
        synthid: SynthIDResult,
        opencv: OpenCVComments,
        conflict: Optional["ConflictResult"] = None,
    ) -> str:
        logger.info(
            "[EvalPrompt] Building evaluation prompt with signals — "
            "AIDE score: %.4f | SynthID is_ai: %s | synthid_detected: %s | "
            "watermark_found: %s | gen_ai_tool: %s | confidence: %.4f | "
            "opencv noise: %s | edges: %s | compression: %s | conflict: %s",
            score,
            synthid.is_ai,
            synthid.synth_id_detected,
            synthid.watermark_found,
            getattr(synthid, "gen_ai_tool", "N/A"),
            synthid.confidence,
            opencv.noise,
            opencv.edges,
            opencv.compression,
            json.dumps(conflict.model_dump(), indent=2) if conflict else "None",
        )
        pct = (score or 0) * 100
        synthid_text = "SynthID Watermark Not Detected."
        if synthid.synth_id_detected or synthid.watermark_found:
            synthid_text = (
                "SynthID Watermark DETECTED. This is cryptographically proven to be "
                "AI-generated by a Google model."
            )
        opencv_text = (
            f"Noise Analysis: {opencv.noise}\n"
            f"Edge Analysis: {opencv.edges}\n"
            f"Compression Analysis: {opencv.compression}"
        )
        conflict_text = ""
        if conflict and conflict.has_conflict:
            conflict_text = (
                f"\n- Conflict Resolution: Rule {conflict.rule_triggered} triggered "
                f"({conflict.severity} severity) — {conflict.reason}"
            )

        return f"""You are a friendly digital forensics educator helping everyday people understand AI-generated content.

Our core model has assigned this image a **{pct:.1f}% probability** of being AI-generated.
Additionally, our low-level forensics tools found:
- SynthID Status: {synthid_text}
- OpenCV Features:
{opencv_text}{conflict_text}

Your job is to explain this combined result so clearly that someone with no technical background walks away both informed and more media-literate. Summarize what these tools found.

---

INSTRUCTIONS:

1. **Open with a plain-English verdict** — one sentence, no jargon.
   Example: "This image very likely wasn't captured by a real camera — here's what gave it away."

2. **Summarize the System's Findings** — In 1-2 paragraphs, explain what the Probability Score, SynthID check, and OpenCV analyses indicate.

3. **Walk through 2-3 specific visual clues you observe**, based on the findings above. Point to WHERE in the image they are and explain WHY they suggest AI generation. Rate how strong each clue is: 🔴 Strong signal / 🟡 Moderate signal / 🟢 Subtle signal.

4. **Give a "What to look for next time" tip** — teach the user one transferable skill.

5. **End with an honest confidence note** — if the probability is in the uncertain range (30–70%), say so plainly.

---

FORMATTING RULES:
- Write in warm, conversational prose.
- Use bullet points only for the clue list.
- Never use markdown headers (#), code blocks, or technical notation.
- Refer to "this image" not "the input" or "the sample."
- Keep the total response under 300 words.

DETECTION SCORE CONTEXT: {pct:.1f}%
"""

    @staticmethod
    def evaluate_image(
        image_path: str | Path,
        score: float,
        synthid: SynthIDResult,
        opencv: OpenCVComments,
        project_id: str,
        location: str,
        conflict: Optional["ConflictResult"] = None,
    ) -> EvalResult:
        """Run the agentic evaluation, returning the full text in one shot."""
        if not project_id:
            return EvalResult(
                text="",
                success=False,
                error="GCP_PROJECT_ID not set; agentic evaluation skipped.",
            )

        try:
            from PIL import Image
            from google import genai

            client = genai.Client(vertexai=True, project=project_id, location=location)
            img = Image.open(image_path)
            prompt = GeminiRouterAgent.build_eval_prompt(score, synthid, opencv, conflict)
            logger.info("[EvalAgent] Sending evaluation prompt to Gemini.")
            response = call_gemini_with_retry(
                client,
                model=get_settings().eval_model,
                contents=[img, prompt],
            )
            logger.info(
                "[EvalAgent] Gemini evaluation response:\n%s", response.text
            )
            return EvalResult(text=response.text, success=True)
        except Exception as e:
            logger.exception("Agentic LLM eval failed")
            return EvalResult(text="", success=False, error=str(e))

    @staticmethod
    def stream_evaluate_image(
        image_path: str | Path,
        score: float,
        synthid: SynthIDResult,
        opencv: OpenCVComments,
        project_id: str,
        location: str,
    ) -> Iterable[str]:
        """Yield evaluation text chunks for SSE / WebSocket streaming."""
        if not project_id:
            return

        from PIL import Image
        from google import genai

        client = genai.Client(vertexai=True, project=project_id, location=location)
        img = Image.open(image_path)
        prompt = GeminiRouterAgent.build_eval_prompt(score, synthid, opencv)
        response = call_gemini_with_retry(
            client,
            model=get_settings().eval_model,
            contents=[img, prompt],
            stream=True,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    @staticmethod
    def conversational_reply(
        user_text: str,
        history: list[dict],
        project_id: str,
        location: str,
        appendix: Optional[str] = None,
    ) -> str:
        """Open-ended chat reply using the dual-POV system prompt."""
        fallback_base = user_text.strip() if user_text else "Hello!"
        fallback = (
            f"Thanks for the message — I'm the TruthLens chatbot. {fallback_base}"
            if user_text
            else "Hi! I'm TruthLens. Upload an image and I'll analyze it for deepfakes."
        )
        if not project_id:
            logger.info("[chat] no project_id; returning fallback reply.")
            return f"{fallback}\n\n{appendix}" if appendix else fallback

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(vertexai=True, project=project_id, location=location)
            transcript_lines = []
            for m in history[-6:]:
                role_label = "User" if m.get("role") == "user" else "Agent"
                text = m.get("text") or (m.get("analysis") or {}).get("greeting") or ""
                if text:
                    transcript_lines.append(f"{role_label}: {text}")
            transcript = "\n".join(transcript_lines) if transcript_lines else "(no prior turns)"
            logger.info("[chat] user_text: %s", user_text)
            logger.info("[chat] transcript (last 6 turns):\n%s", transcript)
            prompt = (
                f"Recent conversation:\n{transcript}\n\n"
                f"User: {user_text}\n\n"
                "Reply to the latest user turn. Detect intent and answer in the single "
                "persona (technical System Owner OR humanized End-User guide) that best "
                "fits, per your system instructions. Plain prose only — no markdown headers."
            )
            if appendix:
                prompt += (
                    f"\n\nAfter your reply, on a new line, append exactly this notice verbatim:\n"
                    f"\"{appendix}\""
                )

            logger.info("[chat] prompt sent to Gemini:\n%s", prompt)

            response = call_gemini_with_retry(
                client,
                model=get_settings().eval_model,
                contents=[prompt],
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            )
            logger.info(
                "[Chat] Gemini conversational reply:\n%s", response.text
            )
            return response.text.strip()
        except Exception as e:
            logger.warning("Conversational reply error: %s", e)
            return f"{fallback}\n\n{appendix}" if appendix else fallback
