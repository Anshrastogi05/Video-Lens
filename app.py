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
        language = st.selectbox("Transcription engine", ["english", "hinglish"], format_func=lambda x: "English" if x == "english" else "Hinglish")
        st.caption("Choose the language for transcription.")
        st.markdown("<div class='section-label'>System status</div>", unsafe_allow_html=True)
        groq, sarvam = bool(os.getenv("GROQ_API_KEY")), bool(os.getenv("SARVAM_API_KEY"))
        st.markdown(f"{'🟢' if groq else '🔴'} Groq analysis {'connected' if groq else 'key missing'}")
        st.markdown(f"{'🟢' if sarvam else '⚪'} Sarvam {'connected' if sarvam else 'optional'}")
        st.divider()
        st.markdown("<div class='section-label'>What VideoLens can do</div>", unsafe_allow_html=True)
        capabilities = [
            "Analyze a public YouTube URL or upload a local audio/video file",
            "Transcribe English or Hinglish speech",
            "Generate a title and an executive summary",
            "Extract action items, key decisions, and open questions",
            "Make the transcript searchable for grounded Q&A",
            "Download the full transcript as a text file",
        ]
        for capability in capabilities:
            st.markdown(f"<div class='subtle' style='margin:.5rem 0'>• {html.escape(capability)}</div>", unsafe_allow_html=True)
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


# import os
# import tempfile
# from importlib import import_module

# import streamlit as st
# from dotenv import load_dotenv

# from core.transcriber import transcribe_all
# from core.summarizer import summarize, generate_title
# from core.extractor import (
#     extract_action_items,
#     extract_key_decisions,
#     extract_questions,
# )
# from core.rag_engine import build_rag_chain, ask_question

# load_dotenv()
# process_input = import_module("utlis.audio_processors").process_input


# # ───────────────────────── Page setup ─────────────────────────
# st.set_page_config(
#     page_title="Meeting Notes AI",
#     page_icon="🎧",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# st.session_state.setdefault("theme", "light")

# # ───────────────────────── Styling ─────────────────────────
# st.markdown(
#     """
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Sora:wght@500;600;700&display=swap');

# :root {
#     --bg: #F2F5FA;
#     --surface: #FFFFFF;
#     --ink: #1A2233;
#     --muted: #5E6B82;
#     --line: #DCE3EF;
#     --primary: #3451D1;
#     --primary-soft: #E6EBFC;
#     --teal: #0E8F7E;
#     --teal-soft: #DDF3EF;
#     --amber: #B7791F;
#     --amber-soft: #FBF0D9;
# }

# html, body, [class*="css"], .stApp {
#     font-family: 'Inter', sans-serif;
#     color: var(--ink);
# }
# .stApp { background: var(--bg); }

# /* Hide default chrome */
# #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
# .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px; }

# /* Headings */
# h1, h2, h3, .display { font-family: 'Sora', sans-serif; letter-spacing: -0.02em; }

# /* Sidebar */
# section[data-testid="stSidebar"] {
#     background: var(--surface);
#     border-right: 1px solid var(--line);
# }
# section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

# /* Brand */
# .brand { display: flex; align-items: center; gap: .6rem; margin-bottom: 1.2rem; }
# .brand-mark {
#     width: 36px; height: 36px; border-radius: 10px;
#     background: var(--primary); color: #fff;
#     display: grid; place-items: center; font-size: 1.1rem;
# }
# .brand-name { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.1rem; }

# /* Hero (before any result) */
# .hero { padding: 3rem 0 1.5rem 0; }
# .hero h1 { font-size: 2.6rem; line-height: 1.1; margin: 0 0 .8rem 0; max-width: 18ch; }
# .hero p { color: var(--muted); font-size: 1.05rem; max-width: 56ch; line-height: 1.6; }

# .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2rem; }
# .step {
#     background: var(--surface); border: 1px solid var(--line);
#     border-radius: 14px; padding: 1.1rem 1.2rem;
# }
# .step b { font-family: 'Sora', sans-serif; display: block; margin-bottom: .25rem; }
# .step span { color: var(--muted); font-size: .92rem; line-height: 1.5; }

