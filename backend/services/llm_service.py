"""
llm_service.py
Wrapper untuk Local LLM menggunakan Ollama (mis. llama3 / mistral).
"""

from langchain_ollama import ChatOllama

from config import settings

_llm_client: ChatOllama | None = None


def get_llm(temperature: float = 0.2) -> ChatOllama:
    """
    Mengembalikan instance ChatOllama.
    temperature rendah karena assistant ini menjawab berdasarkan context/tool result,
    bukan untuk generasi kreatif.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_LLM_MODEL,
            temperature=temperature,
        )
    return _llm_client
