"""Shared transport for the configured OpenAI-compatible chat API."""
import json

import httpx

from it_career_navigator.config import settings


def is_configured():
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


def remove_markdown_fence(content):
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        raise ValueError("Incomplete Markdown code fence")
    return "\n".join(lines[1:-1])


async def request_json(system, user, *, max_tokens=1200):
    if not is_configured():
        raise ValueError("LLM is not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": "Bearer " + settings.llm_api_key.get_secret_value()},
            json={
                "model": settings.llm_model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("LLM response is not text")
    return json.loads(remove_markdown_fence(content))
