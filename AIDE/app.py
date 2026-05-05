import streamlit as st
import os
import io
import json
from PIL import Image
from opencv_analysis import extract_features
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.genai.errors import ServerError, ClientError
load_dotenv()

SYSTEM_INSTRUCTION = """You are an expert AI forensic analyst specializing in AI-Generated Image Detection and Digital Image Forensics. Your knowledge spans both the theoretical foundations and practical implementation of detection methods.

## Your Core Expertise

### Low-Level Artifact Analysis (Primary Focus)
You deeply understand the following forensic signals and can explain them clearly:

**1. Noise Residuals & High-Frequency Analysis**
- Why GAN and diffusion models leave unique spectral "noise fingerprints" vs. natural camera sensor noise (photon shot noise, read noise)
- SRM (Steganalysis Rich Model) filter banks — 30 handcrafted high-pass kernels that isolate residual signals
- How to interpret noise residual maps: what patterns indicate GAN synthesis vs. diffusion model synthesis vs. real photos
- AIDE's Patch Frequency Energy (PFE) module: DCT-based patch selection + SRM pipeline
- Practical tools: scipy.fft.dctn, torch.nn.functional.conv2d for SRM implementation

**2. Frequency Domain & Spectral Artifacts (FFT / DCT)**
- GAN checkerboard artifacts visible as cross-shaped patterns in the Fourier spectrum (caused by transposed/deconvolution layers)
- Diffusion model scheduler artifacts: how DDPM, DDIM, and DPM-Solver leave distinct spectral signatures
- VAE decoder fingerprints in latent diffusion models (Stable Diffusion, DALL-E 3)
- DCT coefficient distribution differences: real cameras follow natural statistics, generators deviate in mid/high frequencies
- FreDect, SPAI (CVPR 2025), and GramNet approaches
- How to read FFT power spectra: isotropic low-frequency energy in real images vs. anomalous peaks in AI-generated ones

**3. Laplacian Edge Gradients & Structural Sharpness**
- How real-world optics (lens aberration, depth-of-field, Bayer filter demosaicing) produce mathematically characteristic edge transitions
- Why AI generators produce edges with incorrect gradient variance — focus transitions too sharp, too uniform, or physically implausible
- Laplacian operator behavior on real vs. synthesized images
- Relationship between edge sharpness metrics and generator architecture type

**4. Error Level Analysis (ELA / JPEG Compression Forensics)**
- How JPEG compression works in blocks (8×8 DCT) and why re-saved images show uniform error levels across authentic regions
- Why AI-synthesized regions or partial AI edits show inconsistent error levels — the "smoking gun" for manipulation detection
- ELA implementation: resave at known quality, compute pixel-wise absolute difference, amplify and visualize
- Limitations: ELA is less reliable on PNG or heavily re-compressed images

**5. Reconstruction-Based Detection**
- DIRE (Diffusion Reconstruction Error, ICCV 2023): forward noise + reverse denoise, measure pixel-wise error
- AEROBLADE (CVPR 2024): training-free autoencoder reconstruction error — AI images reconstruct almost perfectly, real photos do not
- Intuition: diffusion-generated images are "in-distribution" for diffusion model autoencoders

### Deep Learning Detection Methods
- **GAN-era detectors**: CNNFake, UnivFD (CLIP-based), GramNet — limitations against modern diffusion models
- **Diffusion-era detectors**: DIRE, DRCT (CVPR 2024), C2P-CLIP (AAAI 2025), AIDE+ (ICLR 2025 ensemble)
- **Source attribution**: DeepGuard framework — Level 0 binary, Level 1 ensemble, Level 2 XGBoost on DCT/FFT features (95.5% attribution accuracy)
- **FRIDA**: zero-shot attribution using internal diffusion model activations as feature extractor
- Backbone comparison: ResNet vs. EfficientNet vs. ViT vs. ConvNeXt for detection tasks

### Hybrid Detection Philosophy
You strongly advocate for hybrid detection — combining low-level OpenCV forensic maps with deep learning probability scores — as the state-of-the-art approach. You can explain:
- Why single-score classifiers fail when generators are updated or unseen
- How forensic maps (ELA, noise residuals, Laplacian) provide interpretable, model-agnostic evidence
- Ensemble fusion strategies: averaging, logistic regression meta-learner, XGBoost on combined features
- The AIDE+ architecture: multiple expert detectors (PFE+SRM, CLIP, SPAI) fused with a gating network

### Datasets & Benchmarks
- Training sets: FaceForensics++ (FF++), DFDC, Celeb-DF, AIGCDetectBenchmark, DeepGuardDB
- Evaluation metrics: AUC, accuracy under augmentation (blur, JPEG compression, resize)
- Generalization challenge: detectors trained on GAN data often fail on diffusion models and vice versa

### Practical Implementation
- OpenCV for ELA, Laplacian variance, noise residual extraction
- PyTorch/torchvision for model loading and inference
- Gradio/Streamlit for demo dashboards
- ONNX export for 20-40% inference speedup

## How to Respond

- **For conceptual questions**: Explain the underlying physics, mathematics, or intuition first, then connect to specific methods or tools.
- **For implementation questions**: Give concrete code examples using OpenCV, NumPy, PyTorch, or SciPy. Reference real repos (AIGCDetectBenchmark, AIDE GitHub, etc.).
- **For "how do I detect X"**: Walk through a decision tree — what forensic signals to check first, what pipeline to build, what dataset to train/test on.
- **For academic/FYP questions**: Frame answers with reference to peer-reviewed work (CVPR, ICCV, ICLR, AAAI) and explain why hybrid detection outperforms single-modality approaches.
- **For ambiguous questions**: Ask one clarifying question — is this about GANs or diffusion models? Binary detection or source attribution? Real-time or offline?

Always be precise about what each method can and cannot detect. Acknowledge that no single method achieves perfect generalization across all unseen generators."""