# /* Result header */
# .result-title { font-family: 'Sora', sans-serif; font-size: 2rem; font-weight: 700;
#     line-height: 1.2; margin: .2rem 0 .8rem 0; }
# .chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1.4rem; }
# .chip {
#     background: var(--surface); border: 1px solid var(--line); color: var(--muted);
#     border-radius: 999px; padding: .25rem .8rem; font-size: .85rem;
# }

# /* Stat tiles */
# .stat {
#     background: var(--surface); border: 1px solid var(--line);
#     border-radius: 14px; padding: 1rem 1.2rem;
# }
# .stat .num { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; line-height: 1; }
# .stat .lbl { color: var(--muted); font-size: .88rem; margin-top: .35rem; }
# .stat.blue .num { color: var(--primary); }
# .stat.teal .num { color: var(--teal); }
# .stat.amber .num { color: var(--amber); }

# /* Section cards */
# .card {
#     background: var(--surface); border: 1px solid var(--line);
#     border-radius: 14px; padding: 1.4rem 1.6rem; line-height: 1.7;
# }
# .card.accent-blue  { border-left: 4px solid var(--primary); }
# .card.accent-teal  { border-left: 4px solid var(--teal); }
# .card.accent-amber { border-left: 4px solid var(--amber); }

# .item {
#     display: flex; gap: .8rem; align-items: flex-start;
#     background: var(--surface); border: 1px solid var(--line);
#     border-radius: 12px; padding: .85rem 1.1rem; margin-bottom: .6rem; line-height: 1.55;
# }
# .item .dot {
#     flex: 0 0 auto; width: 22px; height: 22px; border-radius: 50%;
#     display: grid; place-items: center; font-size: .75rem; margin-top: 2px;
# }
# .item .dot.teal  { background: var(--teal-soft);  color: var(--teal); }
# .item .dot.blue  { background: var(--primary-soft); color: var(--primary); }
# .item .dot.amber { background: var(--amber-soft); color: var(--amber); }

# /* Tabs */
# button[data-baseweb="tab"] { font-family: 'Sora', sans-serif; font-weight: 600; font-size: .95rem; }
# div[data-baseweb="tab-highlight"] { background-color: var(--primary) !important; }
# button[data-baseweb="tab"][aria-selected="true"] { color: var(--primary); }

# /* Buttons */
# .stButton > button, .stDownloadButton > button {
#     border-radius: 10px; font-weight: 600; border: 1px solid var(--line);
#     transition: border-color .15s, background .15s;
# }
# .stButton > button[kind="primary"] {
#     background: var(--primary); border-color: var(--primary); color: #fff;
# }
# .stButton > button[kind="primary"]:hover { background: #2A43B3; border-color: #2A43B3; }
# .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
#     outline: 3px solid var(--primary-soft); outline-offset: 2px;
# }

# /* Inputs */
# .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
#     border-radius: 10px;
# }

# /* Chat */
# [data-testid="stChatMessage"] {
#     background: var(--surface); border: 1px solid var(--line);
#     border-radius: 14px; padding: 1rem 1.2rem;
# }
# [data-testid="stChatInput"] { border-radius: 14px; }

# /* Transcript */
# .transcript {
#     background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
#     padding: 1.4rem 1.6rem; max-height: 520px; overflow-y: auto;
#     line-height: 1.8; font-size: .97rem; color: #2B3550; white-space: pre-wrap;
# }

# @media (max-width: 760px) {
#     .steps { grid-template-columns: 1fr; }
#     .hero h1 { font-size: 2rem; }
# }
# @media (prefers-reduced-motion: reduce) {
#     * { transition: none !important; animation: none !important; }
# }
# </style>
# """,
#     unsafe_allow_html=True,
# )

