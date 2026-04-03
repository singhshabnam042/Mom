"""
app.py
======
MoM Generator Bot - Streamlit Web Application
Meeting recordings (video/audio) ko upload karo aur
automatically structured Minutes of Meeting (MoM) generate karo.

Run: streamlit run app.py
"""

import os
import sys
import time
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.audio_extractor import AudioExtractor, ALL_SUPPORTED_FORMATS, SUPPORTED_VIDEO_FORMATS
from src.transcriber import Transcriber
from src.summarizer import MoMSummarizer
from src.document_generator import DocumentGenerator
from src.utils import ensure_dirs, format_duration, get_file_size_mb, setup_logging

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Ensure output directories exist
ensure_dirs("outputs", "uploads")

# ──────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="MoM Generator Bot 🎙️",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Main container */
    .main { padding-top: 1rem; }

    /* Header */
    .header-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1f497d, #2980b9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .header-sub {
        text-align: center;
        color: #7f8c8d;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    /* Section cards */
    .section-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border-left: 5px solid #2980b9;
        margin-bottom: 1rem;
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-success { background: #d5f5e3; color: #1e8449; }
    .badge-warning { background: #fdebd0; color: #d68910; }

    /* Download buttons */
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# Session State Initialization
# ──────────────────────────────────────────────
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "mom_text" not in st.session_state:
    st.session_state.mom_text = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "duration" not in st.session_state:
    st.session_state.duration = 0.0
if "processing_done" not in st.session_state:
    st.session_state.processing_done = False


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown('<div class="header-title">🎙️ MoM Generator Bot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="header-sub">Meeting recording upload karo → Auto MoM milega in seconds!</div>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# Sidebar Configuration
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    st.divider()

    # API Key
    api_key = st.text_input(
        "🔑 OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="OpenAI API key. Get it from: platform.openai.com/api-keys",
    )

    # Model selection
    gpt_model = st.selectbox(
        "🤖 GPT Model",
        options=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        index=0,
        help="GPT-4 best accuracy deta hai. GPT-3.5 faster & cheaper hai.",
    )

    whisper_model = st.selectbox(
        "🎤 Whisper Model",
        options=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        index=3,  # medium default
        help="Medium/Large Hindi ke liye better hai. Tiny/Base fast hain.",
    )

    language_option = st.selectbox(
        "🌐 Language",
        options=["Auto-detect", "Hindi (hi)", "English (en)", "Hinglish (auto)"],
        index=0,
        help="Auto-detect zyada tar sahi kaam karta hai.",
    )

    st.divider()
    st.markdown("### 📖 About")
    st.markdown(
        """
        **MoM Generator Bot** meeting recordings ko
        structured Minutes of Meeting mein convert karta hai.

        **Features:**
        - 🎬 Video + Audio support
        - 🗣️ Hindi + English + Hinglish
        - ⏰ 2+ hour meetings
        - 📄 PDF, Word, Markdown export
        """
    )

    st.divider()
    st.caption("Made with ❤️ using Whisper + GPT-4")


# ──────────────────────────────────────────────
# Main Content
# ──────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

# ─── Left Column: Upload ──────────────────────
with col1:
    st.subheader("📁 Upload Meeting Recording")

    uploaded_file = st.file_uploader(
        "Video ya Audio file drag & drop karo",
        type=[
            "mp4", "mkv", "avi", "mov", "webm",   # Video
            "mp3", "wav", "m4a", "ogg", "flac",    # Audio
        ],
        help="Supported: MP4, MKV, AVI, MOV, WEBM, MP3, WAV, M4A, OGG, FLAC",
    )

    if uploaded_file:
        # Display file info
        file_size_mb = len(uploaded_file.getvalue()) / 1024 / 1024
        st.markdown(
            f"""
            <div class="section-card">
            📎 <b>{uploaded_file.name}</b><br>
            📦 Size: {file_size_mb:.1f} MB &nbsp;|&nbsp;
            🎞️ Type: {uploaded_file.type}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Validate API key
        if not api_key:
            st.warning("⚠️ OpenAI API key enter karo (sidebar mein).")

        # Process button
        if st.button(
            "🚀 Generate MoM",
            type="primary",
            disabled=not api_key,
            use_container_width=True,
        ):
            _run_pipeline(
                uploaded_file=uploaded_file,
                api_key=api_key,
                gpt_model=gpt_model,
                whisper_model=whisper_model,
                language_option=language_option,
            )

# ─── Right Column: Results ────────────────────
with col2:
    st.subheader("📋 Generated MoM")

    if st.session_state.mom_text:
        # Show success badge
        st.markdown(
            '<span class="status-badge badge-success">✅ MoM Ready</span>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        # MoM preview
        with st.expander("👀 Preview MoM", expanded=True):
            st.markdown(st.session_state.mom_text)

        st.divider()
        st.markdown("### 💾 Download")

        # Generate and offer downloads
        gen = DocumentGenerator(output_dir="outputs")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # PDF Download
        try:
            pdf_path = gen.to_pdf(st.session_state.mom_text, filename=f"MoM_{timestamp}")
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download PDF",
                    data=f.read(),
                    file_name=f"MoM_{timestamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"PDF error: {e}")

        # DOCX Download
        try:
            docx_path = gen.to_docx(st.session_state.mom_text, filename=f"MoM_{timestamp}")
            with open(docx_path, "rb") as f:
                st.download_button(
                    label="📝 Download Word (.docx)",
                    data=f.read(),
                    file_name=f"MoM_{timestamp}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"DOCX error: {e}")

        # Markdown Download
        md_content = f"# Minutes of Meeting\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n---\n\n{st.session_state.mom_text}"
        st.download_button(
            label="📃 Download Markdown",
            data=md_content.encode("utf-8"),
            file_name=f"MoM_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        # Transcript download
        if st.session_state.transcript:
            st.divider()
            with st.expander("📜 View Full Transcript"):
                st.text_area(
                    "Transcript",
                    value=st.session_state.transcript,
                    height=300,
                    label_visibility="collapsed",
                )
            st.download_button(
                label="📜 Download Transcript (.txt)",
                data=st.session_state.transcript.encode("utf-8"),
                file_name=f"Transcript_{timestamp}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    elif not uploaded_file:
        st.info("👈 Pehle recording upload karo aur 'Generate MoM' dabao.")
    else:
        st.info("⏳ File upload ki hai - ab 'Generate MoM' button dabao!")


# ──────────────────────────────────────────────
# Pipeline Function
# ──────────────────────────────────────────────
def _run_pipeline(
    uploaded_file,
    api_key: str,
    gpt_model: str,
    whisper_model: str,
    language_option: str,
) -> None:
    """
    Complete MoM generation pipeline run karta hai:
    Upload → Extract Audio → Transcribe → Generate MoM
    """
    # Determine language code
    lang_map = {
        "Auto-detect": None,
        "Hinglish (auto)": None,
        "Hindi (hi)": "hi",
        "English (en)": "en",
    }
    language = lang_map.get(language_option)

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(step, total, msg):
        if total > 0:
            pct = min(int((step / total) * 100), 100)
            progress_bar.progress(pct)
        status_text.info(f"⏳ {msg}")

    temp_dir = tempfile.mkdtemp(dir="uploads")

    try:
        # ── Step 1: Save uploaded file ──────────────────
        update_progress(0, 4, "File save ho rahi hai...")
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # ── Step 2: Extract Audio ──────────────────────
        update_progress(1, 4, "Audio extract ho raha hai (FFmpeg)...")
        extractor = AudioExtractor()
        audio_path = extractor.extract(input_path, output_dir=temp_dir)
        duration = extractor.get_duration(audio_path)
        st.session_state.duration = duration
        st.session_state.audio_path = audio_path

        # ── Step 3: Transcribe ─────────────────────────
        update_progress(2, 4, f"Transcription shuru (Whisper '{whisper_model}')...")

        def transcription_progress(step, total, msg):
            base = 2 / 4
            chunk_pct = (step / max(total, 1)) * (1 / 4)
            progress_bar.progress(min(int((base + chunk_pct) * 100), 90))
            status_text.info(f"⏳ {msg}")

        transcriber = Transcriber(
            model_size=whisper_model,
            language=language,
            progress_callback=transcription_progress,
        )
        transcript_result = transcriber.transcribe(audio_path)
        transcript_text = transcript_result["text"]
        st.session_state.transcript = transcript_text

        if not transcript_text.strip():
            st.error("❌ Transcript empty hai! Audio check karo.")
            return

        # ── Step 4: Generate MoM ───────────────────────
        update_progress(3, 4, "GPT se MoM generate ho raha hai...")
        meeting_date = datetime.now().strftime("%Y-%m-%d")

        def mom_progress(step, total, msg):
            base = 3 / 4
            chunk_pct = (step / max(total, 1)) * (1 / 4)
            progress_bar.progress(min(int((base + chunk_pct) * 100), 99))
            status_text.info(f"⏳ {msg}")

        summarizer = MoMSummarizer(
            model=gpt_model,
            api_key=api_key,
            progress_callback=mom_progress,
        )
        mom_result = summarizer.generate(
            transcript=transcript_text,
            meeting_date=meeting_date,
            duration_seconds=duration,
        )
        st.session_state.mom_text = mom_result["formatted"]
        st.session_state.processing_done = True

        # ── Done ───────────────────────────────────────
        progress_bar.progress(100)
        status_text.success(
            f"✅ MoM ready hai! "
            f"({format_duration(duration)} meeting, "
            f"{transcript_result['chunks_processed']} chunk(s) processed)"
        )
        st.balloons()

        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        st.rerun()

    except FileNotFoundError as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ File nahi mila: {exc}")
    except EnvironmentError as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ System error: {exc}")
    except ValueError as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Invalid input: {exc}")
    except RuntimeError as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Processing error: {exc}")
    except Exception as exc:
        progress_bar.empty()
        status_text.empty()
        logger.exception("Unexpected error in pipeline")
        st.error(f"❌ Unexpected error: {exc}")
