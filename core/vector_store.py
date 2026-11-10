import os 
from langchain_chroma import Chroma 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL,
        model_kwargs = {"device" : 'cpu'}
    )


def build_vector_store(transcript: str, job_dir: str | None = None, collection_name: str | None = None) -> Chroma:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty")

    print("Building vector Store")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50
    )
    chunks = splitter.split_text(transcript)

    docs = [
        Document(page_content=chunk, metadata = {'chunk_index' : i})
        for i,chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents= docs,
        embedding=embeddings,
        collection_name=collection_name or COLLECTION_NAME,
        persist_directory=job_dir or CHROMA_DIR,
    )

    return vector_store



def load_vector_store(job_dir: str | None = None, collection_name: str | None = None) -> Chroma:
    vector_dir = job_dir or CHROMA_DIR
    if not os.path.isdir(vector_dir):
        raise FileNotFoundError(
            f"Vector store directory does not exist: {vector_dir}. "
            "Build the vector store before loading it."
        )

    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=collection_name or COLLECTION_NAME,
        embedding_function= embeddings,
        persist_directory=vector_dir
    )

    return vector_store

def get_retriever(vector_store : Chroma, k :int = 4):
    return vector_store.as_retriever(
        search_type = 'similarity',
        search_kwargs = {"k":k}
    )