# if st.session_state.theme == "dark":
#     st.markdown("""
#     <style>
#     :root { --bg:#0b0d12; --surface:#12151c; --ink:#f3f4f6; --muted:#a7afbd; --line:#2a303b; --primary:#ffffff; --primary-soft:#252a33; --teal:#d7dce5; --teal-soft:#252a33; --amber:#f0c674; --amber-soft:#332d20; }
#     .stApp { background:var(--bg); color:var(--ink); }
#     section[data-testid="stSidebar"] { background:#0f1117; }
#     .brand-mark, .stButton > button[kind="primary"] { background:#f5f5f5!important; color:#111827!important; }
#     .step, .stat, .card, .item, .chip, .transcript, [data-testid="stChatMessage"] { background:var(--surface); color:var(--ink); }
#     .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, textarea { background:#0b0d12!important; color:var(--ink)!important; border-color:var(--line)!important; }
#     .transcript { color:#e5e7eb; }
#     .theme-button button { background:#20242d!important; color:#fff!important; border-color:#3a424f!important; }
#     </style>
#     """, unsafe_allow_html=True)
# else:
#     st.markdown("<style>.theme-button button { background:#ffffff!important; color:#111827!important; border-color:#dbe2ef!important; }</style>", unsafe_allow_html=True)


# # ───────────────────────── Helpers ─────────────────────────
# def to_lines(value) -> list[str]:
#     """Turn LLM output (string, bullet text, or list) into a clean list of items."""
#     if not value:
#         return []
#     if isinstance(value, (list, tuple)):
#         raw = [str(v) for v in value]
#     else:
#         raw = str(value).splitlines()
#     cleaned = []
#     for line in raw:
#         line = line.strip().lstrip("-•*0123456789.) ").strip()
#         if line and line.lower() not in {"none", "n/a", "none found", "no action items"}:
#             cleaned.append(line)
#     return cleaned


# def render_items(items: list[str], tone: str, empty_msg: str):
#     if not items:
#         st.info(empty_msg)
#         return
#     icon = {"teal": "✓", "blue": "◆", "amber": "?"}[tone]
#     html = "".join(
#         f'<div class="item"><div class="dot {tone}">{icon}</div><div>{i}</div></div>'
#         for i in items
#     )
#     st.markdown(html, unsafe_allow_html=True)


# def stat_tile(number, label, tone="blue"):
#     st.markdown(
#         f'<div class="stat {tone}"><div class="num">{number}</div>'
#         f'<div class="lbl">{label}</div></div>',
#         unsafe_allow_html=True,
#     )


# def build_report(r: dict) -> str:
#     def bullets(items):
#         return "\n".join(f"- {i}" for i in items) or "_None found_"

#     return (
#         f"# {r['title']}\n\n"
#         f"## Summary\n{r['summary']}\n\n"
#         f"## Action items\n{bullets(to_lines(r['action_items']))}\n\n"
#         f"## Key decisions\n{bullets(to_lines(r['key_decisions']))}\n\n"
#         f"## Open questions\n{bullets(to_lines(r['open_questions']))}\n\n"
#         f"## Transcript\n{r['transcript']}\n"
#     )


# def run_pipeline(source: str, language: str, status) -> dict:
#     status.update(label="Preparing audio…")
#     chunks = process_input(source)

#     status.update(label="Transcribing speech…")
#     transcript = transcribe_all(chunks, language)

#     status.update(label="Writing title and summary…")
#     title = generate_title(transcript)
#     summary = summarize(transcript)

#     status.update(label="Finding action items, decisions and questions…")
#     action_items = extract_action_items(transcript)
#     decisions = extract_key_decisions(transcript)
#     questions = extract_questions(transcript)

#     status.update(label="Getting the chat ready…")
#     rag_chain = build_rag_chain(transcript)

#     return {
#         "title": title,
#         "transcript": transcript,
#         "summary": summary,
#         "action_items": action_items,
#         "key_decisions": decisions,
#         "open_questions": questions,
#         "rag_chain": rag_chain,
#     }


