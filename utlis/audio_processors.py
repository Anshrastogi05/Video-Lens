import imageio_ffmpeg
import glob
import os
import subprocess
from pathlib import Path

import yt_dlp

from core.reliability import retry_call

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


def download_youtube_audio(url: str, output_dir: str = DOWNLOAD_DIR) -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
    }
    def download() -> str:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    filename = retry_call(download, operation_name="YouTube download")
    return convert_to_wav(filename)

def convert_to_wav(input_path: str, output_dir: str | None = None) -> str:
    """Convert any audio/video file to mono 16 kHz WAV using bundled FFmpeg."""
    target_dir = output_dir or os.path.dirname(input_path)
    os.makedirs(target_dir, exist_ok=True)
    output_path = os.path.join(target_dir, Path(input_path).stem + "_converted.wav")

    def convert() -> None:
        subprocess.run(
            [FFMPEG_PATH, "-y", "-i", input_path, "-ac", "1", "-ar", "16000", output_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    retry_call(convert, operation_name="Audio conversion")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10, output_dir: str | None = None) -> list[str]:
    chunk_dir = output_dir or os.path.dirname(wav_path)
    os.makedirs(chunk_dir, exist_ok=True)
    pattern = os.path.join(chunk_dir, "chunk_%03d.wav")

    def chunk() -> None:
        subprocess.run(
            [FFMPEG_PATH, "-y", "-i", wav_path, "-f", "segment", "-segment_time", str(chunk_minutes * 60), "-c", "copy", pattern],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    retry_call(chunk, operation_name="Audio chunking")
    return sorted(glob.glob(os.path.join(chunk_dir, "chunk_*.wav")))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download and process YouTube audio.")
    parser.add_argument("url", help="YouTube URL")
    args = parser.parse_args()
    print(download_youtube_audio(args.url))

def prepare_audio(source: str, work_dir: str | None = None) -> str:
    work_dir = work_dir or DOWNLOAD_DIR
    os.makedirs(work_dir, exist_ok=True)
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source, output_dir=work_dir)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source, output_dir=work_dir)

    return wav_path


def process_input(source: str, work_dir: str | None = None) -> list[str]:
    work_dir = work_dir or DOWNLOAD_DIR
    wav_path = prepare_audio(source, work_dir=work_dir)
    print("Chunking audio...")
    chunks = chunk_audio(wav_path, output_dir=work_dir)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks
