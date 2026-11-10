import whisper
import os
import requests
import argparse
import glob
import shutil
import json
from pathlib import Path
from dotenv import load_dotenv
from core.reliability import retry_call

ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    ffmpeg_candidates = glob.glob(
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft",
            "WinGet",
            "Packages",
            "**",
            "ffmpeg.exe",
        ),
        recursive=True,
    )
    ffmpeg_path = ffmpeg_candidates[0] if ffmpeg_candidates else None
if ffmpeg_path:
    os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ["PATH"]

from pydub import AudioSegment

load_dotenv()

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
SARVAM_PIECE_SECONDS = 25


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")


SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# Use the current STT endpoint. The legacy speech-to-text-translate endpoint
# always returns English, which is why the old "hinglish" output was English.
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4")
SARVAM_MODE = os.getenv("SARVAM_MODE", "codemix")
SARVAM_LANGUAGE_CODE = os.getenv("SARVAM_LANGUAGE_CODE", "unknown")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
_model = None


def load_model():

    global _model  

    if _model is None: 
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        _model = whisper.load_model(WHISPER_MODEL) 
        print("Whisper model loaded.")
    return _model 


def transcribe_chunk_whisper(chunk_path: str) -> str:

    model = load_model()  

    result = model.transcribe(chunk_path, task="transcribe")
    text = result["text"]
    return text if isinstance(text, str) else " ".join(str(item) for item in text)


def _send_to_sarvam(piece_path: str) -> str:
    """Send one ≤30s WAV file to Sarvam and preserve Hindi-English code-mix."""
    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {
            "model": SARVAM_MODEL,
            "mode": SARVAM_MODE,
            "language_code": SARVAM_LANGUAGE_CODE,
            "with_timestamps": "true",
        }
        response = requests.post(
            SARVAM_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"\n❌ Sarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    payload = response.json()
    return payload.get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str) -> str:
    """
    Sarvam sync API only accepts ≤30s audio. We split this chunk into
    25-second pieces, send each separately, and join the transcripts.
    """
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000

    full_text = ""
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")

        try:
            print(f"  → Sarvam piece {i + 1}/{total_pieces} ...")
            full_text += retry_call(
                lambda: _send_to_sarvam(piece_path),
                operation_name="Sarvam transcription",
            ) + " "
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    return full_text.strip()


def transcribe_file_sarvam_batch(
    wav_path: str,
    output_dir: str,
    num_speakers: int | None = None,
) -> str:
    """Transcribe one complete recording with Sarvam speaker diarization."""
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    try:
        from sarvamai import SarvamAI
    except ImportError as exc:
        raise RuntimeError(
            "Sarvam Batch diarization requires the 'sarvamai' package. "
            "Install dependencies with: python -m pip install -r Requirements.txt"
        ) from exc

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    job_kwargs = {
        "model": SARVAM_MODEL,
        "mode": SARVAM_MODE,
        "language_code": SARVAM_LANGUAGE_CODE,
        "with_diarization": True,
    }
    if num_speakers is not None:
        job_kwargs["num_speakers"] = num_speakers

    print("Starting Sarvam Batch transcription with speaker diarization...")
    job = client.speech_to_text_job.create_job(**job_kwargs)
    job.upload_files(file_paths=[wav_path])
    job.start()
    job.wait_until_complete(timeout=int(os.getenv("SARVAM_BATCH_TIMEOUT", "1800")))
    job.download_outputs(output_dir=str(output_path))

    result_files = sorted(output_path.glob("*.json"))
    if not result_files:
        raise RuntimeError("Sarvam Batch completed without a JSON transcript output")

    with result_files[0].open("r", encoding="utf-8") as result_file:
        payload = json.load(result_file)

    entries = payload.get("diarized_transcript", {}).get("entries", [])
    if not entries:
        raise RuntimeError("Sarvam Batch returned no diarized transcript entries")

    formatted = []
    for entry in entries:
        speaker = entry.get("speaker_id", "unknown")
        text = str(entry.get("transcript", "")).strip()
        if text:
            start = entry.get("start_time_seconds")
            timestamp = f" [{start:.2f}s]" if isinstance(start, (int, float)) else ""
            formatted.append(f"[Speaker {speaker}]{timestamp}: {text}")
    return "\n".join(formatted)

   



def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  → Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list[str], language: str = "english") -> str:

    full_transcript = "" 

    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    for i, chunk in enumerate(chunks):  

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        text = transcribe_chunk(chunk, language=language)  

        full_transcript += text + " "  

    print("Transcription complete.")

    return full_transcript.strip()  


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe one or more WAV audio files with Whisper or Sarvam."
    )
    parser.add_argument(
        "audio_files",
        nargs="*",
        help="Paths to WAV files; omitted uses WAV chunks in downloads",
    )
    parser.add_argument(
        "--language",
        choices=("english", "hinglish"),
        default="english",
        help="Transcription engine/language mode (default: english)",
    )
    args = parser.parse_args()

    audio_files = args.audio_files
    if not audio_files:
        audio_files = sorted(glob.glob(os.path.join("downloads", "*_chunk_*.wav")))
        if not audio_files:
            parser.error(
                "No audio files supplied and no WAV chunks were found in the downloads folder"
            )
        print(f"Using {len(audio_files)} audio chunk(s) from downloads.")

    transcript = transcribe_all(audio_files, language=args.language)
    print("\nTranscript:\n")
    print(transcript)