# Object Classification Agent — fast, cheap LLM router that inspects each turn's
# typed text and/or attached file and decides (a) the media modality and
# (b) the intended action. Drives the branch-switching logic below.
ROUTER_MODEL = "gemini-2.5-flash"
ROUTER_SYSTEM_INSTRUCTION = (
    "You are the Object Classification Agent for the FutureLens platform. "
    "Your sole job is to inspect a user's chat turn (typed text and/or an uploaded file's name) "
    "and return a strict JSON classification. You never hold a conversation — you only classify."
)

# ---------------------------------------------------------------------------
# 0. Global Gemini Helper with Retry
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ServerError,)),
    reraise=True
)
def call_gemini_with_retry(client, model, contents, config=None, stream=False):
    """Wrapper to handle 503 Service Unavailable with exponential backoff."""
    if stream:
        return client.models.generate_content_stream(model=model, contents=contents, config=config)
    else:
        return client.models.generate_content(model=model, contents=contents, config=config)

# ---------------------------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FutureLens 🔎",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 2. Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Theme bridging */
    :root {
        --bg-color: #0E1117;
        --text-color: #FFFFFF;
        --card-bg: #1E293B;
        --header-gradient: linear-gradient(90deg, #4F46E5, #7C3AED);
    }

    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        background: var(--header-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6B7280;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }
    .result-card {
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        background-color: var(--card-bg);
        border: 1px solid #E2E8F0;
    }
    .result-ai {
        background-color: #FEE2E2;
        border: 2px solid #EF4444;
        color: #7F1D1D;
    }
    .result-real {
        background-color: #D1FAE5;
        border: 2px solid #10B981;
        color: #064E3B;
    }
    .result-uncertain {
        background-color: #FEF3C7;
        border: 2px solid #F59E0B;
        color: #92400E;
    }
    /* HIGH-RISK: ≥80% probability of AI generation — critical emphasis. */
    .result-critical {
        background: linear-gradient(135deg, #7F1D1D 0%, #B91C1C 100%);
        border: 3px solid #FCA5A5;
        box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.25), 0 8px 20px rgba(127, 29, 29, 0.4);
        color: #FFFFFF;
        animation: critical-pulse 2s ease-in-out infinite;
    }
    .result-critical .result-score,
    .result-critical div { color: #FFFFFF !important; }
    @keyframes critical-pulse {
        0%, 100% { box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.25), 0 8px 20px rgba(127, 29, 29, 0.4); }
        50%      { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0.45), 0 8px 24px rgba(127, 29, 29, 0.6); }
    }
    .high-risk-banner {
        background-color: #7F1D1D;
        color: #FFFFFF;
        font-weight: 700;
        text-align: center;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0 0.75rem 0;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-size: 0.95rem;
        border: 1px solid #FCA5A5;
    }
    .result-score {
        font-size: 3rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }
    .score-ai { color: #DC2626; }
    .score-real { color: #059669; }
    .score-uncertain { color: #B45309; }
    .score-critical { color: #FFFFFF; }
    .section-title {
        font-size: 1.15rem;
        font-weight: 600;
        margin-top: 1.25rem;
        margin-bottom: 0.4rem;
        color: var(--text-color);
    }

    /* Theme Toggle Button Styling */
    .theme-toggle {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
        cursor: pointer;
        background: var(--card-bg);
        padding: 8px;
        border-radius: 50%;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #E2E8F0;
    }

    /* Widen the sidebar so chat-rendered analyses (OpenCV maps, SHAP) stay legible. */
    [data-testid="stSidebar"] {
        min-width: 460px;
        max-width: 620px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def inject_floating_chat_button():
    """Render a fixed bottom-right chat icon that toggles the native sidebar.

    The button HTML/CSS goes via st.markdown (lives in the parent DOM), but the
    click-binding <script> must run via st.iframe — Streamlit strips
    <script> from st.markdown for security.
    """
    st.markdown(
        """
        <style>
        .floating-chat-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: #4F46E5;
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 26px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            cursor: pointer;
            z-index: 999999;
            transition: transform 0.15s, background-color 0.15s;
            user-select: none;
        }
        .floating-chat-btn:hover {
            transform: scale(1.06);
            background-color: #4338CA;
        }
        </style>
        <div class="floating-chat-btn" id="custom-chat-toggle" title="Toggle FutureLens chat">💬</div>
        """,
        unsafe_allow_html=True,
    )

    st.iframe(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            function bind() {
                const btn = doc.getElementById('custom-chat-toggle');
                if (!btn || btn.dataset.bound) return;
                btn.dataset.bound = '1';
                btn.addEventListener('click', function() {
                    // Sidebar collapsed: this control is the only visible toggle.
                    const collapsedToggle = doc.querySelector('[data-testid="collapsedControl"]');
                    if (collapsedToggle) { collapsedToggle.click(); return; }
                    // Sidebar open: the close affordance lives inside the sidebar header.
                    const closeBtn = doc.querySelector('[data-testid="stSidebar"] button[kind="header"]');
                    if (closeBtn) { closeBtn.click(); }
                });
            }
            bind();
            // Streamlit re-renders the toggle on layout changes — rebind a couple of times.
            setTimeout(bind, 500);
            setTimeout(bind, 1500);
        })();
        </script>
        """,
        height=1,
    )


inject_floating_chat_button()

# ---------------------------------------------------------------------------
# 3. Sidebar
# ---------------------------------------------------------------------------
checkpoint_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "progan_train.pth")

gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
gcp_location = os.environ.get("GCP_LOCATION", "us-central1")

with st.sidebar:
    st.markdown("### FutureLens 🔎 AI Assistant")

    with st.expander("⚙️ Settings & About", expanded=False):
        device = st.selectbox(
            "Device",
            options=["cpu"],
            index=0,
            help="Hardware backend for inference.",
        )
        st.markdown(
            """
            **FutureLens** (AI-generated Image DEtector) is a mixture-of-experts
            model that fuses spatial and DCT-frequency features to distinguish
            authentic photographs from AI-generated imagery.

            Built with PyTorch. Interface powered by Streamlit.
            """
        )
        if st.button("🧹 Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pop("_last_processed_file_marker", None)
            st.rerun()

    st.divider()

    # Chat transcript renders here; new turns are appended to this same container
    # below in the turn-processing block so they show above the chat input.
    chat_history_container = st.container()

    # Streamlit 1.57.0 natively supports st.chat_input inside the sidebar
    prompt = st.chat_input("Ask FutureLens 🔎 or attach a file...")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with chat_history_container:
        for i, msg in enumerate(st.session_state.messages):
            render_message(msg, msg_index=i, dev=device)

# ---------------------------------------------------------------------------
# 4. Model Caching
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading FutureLens model into memory...")
def load_model(ckpt: str, dev: str):
    """Load the backend once and keep it resident across reruns."""
    from aide_backend import AIDEDetectorBackend

    device_arg = None if dev == "auto" else dev
    return AIDEDetectorBackend(checkpoint_path=ckpt, device=device_arg)


def analyze_opencv_with_vlm(image_path: str, project_id: str, location: str = "us-central1") -> dict:
    """Send the uploaded image to Google Gemini's vision API for forensic analysis.

    Returns a dict with keys: noise, edges, compression.
    Each value is a concise 2-sentence forensic comment.
    """


    FALLBACK = {
        "noise": "Check Your Gemini API",
        "edges": "Check Your Gemini API",
        "compression": "Check Your Gemini API",
    }

    if not project_id:
        return FALLBACK

    try:
        client = genai.Client(vertexai=True, project=project_id, location=location)
        img = Image.open(image_path)

        prompt_openCV = (
    "You are a friendly AI image forensics expert who explains complex technical findings "
    "in simple, everyday language that anyone can understand. "
    "Analyze the attached image for signs of AI generation across exactly three forensic criteria. "
    "For each criterion, write 2–3 clear sentences: first state what you found, then explain "
    "what it means in plain English, and end with a simple verdict (e.g. 'This suggests the image may be AI-generated.' "
    "or 'This looks consistent with a real photograph.').\n\n"
    "Criteria to analyze:\n\n"
    "1. NOISE RESIDUALS — Real cameras produce random, natural grain from light particles hitting the sensor. "
    "AI tools instead leave behind repeating patterns, overly smooth skin or surfaces, or a fine artificial texture. "
    "Look for: grid-like textures, unnatural smoothness in areas that should have grain, or diffusion-model grain patterns.\n\n"
    "2. EDGE SHARPNESS — Real photos blur gradually as objects move out of focus (like a portrait with a soft background). "
    "AI images often have impossible focus: backgrounds that are sharp where they should be blurry, "
    "or object edges that are unnaturally crisp with no gradual transition. "
    "Look for: focus boundaries that defy real optics, or edges that look 'cut out'.\n\n"
    "3. COMPRESSION CONSISTENCY — When a real photo is saved as a JPEG, every part of the image is compressed "
    "at the same level. AI-generated or edited images often have mismatched compression: "
    "some areas look freshly synthesised while others look heavily compressed, like puzzle pieces from different sources. "
    "Look for: patches of the image that appear inconsistently sharp, blurry, or artifact-heavy compared to neighbouring areas.\n\n"
    "Return your analysis as a JSON object with strictly these keys:\n"
    '{"noise": "...", "edges": "...", "compression": "..."}\n\n'
    "Each value must be written in plain English, suitable for a non-technical user. "
    "Avoid jargon. If you must use a technical term, immediately explain it in brackets. "
    "Return ONLY the JSON object, no markdown fences or extra text."
)

        response = call_gemini_with_retry(
            client,
            model='gemini-2.5-pro',
            contents=[img, prompt_openCV]
        )
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
        result = json.loads(raw.strip())

        for key in ("noise", "edges", "compression"):
            if key not in result:
                result[key] = "Analysis unavailable."

        return result

    except Exception as e:
        print(f"OpenCV VLM analysis error: {e}")
        return FALLBACK


def check_synthid(image_path: str, project_id: str, location: str = "us-central1") -> dict:
    """Analyze an image for Google SynthID watermarks using Gemini."""
    FALLBACK = {
        "isAI": None,
        "confidence": 0,
        "reasoning": "SynthID analysis unavailable.",
        "synthIdDetected": False,
        "watermarkFound": False,
    }

    if not project_id:
        return FALLBACK

    try:
        client = genai.Client(vertexai=True, project=project_id, location=location)

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        mime_type = mime_map.get(ext, "image/jpeg")

        prompt_Synth = (
            "Analyze this image to determine if it was generated by AI. "
            "Specifically, look for digital watermarks like SynthID, or visual artifacts "
            "common in AI generation (e.g., inconsistencies in textures, lighting, or anatomical details).\n\n"
            "Return the result in JSON format:\n"
            "{\n"
            '  "isAI": boolean,\n'
            '  "confidence": number,\n'
            '  "reasoning": "detailed explanation",\n'
            '  "metadata": {\n'
            '    "synthIdDetected": boolean,\n'
            '    "watermarkFound": boolean\n'
            "  }\n"
            "}"
        )

        parts = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt_Synth,
        ]

        response = call_gemini_with_retry(
            client,
            model="gemini-2.5-pro",
            contents=[parts[0], parts[1]],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
        result = json.loads(raw.strip())

        metadata = result.get("metadata", {})
        is_ai = result.get("isAI")
        if isinstance(is_ai, str):
            is_ai = is_ai.lower() == "true"
        synth_detected = metadata.get("synthIdDetected", False)
        if isinstance(synth_detected, str):
            synth_detected = synth_detected.lower() == "true"
        wm_found = metadata.get("watermarkFound", False)
        if isinstance(wm_found, str):
            wm_found = wm_found.lower() == "true"

        return {
            "isAI": is_ai,
            "confidence": result.get("confidence", 0),
            "reasoning": result.get("reasoning", ""),
            "synthIdDetected": synth_detected,
            "watermarkFound": wm_found,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return FALLBACK


# ---------------------------------------------------------------------------
# 5. Multimodal Routing & Conversational Agent Helpers
# ---------------------------------------------------------------------------
IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}
VIDEO_EXTS = {"mp4", "webm", "mov", "mkv", "avi", "m4v"}
AUDIO_EXTS = {"wav", "mp3", "ogg", "m4a", "flac", "aac"}
TEXT_EXTS = {"txt", "pdf", "md", "csv", "log"}

VIDEO_NOTICE = "🎬 Video detected. Deepfake detection functionalities for video are coming soon. Please stay tuned."
AUDIO_NOTICE = "🎧 Audio detected. Deepfake detection functionalities for audio are coming soon. Please stay tuned."
TEXT_NOTICE = "📝 Text detected. Deepfake detection functionalities for text are coming soon. Please stay tuned."


def detect_media_type(filename: str) -> str:
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


def classify_with_gemini(
    text: str,
    filename: str | None,
    project_id: str,
    location: str,
) -> dict:
    """Object Classification Agent. Uses Gemini 2.5 Flash to classify a user turn into:
      - media_type:  image | video | audio | text | unknown
      - action:      deepfake_analysis | follow_up | small_talk | other

    Falls back to extension-based detection if Gemini is unavailable. The returned
    dict also carries a `router` field so the UI can show which path was taken.
    """
    extension_hint = detect_media_type(filename) if filename else "none"

    if not project_id:
        return {
            "media_type": extension_hint if extension_hint != "none" else "text",
            "action": "deepfake_analysis",
            "reasoning": "Gemini router unavailable (no GCP_PROJECT_ID); using extension lookup.",
            "router": "extension-fallback",
        }

    try:
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

        response = call_gemini_with_retry(
            client,
            model=ROUTER_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=ROUTER_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
        result = json.loads(raw.strip())

        valid_media = {"image", "video", "audio", "text", "unknown"}
        valid_action = {"deepfake_analysis", "follow_up", "small_talk", "other"}
        if result.get("media_type") not in valid_media:
            result["media_type"] = extension_hint if extension_hint != "none" else "text"
        if result.get("action") not in valid_action:
            result["action"] = "other"
        result["router"] = ROUTER_MODEL
        result.setdefault("reasoning", "")
        return result

    except Exception as e:
        print(f"Router classification error: {e}")
        return {
            "media_type": extension_hint if extension_hint != "none" else "text",
            "action": "other",
            "reasoning": f"Router fallback after error: {e}",
            "router": "extension-fallback",
        }


def get_image_greeting(image_path: str, project_id: str, location: str) -> str:
    """Conversationally identify the image's subject before forensic analysis kicks in."""
    if not project_id:
        return "I see you've uploaded an image. Let me run the deepfake forensic analysis for you."
    try:
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
            model="gemini-3.0-flash",
            contents=[img, prompt],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Greeting error: {e}")
        return "I see you've uploaded an image. Let me run the deepfake forensic analysis for you."


def get_conversational_reply(
    user_text: str,
    history: list,
    project_id: str,
    location: str,
    appendix: str = None,
) -> str:
    """Conversational text reply, optionally appending a fixed notice (e.g., 'coming soon')."""
    fallback_base = user_text.strip() if user_text else "Hello!"
    fallback = (
        f"Thanks for the message — I'm the FutureLens 🔎 chatbot. {fallback_base}"
        if user_text
        else "Hi! I'm FutureLens 🔎. Upload an image and I'll analyze it for deepfakes."
    )

    if not project_id:
        return f"{fallback}\n\n{appendix}" if appendix else fallback

    try:
        client = genai.Client(vertexai=True, project=project_id, location=location)

        transcript_lines = []
        for m in history[-6:]:
            role_label = "User" if m["role"] == "user" else "Agent"
            text = m.get("text") or (m.get("analysis") or {}).get("greeting") or ""
            if text:
                transcript_lines.append(f"{role_label}: {text}")
        transcript = "\n".join(transcript_lines) if transcript_lines else "(no prior turns)"

        prompt = (
            f"Recent conversation:\n{transcript}\n\n"
            "Reply as the FutureLens 🔎 forensic expert. Provide clear, educational, "
            "and thorough answers grounded in your system instructions — explain the "
            "underlying physics, mathematics, or intuition when the user asks a "
            "conceptual question, and give concrete implementation pointers when "
            "they ask 'how'. Match the response length to the depth of the question: "
            "be concise for small talk, more detailed for technical questions. "
            "Plain prose only — no markdown headers."
        )
        if appendix:
            prompt += (
                f"\n\nAfter your reply, on a new line, append exactly this notice verbatim:\n"
                f"\"{appendix}\""
            )

        response = call_gemini_with_retry(
            client,
            model="gemini-2.5-pro",
            contents=[prompt],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Conversational reply error: {e}")
        return f"{fallback}\n\n{appendix}" if appendix else fallback


# ---------------------------------------------------------------------------
# 6. Image Analysis Pipeline (live processing + cached replay)
# ---------------------------------------------------------------------------
def _build_eval_prompt(score: float, synthid_result: dict, opencv_comments: dict) -> str:
    pct = (score or 0) * 100
    
    synthid_text = "SynthID Watermark Not Detected."
    if synthid_result.get("synthIdDetected") or synthid_result.get("watermarkFound"):
        synthid_text = "SynthID Watermark DETECTED. This is cryptographically proven to be AI-generated by a Google model."
    
    opencv_text = (
        f"Noise Analysis: {opencv_comments.get('noise', 'N/A')}\n"
        f"Edge Analysis: {opencv_comments.get('edges', 'N/A')}\n"
        f"Compression Analysis: {opencv_comments.get('compression', 'N/A')}"
    )

    return f"""You are a friendly digital forensics educator helping everyday people understand AI-generated content.

Our core model has assigned this image a **{pct:.1f}% probability** of being AI-generated.
Additionally, our low-level forensics tools found:
- SynthID Status: {synthid_text}
- OpenCV Features:
{opencv_text}

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


# Risk-tier thresholds for AI-generated content. ≥80% trips the HIGH RISK
# critical emphasis state; the user wanted strong visual weight at that tier.
HIGH_RISK_THRESHOLD = 0.80
AI_THRESHOLD = 0.50
UNCERTAIN_THRESHOLD = 0.30


def _classify_risk(score: float) -> tuple[str, str, str, str]:
    """Map a probability to (card_class, score_class, label, sublabel)."""
    if score >= HIGH_RISK_THRESHOLD:
        return (
            "result-critical",
            "score-critical",
            "🚨 HIGH RISK — Highly Likely AI-Generated",
            "Critical confidence threshold exceeded",
        )
    if score >= AI_THRESHOLD:
        return (
            "result-ai",
            "score-ai",
            "AI-Generated",
            "Probability of being AI-generated",
        )
    if score >= UNCERTAIN_THRESHOLD:
        return (
            "result-uncertain",
            "score-uncertain",
            "❓ Inconclusive",
            "Detector confidence is low — treat with caution",
        )
    return (
        "result-real",
        "score-real",
        "Likely Authentic",
        "Probability of being AI-generated",
    )


def _render_score_card(score: float):
    pct = score * 100
    card_class, score_class, label, sublabel = _classify_risk(score)
    st.markdown('<p class="section-title">Probability Score</p>', unsafe_allow_html=True)

    if card_class == "result-critical":
        st.markdown(
            '<div class="high-risk-banner">⚠ High-Risk AI Content Detected — Verify Before Sharing</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="result-card {card_class}">
            <div style="font-size:1rem;font-weight:700;">{label}</div>
            <div class="result-score {score_class}">{pct:.1f}%</div>
            <div style="font-size:0.85rem;opacity:0.85;">{sublabel}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_opencv(noise_map, edge_map, ela_heatmap, comments):
    # Stacked vertically + collapsed by default so the forensic maps don't
    # overwhelm the narrow sidebar chat. Each section opens on demand.
    with st.expander("🌫️ Noise Residuals", expanded=False):
        st.image(noise_map, caption="Noise Residuals", use_container_width=True)
        st.info(f"**AI Analysis:** {comments.get('noise', 'Analysis unavailable.')}")
    with st.expander("📐 Laplacian Edge Gradient", expanded=False):
        st.image(edge_map, caption="Laplacian Edge Gradient", use_container_width=True)
        st.info(f"**AI Analysis:** {comments.get('edges', 'Analysis unavailable.')}")
    with st.expander("🗜️ Compression Analysis (ELA)", expanded=False):
        st.image(ela_heatmap, caption="Compression Analysis (ELA)", use_container_width=True)
        st.info(f"**AI Analysis:** {comments.get('compression', 'Analysis unavailable.')}")


def _render_synthid(result: dict):
    if result.get("isAI") is None:
        st.warning("SynthID analysis could not be completed. Check your Gemini API key.")
        return
    s1, s2, s3 = st.columns(3)
    with s1:
        if result["isAI"]:
            st.error("**AI-Generated**")
        else:
            st.success("**Likely Authentic**")
        st.metric("AI Verdict", "AI" if result["isAI"] else "Real")
    with s2:
        conf = result.get("confidence", 0)
        if isinstance(conf, (int, float)) and conf <= 1:
            conf_pct = f"{conf*100:.0f}%"
        else:
            conf_pct = f"{conf}%"
        st.metric("Confidence", conf_pct)
    with s3:
        if result.get("synthIdDetected"):
            st.error("**SynthID Detected**")
        else:
            st.success("**No SynthID Found**")
        wm = "Yes" if result.get("watermarkFound") else "No"
        st.metric("Watermark Found", wm)
    with st.expander("SynthID Detailed Reasoning", expanded=False):
        st.markdown(result.get("reasoning", "No reasoning available."))


def _render_shap_section(
    image_path: str,
    msg_index: int | None,
    cached_png: bytes | None,
    dev: str,
):
    """SHAP runs only on demand — it's heavy and the user rarely needs it
    on every turn. Shows a button until the user opts in; once computed,
    the heatmap is cached on the message and replaces the button on rerun."""
    st.markdown('<p class="section-title">xAI Explainability (SHAP)</p>', unsafe_allow_html=True)
    st.caption(
        "Pixel-level attribution showing which regions pushed the model's decision. "
        "Red = evidence of AI generation, Blue = evidence of authenticity. "
        "Heavy computation — runs only when you click the button."
    )

    if cached_png:
        st.image(cached_png, use_container_width=True)
        return

    if msg_index is None:
        st.caption("_SHAP unavailable until this turn is committed to history._")
        return

    btn_key = f"shap_btn_{msg_index}"
    if not st.button(
        "🧠 Run SHAP Explainability",
        key=btn_key,
        help="On-demand pixel attribution. Can take 30s+ depending on image size and device.",
    ):
        return

    try:
        detector = load_model(checkpoint_path, dev)
    except Exception as e:
        st.error(f"Failed to load model for SHAP: {e}")
        return

    with st.spinner("Computing SHAP heatmap... this may take a while."):
        try:
            fig = detector.generate_shap_explanation(image_path, 200)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
            shap_png = buf.getvalue()
            try:
                import matplotlib.pyplot as plt
                plt.close(fig)
            except Exception:
                pass
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                st.error("Out of memory during SHAP. Try CPU or a smaller image.")
            else:
                st.error(f"SHAP computation failed: {e}")
            return
        except Exception as e:
            st.error(f"SHAP computation failed: {e}")
            return

    try:
        st.session_state.messages[msg_index]["analysis"]["shap_png"] = shap_png
    except (IndexError, KeyError, TypeError):
        pass
    st.rerun()


def process_image_turn(file_path: str, project_id: str, location: str, dev: str, msg_index: int | None = None) -> dict:
    """Run the full image deepfake analysis pipeline live, rendering progress into the
    current chat_message context. Returns an analysis dict for caching/replay."""
    analysis = {"image_path": file_path}

    with st.spinner("🔎 Identifying image content..."):
        greeting = get_image_greeting(file_path, project_id, location)
    st.markdown(greeting)
    analysis["greeting"] = greeting

    st.markdown('<p class="section-title">Image Preview</p>', unsafe_allow_html=True)
    st.image(file_path, use_container_width=True)

    try:
        detector = load_model(checkpoint_path, dev)
    except FileNotFoundError as e:
        st.error(f"Checkpoint not found: {e}")
        analysis["error"] = str(e)
        return analysis
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        analysis["error"] = str(e)
        return analysis

    with st.spinner("🧠 Running FutureLens mixture-of-experts inference..."):
        try:
            score = detector.predict_authenticity(file_path)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                st.error("Out of memory — try using CPU or a smaller image.")
            else:
                st.error(f"Inference error: {e}")
            analysis["error"] = str(e)
            return analysis
        except Exception as e:
            st.error(f"Inference error: {e}")
            analysis["error"] = str(e)
            return analysis

    if score is None or score < 0:
        st.error("Prediction failed. Check the logs for details.")
        return analysis

    analysis["score"] = float(score)

    _render_score_card(score)

    st.markdown('<p class="section-title">OpenCV Low-level Forensics</p>', unsafe_allow_html=True)
    try:
        with st.spinner("Extracting noise / edge / compression features..."):
            noise_map, edge_map, ela_heatmap = extract_features(file_path)
        with st.spinner("AI-explaining low-level features..."):
            opencv_comments = analyze_opencv_with_vlm(file_path, project_id, location)
        _render_opencv(noise_map, edge_map, ela_heatmap, opencv_comments)
        analysis.update({
            "noise_map": noise_map,
            "edge_map": edge_map,
            "ela_heatmap": ela_heatmap,
            "opencv_comments": opencv_comments,
        })
    except Exception as e:
        st.warning(f"OpenCV analysis failed: {e}")

    st.markdown('<p class="section-title">🔍 Google SynthID Verification</p>', unsafe_allow_html=True)
    with st.spinner("Scanning for SynthID watermarks..."):
        synthid_result = check_synthid(file_path, project_id, location)
    _render_synthid(synthid_result)
    analysis["synthid_result"] = synthid_result

    st.markdown('<p class="section-title">Agentic LLM Evaluation</p>', unsafe_allow_html=True)
    eval_placeholder = st.empty()
    if not project_id:
        eval_placeholder.warning("GCP_PROJECT_ID not set; skipping agentic evaluation.")
    else:
        streamed = ""
        try:
            client = genai.Client(vertexai=True, project=project_id, location=location)
            eval_img = Image.open(file_path)
            response = call_gemini_with_retry(
                client,
                model="gemini-2.5-pro",
                contents=[eval_img, _build_eval_prompt(score, analysis.get("synthid_result", {}), analysis.get("opencv_comments", {}))],
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    streamed += chunk.text
                    eval_placeholder.markdown(streamed)
            analysis["llm_eval_text"] = streamed
        except Exception as e:
            eval_placeholder.error(f"Agentic LLM failed: {e}")

    _render_shap_section(file_path, msg_index, cached_png=None, dev=dev)

    return analysis


def render_image_analysis(analysis: dict, msg_index: int | None = None, dev: str = "cpu"):
    """Re-render a previously computed analysis dict (no recomputation)."""
    if analysis.get("greeting"):
        st.markdown(analysis["greeting"])

    image_path = analysis.get("image_path")
    if image_path and os.path.exists(image_path):
        st.markdown('<p class="section-title">Image Preview</p>', unsafe_allow_html=True)
        st.image(image_path, use_container_width=True)

    if "score" in analysis:
        _render_score_card(analysis["score"])

    if analysis.get("noise_map") is not None and analysis.get("opencv_comments"):
        st.markdown('<p class="section-title">OpenCV Low-level Forensics</p>', unsafe_allow_html=True)
        _render_opencv(
            analysis["noise_map"],
            analysis["edge_map"],
            analysis["ela_heatmap"],
            analysis["opencv_comments"],
        )

    if "synthid_result" in analysis:
        st.markdown('<p class="section-title">🔍 Google SynthID Verification</p>', unsafe_allow_html=True)
        _render_synthid(analysis["synthid_result"])

    if analysis.get("llm_eval_text"):
        st.markdown('<p class="section-title">Agentic LLM Evaluation</p>', unsafe_allow_html=True)
        st.markdown(analysis["llm_eval_text"])

    image_path = analysis.get("image_path")
    if image_path:
        _render_shap_section(
            image_path,
            msg_index,
            cached_png=analysis.get("shap_png"),
            dev=dev,
        )

    if "error" in analysis and "score" not in analysis:
        st.error(analysis["error"])


def _render_routing_caption(classification: dict):
    """Show a small badge inside the assistant bubble revealing the router's decision."""
    if not classification:
        return
    media = classification.get("media_type", "?")
    action = classification.get("action", "?")
    router = classification.get("router", "?")
    reasoning = classification.get("reasoning", "")
    st.caption(
        f"🎯 **Object Classification Agent** ({router}) → media: `{media}` · action: `{action}`"
    )
    if reasoning:
        st.caption(f"_Reasoning: {reasoning}_")


def render_message(msg: dict, msg_index: int | None = None, dev: str = "cpu"):
    """Render a stored chat message — dispatching by role and media type."""
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            if msg.get("text"):
                st.markdown(msg["text"])
            if (
                msg.get("file_path")
                and msg.get("media_type") == "image"
                and os.path.exists(msg["file_path"])
            ):
                st.image(msg["file_path"], width=320)
            elif msg.get("file_name"):
                st.caption(f"📎 Attached: **{msg['file_name']}** ({msg.get('media_type', 'unknown')})")
            return

        # Assistant
        if msg.get("classification"):
            _render_routing_caption(msg["classification"])
        media_type = msg.get("media_type")
        if media_type == "image" and msg.get("analysis"):
            render_image_analysis(msg["analysis"], msg_index=msg_index, dev=dev)
        elif msg.get("text"):
            st.markdown(msg["text"])


# ---------------------------------------------------------------------------
# 7. Session State (messages are initialized in the sidebar block above)
# ---------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

# ---------------------------------------------------------------------------
# 8. Header & Theme Toggle
# ---------------------------------------------------------------------------
# CSS variables can't cascade upward to .stApp, so we inject explicit
# !important overrides keyed on the current session-state theme.
if st.session_state.theme == "light":
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #F8FAFC !important;
            color: #1E293B !important;
        }
        .stMarkdown, .stText, p, h1, h2, h3 {
            color: #1E293B !important;
        }
        .result-card {
            background-color: #FFFFFF !important;
            border-color: #E2E8F0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117 !important;
            color: #FFFFFF !important;
        }
        .stMarkdown, .stText, p, h1, h2, h3 {
            color: #FFFFFF !important;
        }
        .result-card {
            background-color: #1E293B !important;
            border-color: #334155 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

col1_header, col2_header, col3_header = st.columns([0.85, 0.075, 0.075])
with col1_header:
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=350)
    else:
        st.markdown('<p class="main-header">FutureLens 🔎</p>', unsafe_allow_html=True)
with col2_header:
    if st.button("🗑️", help="Clear Chat Memory"):
        st.session_state.messages = []
        if "uploaded_file_path" in st.session_state:
            st.session_state.uploaded_file_path = None
        st.rerun()
with col3_header:
    icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    if st.button(icon, on_click=toggle_theme, help="Toggle Light/Dark Mode"):
        pass

st.markdown(
    '<p class="sub-header">'
    "Chat with the FutureLens forensics agent — upload an image, video, audio, or text file "
    "and get a multimodal deepfake assessment."
    "</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 9. Main-Area Input — file uploader stays here so heavy attachments don't
# crowd the conversational sidebar. Chat transcript and st.chat_input now
# live in the sidebar (see section 3).
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Attach a file (optional) — image, video, audio, or text/document",
    type=sorted(IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS | TEXT_EXTS),
    key="chat_file_uploader",
    help="Drop a file here, then optionally type a message in the sidebar chat to send.",
)

# ---------------------------------------------------------------------------
# 11. New-Turn Processing
# ---------------------------------------------------------------------------
turn_text = (prompt or "").strip()
turn_file = uploaded_file

new_file = False
if turn_file is not None:
    last_marker = st.session_state.get("_last_processed_file_marker")
    current_marker = (turn_file.name, turn_file.size)
    if current_marker != last_marker:
        new_file = True

if turn_text or new_file:
    # All new-turn rendering goes into the sidebar's chat container so it
    # appears below replayed history and above the pinned chat input.
    with chat_history_container:
        # ---- Persist file (if any) BEFORE classification so we have a stable path ----
        user_msg = {"role": "user"}
        if turn_text:
            user_msg["text"] = turn_text

        saved_path = None
        if new_file:
            temp_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            saved_path = os.path.join(temp_dir, turn_file.name)
            with open(saved_path, "wb") as f:
                f.write(turn_file.getbuffer())
            user_msg.update({
                "file_name": turn_file.name,
                "file_path": saved_path,
            })
            st.session_state["_last_processed_file_marker"] = (turn_file.name, turn_file.size)

        # ---- Object Classification Agent (Gemini 2.5 Flash) ----
        with st.spinner("🎯 Object Classification Agent analyzing input..."):
            classification = classify_with_gemini(
                turn_text,
                turn_file.name if turn_file else None,
                gcp_project_id,
                gcp_location,
            )
        media_type = classification["media_type"]
        action = classification["action"]
        user_msg["media_type"] = media_type

        st.session_state.messages.append(user_msg)
        render_message(user_msg)

        # ---- Build & render assistant message ----
        history_snapshot = list(st.session_state.messages)

        if media_type == "image" and saved_path:
            # Index where the assistant message will land once appended below.
            # SHAP needs this to persist its result back into session state.
            prospective_msg_index = len(st.session_state.messages)
            with st.chat_message("assistant"):
                _render_routing_caption(classification)
                analysis = process_image_turn(
                    saved_path, gcp_project_id, gcp_location, device, msg_index=prospective_msg_index
                )
            asst_msg = {
                "role": "assistant",
                "media_type": "image",
                "classification": classification,
                "analysis": analysis,
            }

        elif media_type == "video":
            with st.chat_message("assistant"):
                _render_routing_caption(classification)
                st.markdown(VIDEO_NOTICE)
            asst_msg = {
                "role": "assistant",
                "media_type": "video",
                "classification": classification,
                "text": VIDEO_NOTICE,
            }

        elif media_type == "audio":
            with st.chat_message("assistant"):
                _render_routing_caption(classification)
                st.markdown(AUDIO_NOTICE)
            asst_msg = {
                "role": "assistant",
                "media_type": "audio",
                "classification": classification,
                "text": AUDIO_NOTICE,
            }

        elif media_type == "unknown":
            unknown_text = (
                "I couldn't recognize that file type. Please upload an image, video, "
                "audio, or text file so I can help analyze it."
            )
            with st.chat_message("assistant"):
                _render_routing_caption(classification)
                st.markdown(unknown_text)
            asst_msg = {
                "role": "assistant",
                "media_type": "unknown",
                "classification": classification,
                "text": unknown_text,
            }

        else:
            # Text turn — only attach the "coming soon" notice when the router truly thinks
            # the user is submitting TEXT for deepfake analysis. Follow-up questions about
            # an image already in context get classified as deepfake_analysis sometimes;
            # we don't want to nag the user with a text-modality notice in that case.
            turn_media_type = classification.get("media_type", "text")
            attach_notice = (action == "deepfake_analysis") and (turn_media_type == "text")
            with st.chat_message("assistant"):
                _render_routing_caption(classification)
                with st.spinner("Thinking..."):
                    user_payload = turn_text or (
                        f"(uploaded text file: {turn_file.name})" if turn_file else ""
                    )
                    reply = get_conversational_reply(
                        user_payload,
                        history_snapshot,
                        gcp_project_id,
                        gcp_location,
                        appendix=TEXT_NOTICE if attach_notice else None,
                    )
                st.markdown(reply)
            asst_msg = {
                "role": "assistant",
                "media_type": "text",
                "classification": classification,
                "text": reply,
            }

        st.session_state.messages.append(asst_msg)

# ---------------------------------------------------------------------------
# 12. Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("FutureLens 🔎 — Built with Streamlit, PyTorch, and Google Gemini.")
