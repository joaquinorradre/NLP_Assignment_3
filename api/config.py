import os

class Config:
    # MinIO
    MINIO_ENDPOINT     = os.environ["MINIO_ENDPOINT"]        # minio:9000
    MINIO_ACCESS_KEY   = os.environ["MINIO_ROOT_USER"]
    MINIO_SECRET_KEY   = os.environ["MINIO_ROOT_PASSWORD"]
    MINIO_BUCKET       = os.environ.get("MINIO_BUCKET", "documents")

    # ChromaDB
    CHROMA_HOST        = os.environ.get("CHROMA_HOST", "localhost")
    CHROMA_PORT        = int(os.environ.get("CHROMA_PORT", 8000))

    # LLM (llama-server OpenAI-compatible endpoint)
    LLM_HOST           = os.environ.get("LLM_HOST", "localhost")
    LLM_PORT           = int(os.environ.get("LLM_PORT", 8080))
    LLM_URL            = f"http://{LLM_HOST}:{LLM_PORT}"