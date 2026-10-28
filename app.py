"""VideoLens Streamlit frontend for the video intelligence pipeline."""

from __future__ import annotations

import html
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
DOWNLOAD_DIR = ROOT / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root { --bg:#080d18; --card:#101829; --line:#263653; --text:#f5f7fb; --muted:#91a0b9; --violet:#8066ff; --teal:#35d4c3; }
        .stApp { background:radial-gradient(circle at 80% -10%,#1a2150 0,transparent 32%),var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
        .block-container { max-width:1440px; padding:2.4rem 3.5rem 4rem; }
        h1,h2,h3,h4 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; }
        h1 { font-size:clamp(2.5rem,5vw,4.7rem)!important; line-height:1.01!important; margin:.3rem 0 .9rem!important; }
        h2 { font-size:1.65rem!important; }
        [data-testid='stSidebar'] { background:#0a1221; border-right:1px solid var(--line); }
        [data-testid='stSidebar'] .block-container { padding:1.8rem 1.15rem; }
        .brand { display:flex; align-items:center; gap:.65rem; font:700 1.2rem 'Space Grotesk',sans-serif; margin-bottom:2.3rem; }
        .brand-icon { display:grid; place-items:center; width:31px; height:31px; border-radius:10px; background:linear-gradient(135deg,var(--violet),var(--teal)); color:white; }
        .eyebrow { color:var(--teal); font-size:.73rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
        .hero-copy { max-width:680px; color:var(--muted); font-size:1.08rem; line-height:1.65; }
        .subtle { color:var(--muted); font-size:.83rem; line-height:1.55; }
        .metric { background:rgba(16,24,41,.86); border:1px solid var(--line); border-radius:15px; padding:1rem; min-height:100px; }
        .metric-label { color:var(--muted); font-size:.76rem; margin-bottom:.5rem; }
        .metric-value { font:700 1.16rem 'Space Grotesk',sans-serif; overflow-wrap:anywhere; }
        .section-label { color:var(--muted); font-size:.73rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin:1.25rem 0 .65rem; }
        .empty { border:1px dashed #385073; border-radius:18px; padding:3.7rem 1.5rem; text-align:center; color:var(--muted); }
        .empty-mark { color:var(--teal); font-size:2.5rem; }
        .chat-user { background:#1c2b58; border-radius:15px 15px 4px 15px; padding:.85rem 1rem; margin:.7rem 0 .7rem 14%; }
        .chat-assistant { background:#111c31; border:1px solid var(--line); border-radius:15px 15px 15px 4px; padding:.85rem 1rem; margin:.7rem 14% .7rem 0; }
        .stButton > button, .stDownloadButton > button { min-height:43px; border-radius:11px; font-weight:600; }
        .stButton > button:hover { border-color:var(--teal); }
        div[data-testid='stForm'] { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    for key, value in {"result": None, "chat": [], "source_name": "", "language": "english", "running": False}.items():
        st.session_state.setdefault(key, value)


def metric(label: str, value: str) -> None:
    st.markdown(f"<div class='metric'><div class='metric-label'>{html.escape(label)}</div><div class='metric-value'>{html.escape(value)}</div></div>", unsafe_allow_html=True)


def sidebar() -> str:
    with st.sidebar:
        st.markdown("<div class='brand'><span class='brand-icon'>V</span>VideoLens</div>", unsafe_allow_html=True)
        st.markdown("### Workspace")
        st.caption("A focused command center for every recording, interview, and meeting.")
        language = st.selectbox("Transcription engine", ["english", "hinglish"], format_func=lambda x: "English  /  Whisper" if x == "english" else "Hinglish  /  Sarvam AI")
        st.markdown("<div class='subtle'>English runs locally with Whisper. Hinglish uses Sarvam AI.</div>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>System status</div>", unsafe_allow_html=True)
        groq, sarvam = bool(os.getenv("GROQ_API_KEY")), bool(os.getenv("SARVAM_API_KEY"))
        st.markdown(f"{'🟢' if groq else '🔴'} Groq analysis {'connected' if groq else 'key missing'}")
        st.markdown(f"{'🟢' if sarvam else '⚪'} Sarvam {'connected' if sarvam else 'optional'}")
        st.divider()
        st.markdown("<div class='section-label'>Workflow</div>", unsafe_allow_html=True)
        for index, label in enumerate(["Ingest media", "Transcribe audio", "Extract insights", "Chat with transcript"], 1):
            st.markdown(f"<div class='subtle'><b style='color:#35d4c3'>{index:02}</b>&nbsp;&nbsp;{label}</div>", unsafe_allow_html=True)
        if st.session_state.result:
            st.divider()
            st.markdown("<div class='section-label'>Current session</div>", unsafe_allow_html=True)
            st.caption(st.session_state.source_name or "Analyzed video")
            if st.button("Clear workspace", use_container_width=True):
                st.session_state.result, st.session_state.chat, st.session_state.source_name = None, [], ""
                st.rerun()
    return language


def analyze(source: str, language: str, name: str) -> None:
    from main import run_pipeline
    st.session_state.running = True
    with st.status("Preparing your intelligence brief", expanded=True) as status:
        try:
            st.write("Normalizing media and creating audio chunks")
            result = run_pipeline(source, language)
            st.write("Building transcript knowledge base")
            st.session_state.result, st.session_state.chat = result, []
            st.session_state.source_name, st.session_state.language = name, language
            status.update(label="Brief ready", state="complete", expanded=False)
            st.toast("Analysis complete", icon="✅")
        except Exception as exc:
            status.update(label="Analysis failed", state="error", expanded=True)
            st.error(f"{type(exc).__name__}: {exc}")
        finally:
            st.session_state.running = False


def source_panel(language: str) -> None:
    with st.container(border=True):
        st.markdown("### Create a new brief")
        st.markdown("<div class='subtle'>Choose a source, select your language, and let the pipeline turn it into structured knowledge.</div>", unsafe_allow_html=True)
        mode = st.radio("Source", ["YouTube URL", "Local file"], horizontal=True, label_visibility="collapsed")
        source, name = "", ""
        if mode == "YouTube URL":
            source = st.text_input("Video URL", placeholder="Paste a public YouTube URL…", label_visibility="collapsed")
            name = source or "YouTube video"
        else:
            uploaded = st.file_uploader("Upload media", type=["mp4", "mov", "mkv", "webm", "mp3", "wav", "m4a", "flac"], label_visibility="collapsed")
            if uploaded:
                path = DOWNLOAD_DIR / uploaded.name
                path.write_bytes(uploaded.getbuffer())
                source, name = str(path), uploaded.name
                st.success(f"{uploaded.name}  ·  {uploaded.size / 1024 / 1024:.1f} MB ready")
        if st.button("Analyze video  →", type="primary", use_container_width=True, disabled=st.session_state.running):
            if not source.strip():
                st.warning("Add a YouTube URL or upload a file to continue.")
            elif mode == "YouTube URL" and not source.startswith(("http://", "https://")):
                st.warning("Please enter a valid http(s) URL.")
            else:
                analyze(source, language, name)


def render_chat(chain) -> None:
    if chain is None:
        st.warning("The searchable knowledge base is unavailable for this analysis.")
        return
    st.markdown("Ask questions grounded only in the transcript.")
    if not st.session_state.chat:
        st.markdown("<div class='subtle'>Try one of these:</div>", unsafe_allow_html=True)
        for col, prompt in zip(st.columns(3), ["What were the key decisions?", "List all action items.", "What remains unresolved?"]):
            with col:
                if st.button(prompt, use_container_width=True):
                    st.session_state.pending_question = prompt
                    st.rerun()
    for item in st.session_state.chat:
        css = "chat-user" if item["role"] == "user" else "chat-assistant"
        label = "You" if item["role"] == "user" else "VideoLens"
        text = html.escape(item["text"]).replace("\n", "<br>")
        st.markdown(f"<div class='{css}'><b>{label}</b><br>{text}</div>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        question = st.text_input("Question", value=st.session_state.pop("pending_question", ""), placeholder="What was decided about the launch timeline?", label_visibility="collapsed")
        submitted = st.form_submit_button("Ask the transcript  →", use_container_width=True)
    if submitted and question.strip():
        from core.rag_engine import ask_question
        with st.spinner("Searching the transcript…"):
            answer = ask_question(chain, question.strip())
        st.session_state.chat += [{"role": "user", "text": question.strip()}, {"role": "assistant", "text": answer}]
        st.rerun()


def results(result: dict) -> None:
    transcript = result.get("transcript", "")
    st.markdown("## Intelligence brief")
    st.caption(st.session_state.source_name or "Analyzed source")
    cards = st.columns(4)
    with cards[0]: metric("Title", result.get("title", "Untitled"))
    with cards[1]: metric("Transcript", f"{len(transcript.split()):,} words")
    with cards[2]: metric("Language", "Hinglish" if st.session_state.language == "hinglish" else "English")
    with cards[3]: metric("Status", "Searchable")
    st.write("")
    overview, transcript_tab, chat_tab = st.tabs(["Overview", "Transcript", "Ask your video"])
    with overview:
        left, right = st.columns([1.08, .92], gap="large")
        with left:
            st.markdown("### Executive summary")
            st.markdown(result.get("summary", "No summary available."))
        with right:
            st.markdown("### Extracted signals")
            with st.expander("Action items", expanded=True): st.markdown(result.get("action_items", "No action items found."))
            with st.expander("Key decisions"): st.markdown(result.get("key_decisions", "No key decisions found."))
            with st.expander("Open questions"): st.markdown(result.get("open_questions", "No open questions found."))
    with transcript_tab:
        st.download_button("Download transcript", transcript, "transcript.txt", "text/plain", use_container_width=True)
        st.text_area("Full transcript", transcript, height=560, label_visibility="collapsed")
    with chat_tab:
        render_chat(result.get("rag_chain"))


def main() -> None:
    st.set_page_config(page_title="VideoLens | Video Intelligence", page_icon="V", layout="wide", initial_sidebar_state="expanded")
    styles()
    init_state()
    language = sidebar()
    st.markdown("<div class='eyebrow'>AI video intelligence workspace</div>", unsafe_allow_html=True)
    st.title("Make every video\nsearchable and useful.")
    st.markdown("<div class='hero-copy'>A calm, focused workspace for turning recordings into decisions, action items, summaries, and grounded answers.</div>", unsafe_allow_html=True)
    st.write("")
    source_panel(language)
    st.write("")
    if st.session_state.result:
        results(st.session_state.result)
    else:
        st.markdown("<div class='empty'><div class='empty-mark'>◌</div><h3>Your brief will appear here</h3><div>Start above to unlock the summary, extracted signals, transcript, and Q&A.</div></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