# # ───────────────────────── Session state ─────────────────────────
# st.session_state.setdefault("result", None)
# st.session_state.setdefault("messages", [])
# st.session_state.setdefault("meta", {})


# # ───────────────────────── Sidebar ─────────────────────────
# with st.sidebar:
#     st.markdown(
#         '<div class="brand"><div class="brand-mark">🎧</div>'
#         '<div class="brand-name">Meeting Notes AI</div></div>',
#         unsafe_allow_html=True,
#     )

#     theme_col, _ = st.columns([1, 5])
#     with theme_col:
#         st.markdown('<div class="theme-button">', unsafe_allow_html=True)
#         if st.button("☀" if st.session_state.theme == "dark" else "☾", key="theme_toggle", help="Switch light / dark mode"):
#             st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
#             st.rerun()
#         st.markdown('</div>', unsafe_allow_html=True)

#     input_mode = st.radio(
#         "Where is your recording?",
#         ["YouTube link", "Upload a file"],
#         horizontal=True,
#     )

#     source, source_label = None, ""
#     uploaded = None
#     if input_mode == "YouTube link":
#         url = st.text_input("Video URL", placeholder="https://www.youtube.com/watch?v=…")
#         if url.strip():
#             source, source_label = url.strip(), "YouTube"
#     else:
#         uploaded = st.file_uploader(
#             "Audio or video file",
#             type=["mp3", "wav", "m4a", "mp4", "mkv", "webm", "mov", "ogg", "flac"],
#         )
#         if uploaded:
#             source_label = uploaded.name

#     language = st.selectbox(
#         "Spoken language",
#         ["english", "hinglish"],
#         format_func=lambda x: x.capitalize(),
#         help="Pick Hinglish if speakers mix Hindi and English.",
#     )

#     can_run = bool(source or uploaded)
#     go = st.button(
#         "Generate notes",
#         type="primary",
#         use_container_width=True,
#         disabled=not can_run,
#     )

#     if st.session_state.result:
#         if st.button("Start over", use_container_width=True):
#             st.session_state.result = None
#             st.session_state.messages = []
#             st.session_state.meta = {}
#             st.rerun()

#     st.divider()
#     st.caption("Long recordings can take a few minutes. Keep this tab open while it runs.")


# # ───────────────────────── Run pipeline ─────────────────────────
# if go and can_run:
#     tmp_path = None
#     try:
#         if uploaded:
#             suffix = os.path.splitext(uploaded.name)[1]
#             with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
#                 tmp.write(uploaded.getbuffer())
#                 tmp_path = tmp.name
#             source = tmp_path

#         with st.status("Starting…", expanded=True) as status:
#             result = run_pipeline(source, language, status)
#             status.update(label="Notes are ready", state="complete", expanded=False)

#         st.session_state.result = result
#         st.session_state.messages = []
#         st.session_state.meta = {"source": source_label, "language": language}
#     except Exception as e:
#         st.error(
#             f"Something went wrong while processing this recording: {e}\n\n"
#             "Check the link or file, then try again."
#         )
#     finally:
#         if tmp_path and os.path.exists(tmp_path):
#             os.remove(tmp_path)


# # ───────────────────────── Main area ─────────────────────────
# result = st.session_state.result

# if not result:
#     st.markdown(
#         """
# <div class="hero">
#   <h1>Turn any recording into notes you can question</h1>
#   <p>Paste a YouTube link or upload a meeting recording. You'll get a summary, action items,
#   decisions, open questions, and a chat that answers from the transcript.</p>
# </div>
# <div class="steps">
#   <div class="step"><b>Add a recording</b>
#     <span>Use the panel on the left: a YouTube link, or an audio or video file.</span></div>
#   <div class="step"><b>Generate notes</b>
#     <span>The recording is transcribed, then summarised and sorted into what matters.</span></div>
#   <div class="step"><b>Ask follow-ups</b>
#     <span>Chat with the transcript to find who said what, and when it came up.</span></div>
# </div>
# """,
#         unsafe_allow_html=True,
#     )
#     st.stop()

