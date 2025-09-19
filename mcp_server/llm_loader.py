import os
from langchain_ollama import OllamaLLM

def get_llm(provider: str = None, model: str = None):
    if not provider :
        provider = provider or os.getenv("LLM_PROVIDER", "ollama")
    if not model:
        model = model or os.getenv("LLM_MODEL", "artifish/llama3.2-uncensored")

    if provider == "ollama":
        return OllamaLLM(model=model)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
