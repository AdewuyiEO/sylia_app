"""Shared LLM client (spec §1.1, §4.4) — provider-abstracted.

One place that talks to whatever LLM you configure. Every caller (daily-look
explanation, style coach, identity extraction) goes through `complete()` /
`stream()`; NOTHING else imports a vendor SDK. Swapping Anthropic ↔ OpenAI ↔ any
future provider is a one-line env change (LLM_PROVIDER) + a small adapter class —
no caller changes.

Centralises:
  * provider selection (anthropic | openai | none);
  * model-tier selection (small/fast for explanations, capable for coach);
  * prompt caching where the provider supports it (Anthropic ephemeral cache) —
    the big static identity+wardrobe preamble is cached, the single biggest cost
    lever at scale;
  * a deterministic fallback so every caller works with NO provider configured —
    the app is fully functional offline, copy is just templated not generated.
"""
from __future__ import annotations

from collections.abc import Iterator

from ..config import get_settings

settings = get_settings()


# ── provider adapters ────────────────────────────────────────────────────────
class _BaseProvider:
    name = "none"
    def available(self) -> bool: return False
    def complete(self, system, messages, *, model, max_tokens) -> str: raise NotImplementedError
    def stream(self, system, messages, *, model, max_tokens) -> Iterator[str]: raise NotImplementedError


class _AnthropicProvider(_BaseProvider):
    name = "anthropic"

    def __init__(self):
        self._ok = False
        try:
            import anthropic
            if settings.anthropic_api_key:
                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self._ok = True
        except Exception:
            self._ok = False

    def available(self) -> bool:
        return self._ok

    def _system_block(self, system: str):
        # Anthropic supports prompt caching via cache_control
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    def complete(self, system, messages, *, model, max_tokens):
        resp = self._client.messages.create(
            model=model, max_tokens=max_tokens,
            system=self._system_block(system), messages=messages)
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def stream(self, system, messages, *, model, max_tokens):
        with self._client.messages.stream(
            model=model, max_tokens=max_tokens,
            system=self._system_block(system), messages=messages) as s:
            for text in s.text_stream:
                yield text


class _OpenAIProvider(_BaseProvider):
    name = "openai"

    def __init__(self):
        self._ok = False
        try:
            import openai
            if settings.openai_api_key:
                self._client = openai.OpenAI(api_key=settings.openai_api_key)
                self._ok = True
        except Exception:
            self._ok = False

    def available(self) -> bool:
        return self._ok

    def _messages(self, system, messages):
        # OpenAI takes the system prompt as the first message
        return [{"role": "system", "content": system}, *messages]

    def complete(self, system, messages, *, model, max_tokens):
        resp = self._client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=self._messages(system, messages))
        return resp.choices[0].message.content or ""

    def stream(self, system, messages, *, model, max_tokens):
        s = self._client.chat.completions.create(
            model=model, max_tokens=max_tokens, stream=True,
            messages=self._messages(system, messages))
        for chunk in s:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


_PROVIDERS = {"anthropic": _AnthropicProvider, "openai": _OpenAIProvider}
_provider: _BaseProvider | None = None


def _get_provider() -> _BaseProvider:
    global _provider
    if _provider is None:
        cls = _PROVIDERS.get(settings.llm_provider.lower(), _BaseProvider)
        _provider = cls()
    return _provider


def available() -> bool:
    return _get_provider().available()


def provider_name() -> str:
    return _get_provider().name


# ── model-tier resolution (provider-specific names live in config) ───────────
def model_for(tier: str) -> str:
    """tier: 'explanation' | 'coach'. Returns the configured model id for the
    active provider, so callers ask for a role, not a vendor model string."""
    if settings.llm_provider.lower() == "openai":
        return settings.openai_model_coach if tier == "coach" else settings.openai_model_explanation
    return settings.model_coach if tier == "coach" else settings.model_explanation


# ── public API (unchanged for callers) ───────────────────────────────────────
def complete(system: str, messages: list[dict], *, model: str,
             max_tokens: int = 600, fallback: str = "") -> str:
    p = _get_provider()
    if not p.available():
        return fallback
    try:
        return p.complete(system, messages, model=model, max_tokens=max_tokens)
    except Exception:
        return fallback


def stream(system: str, messages: list[dict], *, model: str,
           max_tokens: int = 600, fallback: str = "") -> Iterator[str]:
    p = _get_provider()
    if not p.available():
        for chunk in _chunk(fallback):
            yield chunk
        return
    try:
        yield from p.stream(system, messages, model=model, max_tokens=max_tokens)
    except Exception:
        for chunk in _chunk(fallback):
            yield chunk


def _chunk(text: str, size: int = 24) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i:i + size]
