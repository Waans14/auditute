
import streamlit as st
import whisper
from whisper.tokenizer import LANGUAGES
import hashlib
import json
import tempfile
import os
import shutil
from pathlib import Path
from io import BytesIO
from fpdf import FPDF
from docx import Document
from typing import Optional
from redis import Redis

st.set_page_config(
    page_title="Auditute | Whisper Transcription",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }
        .hero {
            background: linear-gradient(120deg, #0f172a, #1e293b);
            color: #f8fafc;
            padding: 1.75rem 2rem;
            border-radius: 18px;
            margin-bottom: 1.5rem;
        }
        .hero h1 {
            font-size: 2.2rem;
            margin: 0.2rem 0 0.4rem 0;
        }
        .hero p {
            margin: 0;
            color: #e2e8f0;
        }
        .badge {
            display: inline-block;
            background: #e2e8f0;
            color: #0f172a;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 0.4rem;
        }
        .card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1rem 1.2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <span class="badge">Whisper ASR</span>
        <span class="badge">Multi-language</span>
        <span class="badge">Production-ready</span>
        <h1>Auditute Transcription Studio</h1>
        <p>Upload audio, choose the right model, and get a clean transcript in minutes.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        st.error(
            "ffmpeg not found in PATH. Install it and restart the app. "
            "Windows: winget install Gyan.FFmpeg or choco install ffmpeg."
        )
        st.stop()


@st.cache_resource(show_spinner=False)
def load_model(model_size: str) -> whisper.Whisper:
    return whisper.load_model(model_size)


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_docx_bytes(text: str) -> bytes:
    doc = Document()
    lines = text.splitlines() if text else [""]
    for line in lines:
        doc.add_paragraph(line)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def build_pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    lines = text.splitlines() if text else [""]
    for line in lines:
        pdf.multi_cell(0, 8, line)
    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    if isinstance(output, bytearray):
        return bytes(output)
    return bytes(output)


def get_redis_client() -> tuple[Optional[Redis], str]:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None, "Redis not configured"
    try:
        client = Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client, "Redis connected"
    except Exception:
        return None, "Redis unavailable"


def get_cache_ttl_seconds() -> int:
    ttl_value = os.getenv("REDIS_TTL_SECONDS", "604800")
    try:
        ttl = int(ttl_value)
    except ValueError:
        return 604800
    return ttl if ttl > 0 else 0


def build_cache_key(audio_bytes: bytes, options: dict) -> str:
    payload = json.dumps(options, sort_keys=True).encode("utf-8")
    hasher = hashlib.sha256()
    hasher.update(audio_bytes)
    hasher.update(payload)
    return f"transcription:{hasher.hexdigest()}"


def load_cached_transcription(client: Redis, cache_key: str) -> Optional[dict]:
    cached_payload = client.get(cache_key)
    if not cached_payload:
        return None
    try:
        return json.loads(cached_payload)
    except json.JSONDecodeError:
        return None


def store_cached_transcription(client: Redis, cache_key: str, data: dict) -> None:
    ttl = get_cache_ttl_seconds()
    payload = json.dumps(data)
    if ttl > 0:
        client.setex(cache_key, ttl, payload)
    else:
        client.set(cache_key, payload)


redis_client, redis_status = get_redis_client()
cache_enabled = False


with st.sidebar:
    st.header("Settings")
    model_size = st.selectbox(
        "Model",
        ["tiny", "base", "small", "medium", "large"],
        index=1,
        help="Larger models are more accurate but slower.",
    )
    task = st.selectbox("Task", ["transcribe", "translate"], index=0)

    language_codes = ["auto"] + sorted(LANGUAGES.keys())
    language_code = st.selectbox(
        "Language",
        language_codes,
        index=0,
        format_func=lambda code: "Auto-detect"
        if code == "auto"
        else LANGUAGES[code].title(),
    )

    show_segments = st.checkbox("Show timestamps", value=False)
    use_fp16 = st.checkbox(
        "Use FP16 (GPU)",
        value=False,
        help="Enable on GPU for speed. Keep off on CPU to avoid warnings.",
    )

    st.divider()
    st.markdown("**Tips**")
    st.caption("Short clips (5-15 min) process faster and cost less.")
    st.caption("MP3, WAV, M4A, AAC, FLAC, and OGG are supported.")

    st.divider()
    st.markdown("**Cache**")
    if redis_client is None:
        st.caption("Redis not configured. Set REDIS_URL to enable caching.")
    else:
        st.caption(redis_status)
        cache_enabled = st.checkbox(
            "Enable Redis cache",
            value=True,
            help="Cache transcripts by audio content and settings.",
        )


left, right = st.columns([2, 1], gap="large")

with left:
    st.subheader("Upload audio")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    audio_file = st.file_uploader(
        "Drag and drop or browse",
        type=["wav", "mp3", "m4a", "aac", "flac", "ogg"],
        help="Select a single audio file to transcribe.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    action_col, clear_col = st.columns([1, 1])
    with action_col:
        transcribe_clicked = st.button(
            "Transcribe audio",
            type="primary",
            use_container_width=True,
        )
    with clear_col:
        clear_clicked = st.button("Clear result", use_container_width=True)

with right:
    st.subheader("What you get")
    st.markdown(
        """
        - Accurate multi-language transcription
        - Optional timestamps for review
        - Downloadable text output
        """
    )
    st.info("Set the model to *base* for a good speed/accuracy balance.")

if clear_clicked:
    st.session_state.pop("transcription", None)
    st.session_state.pop("audio_name", None)

if transcribe_clicked:
    if audio_file is None:
        st.error("Please upload an audio file before transcribing.")
    else:
        audio_bytes = audio_file.read()
        transcribe_options = {
            "task": task,
            "fp16": use_fp16,
        }
        if language_code != "auto":
            transcribe_options["language"] = language_code
        cache_options = {**transcribe_options, "model": model_size}

        cache_key = None
        cached_transcription = None
        if cache_enabled and redis_client is not None:
            cache_key = build_cache_key(audio_bytes, cache_options)
            cached_transcription = load_cached_transcription(redis_client, cache_key)

        if cached_transcription is not None:
            st.session_state["transcription"] = cached_transcription
            st.session_state["audio_name"] = audio_file.name or "audio"
            st.info("Loaded transcript from Redis cache.")
        else:
            ensure_ffmpeg_available()
            suffix = Path(audio_file.name).suffix if audio_file.name else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
                temp_audio.write(audio_bytes)

            audio_file_path = os.path.abspath(temp_audio.name)

            try:
                with st.spinner("Transcribing... this may take a few minutes."):
                    model = load_model(model_size)
                    transcription = model.transcribe(audio_file_path, **transcribe_options)

                st.session_state["transcription"] = transcription
                st.session_state["audio_name"] = audio_file.name or "audio"
                st.success("Transcription complete.")
                if cache_key and redis_client is not None:
                    store_cached_transcription(redis_client, cache_key, transcription)
            finally:
                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)


if "transcription" in st.session_state:
    result = st.session_state["transcription"]
    transcript_text = result.get("text", "").strip()
    st.divider()
    st.subheader("Transcript")
    st.text_area("", transcript_text, height=260)

    download_name = f"{Path(st.session_state.get('audio_name', 'transcript')).stem}.txt"
    download_cols = st.columns([1, 1, 1, 1])
    with download_cols[0]:
        st.download_button(
            "Download TXT",
            transcript_text,
            file_name=download_name,
            mime="text/plain",
            use_container_width=True,
        )
    with download_cols[1]:
        st.download_button(
            "Download PDF",
            build_pdf_bytes(transcript_text),
            file_name=f"{Path(st.session_state.get('audio_name', 'transcript')).stem}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with download_cols[2]:
        st.download_button(
            "Download DOCX",
            build_docx_bytes(transcript_text),
            file_name=f"{Path(st.session_state.get('audio_name', 'transcript')).stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with download_cols[3]:
        detected_language = result.get("language", "-")
        st.caption(f"Detected language: {detected_language}")

    if show_segments:
        segments = result.get("segments", [])
        if segments:
            rows = [
                {
                    "Start": format_timestamp(seg.get("start", 0)),
                    "End": format_timestamp(seg.get("end", 0)),
                    "Text": seg.get("text", "").strip(),
                }
                for seg in segments
            ]
            st.dataframe(rows, use_container_width=True, height=320)
        else:
            st.info("No timestamp data available for this transcript.")