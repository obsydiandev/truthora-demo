"""Truthora — LLM client with Groq ↔ Ollama hot-swap.

Configured via environment variables:
  LLM_PROVIDER = "groq" | "ollama"
  GROQ_API_KEY = <key>
  OLLAMA_BASE_URL = http://localhost:11434
  OLLAMA_MODEL = llama3.1:8b
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client that switches between Groq and Ollama."""

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if self.provider == "groq":
            self._api_key = os.getenv("GROQ_API_KEY", "")
            self._base_url = "https://api.groq.com/openai/v1"
            self._model = "llama-3.1-8b-instant"
        else:
            self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self._model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            self._api_key = ""

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt and return the LLM text response."""
        if self.provider == "groq":
            return await self._call_groq(prompt, system_prompt, temperature, max_tokens)
        return await self._call_ollama(prompt, system_prompt, temperature, max_tokens)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Any:
        """Send a prompt and parse the LLM response as JSON."""
        raw = await self.generate(prompt, system_prompt, temperature, max_tokens)
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)

    # ------------------------------------------------------------------
    # Groq (OpenAI-compatible API)
    # ------------------------------------------------------------------

    async def _call_groq(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Ollama (local)
    # ------------------------------------------------------------------

    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
