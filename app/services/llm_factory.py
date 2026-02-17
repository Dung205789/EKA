from app.core.config import settings
from app.adapters.llm.ollama import OllamaLLM
from app.adapters.llm.openai import OpenAILLM

def get_llm():
    if settings.LLM_PROVIDER == "openai":
        return OpenAILLM()
    return OllamaLLM()
