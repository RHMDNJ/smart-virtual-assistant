"""
embedding_service.py
Wrapper untuk membuat embedding teks menggunakan model Ollama (mis. nomic-embed-text).
"""

from langchain_ollama import OllamaEmbeddings

from config import settings

_embeddings_client: OllamaEmbeddings | None = None


def get_embeddings_client() -> OllamaEmbeddings:
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_EMBEDDING_MODEL,
        )
    return _embeddings_client


def embed_text(text: str) -> list[float]:
    """Embed satu teks (query atau chunk dokumen) menjadi vector."""
    client = get_embeddings_client()
    return client.embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed banyak teks sekaligus (batch), lebih efisien untuk indexing dokumen."""
    client = get_embeddings_client()
    return client.embed_documents(texts)