# # ----- Results -----
# meta = st.session_state.meta
# transcript = result["transcript"]
# actions = to_lines(result["action_items"])
# decisions = to_lines(result["key_decisions"])
# questions = to_lines(result["open_questions"])
# word_count = len(transcript.split())
# read_min = max(1, round(word_count / 200))

# st.markdown(f'<div class="result-title">{result["title"]}</div>', unsafe_allow_html=True)
# st.markdown(
#     f'<div class="chips"><span class="chip">{meta.get("source", "")}</span>'
#     f'<span class="chip">{meta.get("language", "").capitalize()}</span>'
#     f'<span class="chip">{word_count:,} words</span>'
#     f'<span class="chip">{read_min} min read</span></div>',
#     unsafe_allow_html=True,
# )

# c1, c2, c3 = st.columns(3)
# with c1:
#     stat_tile(len(actions), "Action items", "teal")
# with c2:
#     stat_tile(len(decisions), "Key decisions", "blue")
# with c3:
#     stat_tile(len(questions), "Open questions", "amber")

# st.write("")

# tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
#     ["Summary", "Action items", "Decisions", "Open questions", "Transcript", "Chat"]
# )

# with tab_summary:
#     st.markdown(
#         f'<div class="card accent-blue">{result["summary"]}</div>'
#         if "\n" not in str(result["summary"])
#         else "",
#         unsafe_allow_html=True,
#     )
#     if "\n" in str(result["summary"]):
#         with st.container(border=True):
#             st.markdown(result["summary"])
#     st.write("")
#     st.download_button(
#         "Download full report (.md)",
#         data=build_report(result),
#         file_name="meeting_notes.md",
#         mime="text/markdown",
#     )

# with tab_actions:
#     render_items(actions, "teal", "No action items were found in this recording.")

# with tab_decisions:
#     render_items(decisions, "blue", "No clear decisions were found in this recording.")

# with tab_questions:
#     render_items(questions, "amber", "No unanswered questions were found in this recording.")

# with tab_transcript:
#     search = st.text_input("Find in transcript", placeholder="Type a word or phrase")
#     text = transcript
#     if search.strip():
#         hits = transcript.lower().count(search.strip().lower())
#         st.caption(f"{hits} match{'es' if hits != 1 else ''}")
#         import re

#         text = re.sub(
#             f"({re.escape(search.strip())})",
#             r"<mark>\1</mark>",
#             transcript,
#             flags=re.IGNORECASE,
#         )
#     st.markdown(f'<div class="transcript">{text}</div>', unsafe_allow_html=True)
#     st.download_button(
#         "Download transcript (.txt)",
#         data=transcript,
#         file_name="transcript.txt",
#         mime="text/plain",
#     )

# with tab_chat:
#     suggestions = [
#         "What were the main points?",
#         "Who is responsible for what?",
#         "What deadlines were mentioned?",
#     ]

#     pending = None
#     if not st.session_state.messages:
#         st.caption("Ask anything about this recording, or start with one of these:")
#         cols = st.columns(len(suggestions))
#         for col, s in zip(cols, suggestions):
#             if col.button(s, use_container_width=True):
#                 pending = s

#     for m in st.session_state.messages:
#         with st.chat_message(m["role"]):
#             st.markdown(m["content"])

#     typed = st.chat_input("Ask about this recording")
#     question = typed or pending

#     if question:
#         st.session_state.messages.append({"role": "user", "content": question})
#         with st.chat_message("user"):
#             st.markdown(question)
#         with st.chat_message("assistant"):
#             with st.spinner("Looking through the transcript…"):
#                 try:
#                     answer = ask_question(result["rag_chain"], question)
#                 except Exception as e:
#                     answer = f"I couldn't answer that: {e}"
#             st.markdown(answer)
#         st.session_state.messages.append({"role": "assistant", "content": answer})

#     if st.session_state.messages:
#         if st.button("Clear chat"):
#             st.session_state.messages = []
#             st.rerun()
