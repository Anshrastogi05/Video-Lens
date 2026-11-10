from dotenv import load_dotenv
from importlib import import_module

audio_processors = import_module("utlis.audio_processors")
process_input = audio_processors.process_input
prepare_audio = audio_processors.prepare_audio
from core.transcriber import transcribe_all, transcribe_file_sarvam_batch
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question
from core.job_storage import create_job, cleanup_audio_job, cleanup_vector_job, cleanup_expired_vector_jobs


load_dotenv()

def run_pipeline(source :str, language :str = "english") -> dict:
    print("starting AI Video Assistant")
    cleanup_expired_vector_jobs()
    job_id, audio_dir, vector_dir = create_job()
    completed = False
    try:
        if language.lower() == "hinglish":
            # Keep the complete recording together so speaker labels remain
            # consistent across the entire conversation.
            wav_path = prepare_audio(source, work_dir=str(audio_dir))
            transcript = transcribe_file_sarvam_batch(
                wav_path,
                output_dir=str(audio_dir / "sarvam_batch_output"),
            )
        else:
            chunks = process_input(source, work_dir=str(audio_dir))
            if not chunks:
                raise RuntimeError("No audio chunks were produced")
            transcript = transcribe_all(chunks, language)
        if not transcript.strip():
            raise RuntimeError("Transcription returned no text")
        print(f"raw transcription (first 300 characters ) {transcript[:300]}")

        title = generate_title(transcript)
        summary = summarize(transcript)
        action_item = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)
        rag_chain = build_rag_chain(
            transcript,
            vector_dir=str(vector_dir),
            collection_name=f"meeting_{job_id}",
        )

        result = {
            "job_id": job_id,
            "title": title,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_item,
            "key_decisions": decisions,
            "open_questions": questions,
            "rag_chain": rag_chain,
        }
        completed = True
        return result
    finally:
        # The RAG chain uses the persistent vector_dir; raw media is disposable.
        cleanup_audio_job(audio_dir)
        if not completed:
            cleanup_vector_job(vector_dir)

if __name__ == "__main__":
    # CLI entry point
    source = input("Enter YouTube URL or local file path: ").strip()
    language = input("Language (english/hinglish): ").strip() or "english"
    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n📋 Summary:\n{result['summary']}")
    print(f"\n✅ Action Items:\n{result['action_items']}")
    print(f"\n🔑 Key Decisions:\n{result['key_decisions']}")
    print(f"\n❓ Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # Phase 2 — Chat with your meeting via RAG
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")
    rag_chain = result["rag_chain"]
    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue
        answer = ask_question(rag_chain, question)
        print(f"\n🤖 Assistant: {answer}\n")
