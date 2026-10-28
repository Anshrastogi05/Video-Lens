import glob
import os
import subprocess

from dotenv import load_dotenv
from sarvamai import SarvamAI

from utlis.audio_processors import FFMPEG_PATH, download_youtube_audio


load_dotenv()

source = "https://youtu.be/Ty8gcCKuwNI?si=Yyt2YhKxbbO2dRFG"
existing_audio = glob.glob("downloads/What is RAG*_converted.wav")
audio_path = existing_audio[0] if existing_audio else download_youtube_audio(source)
print("Audio prepared.", flush=True)

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])

chunk_dir = "transcript_chunks"
os.makedirs(chunk_dir, exist_ok=True)
if not glob.glob(os.path.join(chunk_dir, "*.wav")):
    subprocess.run(
        [
            FFMPEG_PATH,
            "-y",
            "-i",
            audio_path,
            "-f",
            "segment",
            "-segment_time",
            "25",
            "-c",
            "copy",
            os.path.join(chunk_dir, "chunk_%03d.wav"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

chunks = sorted(glob.glob(os.path.join(chunk_dir, "*.wav")))
start = int(os.getenv("START_CHUNK", "0"))
end = min(int(os.getenv("END_CHUNK", str(len(chunks)))), len(chunks))
transcript_parts = []
for index, chunk_path in enumerate(chunks[start:end], start + 1):
    print(f"Transcribing chunk {index}/{len(chunks)}...", flush=True)
    with open(chunk_path, "rb") as audio_file:
        response = client.speech_to_text.transcribe(
            file=audio_file,
            model="saaras:v4",
            mode="transcribe",
        )
    transcript_parts.append(response.transcript)

transcript = "\n\n".join(transcript_parts)

output_dir = "transcripts"
os.makedirs(output_dir, exist_ok=True)
transcript_path = os.path.join(output_dir, "Ty8gcCKuwNI.txt")
mode = "a" if start else "w"
with open(transcript_path, mode, encoding="utf-8") as transcript_file:
    if start and os.path.getsize(transcript_path) > 0:
        transcript_file.write("\n\n")
    transcript_file.write(transcript)

print(transcript_path)
