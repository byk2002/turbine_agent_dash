import os
from functools import lru_cache
from typing import Tuple

from langchain_openai import ChatOpenAI

from .llm_profiles import PROFILES, LLMProfile

def list_llm_profiles() -> dict[str, LLMProfile]:
    return PROFILES

@lru_cache(maxsize=64)
def get_llm(profile_key: str, temperature: float = 0.2) -> Tuple[ChatOpenAI, LLMProfile]:
    if profile_key not in PROFILES:
        raise KeyError(f"Unknown LLM profile_key: {profile_key}")

    p = PROFILES[profile_key]
    api_key = os.getenv(p.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing API key env var: {p.api_key_env} for profile={p.key} ({p.label})"
        )

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=p.base_url,
        model=p.model,
        temperature=temperature,
    )
    return llm, p
