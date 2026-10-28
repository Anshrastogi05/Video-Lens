import imageio_ffmpeg
import glob
import os
import subprocess

import yt_dlp

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return convert_to_wav(filename)

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to mono 16 kHz WAV using bundled FFmpeg."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    subprocess.run(
        [FFMPEG_PATH, "-y", "-i", input_path, "-ac", "1", "-ar", "16000", output_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list[str]:
    pattern = f"{wav_path}_chunk_%03d.wav"
    for old_chunk in glob.glob(f"{wav_path}_chunk_*.wav"):
        os.remove(old_chunk)
    subprocess.run(
        [
            FFMPEG_PATH,
            "-y",
            "-i",
            wav_path,
            "-f",
            "segment",
            "-segment_time",
            str(chunk_minutes * 60),
            "-c",
            "copy",
            pattern,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return sorted(glob.glob(f"{wav_path}_chunk_*.wav"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download and process YouTube audio.")
    parser.add_argument("url", help="YouTube URL")
    args = parser.parse_args()
    print(download_youtube_audio(args.url))

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks
