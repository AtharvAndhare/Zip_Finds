# llm/llm_client.py

from openai import OpenAI
from config.settings import settings

_client = None

def get_llm_client():
    global _client

    if _client:
        return _client

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing in .env file.")

    _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client
