"""Unified LLM client — Groq cloud or local Ollama, with optional Groq fallback.

Model tiers (Groq):
  small     — fast/cheap  : planner, research, evaluator-light, mermaid repair
  medium    — balanced    : gap bridger, diagram generation
  large     — high quality: student notes, tutor notes
  reasoning — chain-of-thought: evaluator full

Each tier has a fallback chain; on rate-limit the next model is tried
automatically. Set GROQ_API_KEY_2 / GROQ_API_KEY_3 for multi-key
round-robin to further stretch rate limits.
"""
import itertools
import os
import re
import sys
import json
import time
import httpx
from groq import Groq

from services.llm_config import get_provider_name, use_ollama

# ── Model chains — primary first, fallbacks after ─────────────────────────────
# Override any tier with env vars, e.g. GROQ_MODEL_LARGE=llama-3.3-70b-versatile
GROQ_MODEL_CHAINS: dict[str, list[str]] = {
    "small": [
        os.getenv("GROQ_MODEL_SMALL", "llama-3.1-8b-instant"),
        "gemma2-9b-it",
    ],
    "medium": [
        os.getenv("GROQ_MODEL_MEDIUM", "gemma2-9b-it"),
        "llama-3.1-8b-instant",
    ],
    "large": [
        os.getenv("GROQ_MODEL_LARGE", "llama-3.3-70b-versatile"),
        "mixtral-8x7b-32768",       # long-context fallback
        "gemma2-9b-it",             # last resort
    ],
    "reasoning": [
        os.getenv("GROQ_MODEL_REASONING", "deepseek-r1-distill-llama-70b"),
        "llama-3.3-70b-versatile",  # fallback if reasoning quota hit
    ],
}

# Backward-compatible single-model map (primary of each chain)
GROQ_MODELS = {tier: chain[0] for tier, chain in GROQ_MODEL_CHAINS.items()}


def _get_api_keys() -> list[str]:
    """Collect all configured Groq API keys for round-robin use."""
    keys = []
    for suffix in ("", "_2", "_3"):
        k = os.getenv(f"GROQ_API_KEY{suffix}", "").strip()
        if k:
            keys.append(k)
    return keys or [""]   # empty string → GroqClient will raise a clear error

DEFAULT_OLLAMA_MODEL = "qwen3.5:9b-q4_K_M"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _fallback_enabled() -> bool:
    flag = os.getenv("LLM_FALLBACK_GROQ", "true").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _streaming_enabled() -> bool:
    flag = os.getenv("LLM_STREAMING", "true").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _ollama_think_enabled() -> bool:
    """Off by default — Qwen 3.x thinking adds latency with little benefit here."""
    flag = os.getenv("OLLAMA_THINK", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _resolve_ollama_think(think: bool | None) -> bool:
    if think is not None:
        return think
    return _ollama_think_enabled()


_THINKING_BLOCK_RE = re.compile(
    "<think" + r">.*?<\/think>\s*",
    re.DOTALL | re.IGNORECASE,
)


def _strip_thinking_blocks(text: str) -> str:
    """Fallback if thinking trace leaks into message.content."""
    return _THINKING_BLOCK_RE.sub("", text).strip()


def check_ollama_reachable() -> bool | None:
    """Return True/False if Ollama mode; None if not using Ollama."""
    if not use_ollama():
        return None
    base = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{base}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


class GroqClient:
    """Groq client with per-tier model fallback chains and multi-key round-robin."""

    # Shared key cycle across all instances so concurrent calls spread load
    _key_cycle: "itertools.cycle[str] | None" = None

    def __init__(self):
        keys = _get_api_keys()
        if not any(keys):
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        if GroqClient._key_cycle is None:
            GroqClient._key_cycle = itertools.cycle(keys)
        # Primary client uses first key; _next_client() rotates
        self._clients = {k: Groq(api_key=k) for k in keys}
        self._keys = keys

    def _next_client(self) -> Groq:
        key = next(GroqClient._key_cycle)  # type: ignore[arg-type]
        return self._clients[key]

    # ── Core call with model-chain + multi-key fallback ────────────────────────

    def _call_with_fallback(
        self,
        messages: list[dict],
        size: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        llm_options: dict | None,
    ):
        """Try each model in the chain for `size`, rotating keys on rate-limit."""
        chain = GROQ_MODEL_CHAINS.get(size, GROQ_MODEL_CHAINS["large"])
        last_exc: Exception | None = None

        for model in chain:
            retries = len(self._keys) * 2  # try each key twice per model
            for attempt in range(1, retries + 1):
                client = self._next_client()
                try:
                    create_kwargs: dict = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if stream:
                        create_kwargs["stream"] = True
                    if llm_options and "top_p" in llm_options:
                        create_kwargs["top_p"] = llm_options["top_p"]

                    result = client.chat.completions.create(**create_kwargs)
                    print(f"[GroqClient] ✓ {model} (size={size})", file=sys.stderr)
                    return model, result

                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = "rate_limit_exceeded" in error_str or "429" in error_str
                    if is_rate_limit:
                        wait = 5.0
                        match = re.search(r"try again in ([\d.]+)s", error_str)
                        if match:
                            wait = float(match.group(1)) + 1.0
                        print(
                            f"[GroqClient] Rate limit on {model} key#{attempt} — "
                            f"{'waiting' if attempt >= retries else 'rotating key'} {wait:.0f}s",
                            file=sys.stderr,
                        )
                        if attempt >= retries:
                            last_exc = e
                            break   # move to next model in chain
                        time.sleep(min(wait, 10.0))
                        continue
                    # Non-rate-limit error on this model — try next model
                    print(f"[GroqClient] {model} error: {e} — trying next model", file=sys.stderr)
                    last_exc = e
                    break

        raise RuntimeError(
            f"All models in chain for size='{size}' failed. Last error: {last_exc}"
        )

    def complete(
        self,
        prompt: str,
        size: str = "large",
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        session_id: str | None = None,
        stream_node: str | None = None,
        think: bool | None = None,  # noqa: ARG002 (Groq doesn't use think)
        llm_options: dict | None = None,
    ) -> str:
        if session_id and stream_node and _streaming_enabled():
            return self._collect_stream(
                self.iter_complete(
                    prompt=prompt,
                    size=size,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    llm_options=llm_options,
                ),
                session_id,
                stream_node,
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        _, response = self._call_with_fallback(
            messages, size, temperature, max_tokens, stream=False, llm_options=llm_options
        )
        return response.choices[0].message.content

    def iter_complete(
        self,
        prompt: str,
        size: str = "large",
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        think: bool | None = None,  # noqa: ARG002
        llm_options: dict | None = None,
    ):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        _, stream = self._call_with_fallback(
            messages, size, temperature, max_tokens, stream=True, llm_options=llm_options
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token

    @staticmethod
    def _collect_stream(token_iter, session_id: str, stream_node: str) -> str:
        from utils.stream_bus import end_node, publish_token, start_node

        start_node(session_id, stream_node)
        parts: list[str] = []
        try:
            for token in token_iter:
                parts.append(token)
                publish_token(session_id, stream_node, token)
        finally:
            end_node(session_id, stream_node)
        return "".join(parts)

    def complete_json(
        self,
        prompt: str,
        size: str = "large",
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        session_id: str | None = None,
        stream_node: str | None = None,
        think: bool | None = None,
    ) -> dict:
        raw = self.complete(
            prompt=prompt,
            size=size,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            session_id=session_id,
            stream_node=stream_node,
            think=think,
        )
        return _parse_json_response(raw, "GroqClient")


class OllamaClient:
    """Local inference via Ollama's /api/chat endpoint."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "600"))

    def complete(
        self,
        prompt: str,
        size: str = "large",  # noqa: ARG002
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        session_id: str | None = None,
        stream_node: str | None = None,
        think: bool | None = None,
        llm_options: dict | None = None,
    ) -> str:
        if session_id and stream_node and _streaming_enabled():
            return GroqClient._collect_stream(
                self.iter_complete(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    think=think,
                    llm_options=llm_options,
                ),
                session_id,
                stream_node,
            )

        payload = self._build_payload(
            prompt, system, temperature, max_tokens, stream=False, think=think, llm_options=llm_options
        )
        return self._post_chat(payload)

    def iter_complete(
        self,
        prompt: str,
        size: str = "large",  # noqa: ARG002
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        think: bool | None = None,
        llm_options: dict | None = None,
    ):
        payload = self._build_payload(
            prompt, system, temperature, max_tokens, stream=True, think=think, llm_options=llm_options
        )
        yield from self._iter_chat(payload)

    def complete_json(
        self,
        prompt: str,
        size: str = "large",  # noqa: ARG002
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        session_id: str | None = None,
        stream_node: str | None = None,
        think: bool | None = None,
    ) -> dict:
        if session_id and stream_node and _streaming_enabled():
            raw = GroqClient._collect_stream(
                self._iter_json_complete(
                    prompt, system, temperature, max_tokens, think=think
                ),
                session_id,
                stream_node,
            )
        else:
            payload = self._build_payload(
                prompt,
                system,
                temperature,
                max_tokens,
                stream=False,
                json_mode=True,
                think=think,
            )
            raw = self._post_chat(payload)
        return _parse_json_response(raw, "OllamaClient")

    def _iter_json_complete(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        think: bool | None = None,
    ):
        payload = self._build_payload(
            prompt,
            system,
            temperature,
            max_tokens,
            stream=True,
            json_mode=True,
            think=think,
        )
        yield from self._iter_chat(payload)

    def _build_payload(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        json_mode: bool = False,
        think: bool | None = None,
        llm_options: dict | None = None,
    ) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        options: dict = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": self.num_ctx,
        }
        if llm_options:
            options.update(llm_options)

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "think": _resolve_ollama_think(think),
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
            "options": options,
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def _post_chat(self, payload: dict) -> str:
        url = f"{self.base_url}/api/chat"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"OllamaClient: cannot reach {self.base_url}. "
                "Is Ollama running? Try: ollama serve"
            ) from e
        except httpx.HTTPStatusError as e:
            print(
                f"[OllamaClient] HTTP {e.response.status_code}: {e.response.text}",
                file=sys.stderr,
            )
            raise

        content = data.get("message", {}).get("content")
        if not content:
            raise ValueError(f"OllamaClient: empty response from {self.model}")
        return _strip_thinking_blocks(content)

    def _iter_chat(self, payload: dict):
        url = f"{self.base_url}/api/chat"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"OllamaClient: cannot reach {self.base_url}. "
                "Is Ollama running? Try: ollama serve"
            ) from e
        except httpx.HTTPStatusError as e:
            print(
                f"[OllamaClient] HTTP {e.response.status_code}: {e.response.text}",
                file=sys.stderr,
            )
            raise


def _parse_json_response(raw: str, client_name: str) -> dict:
    cleaned = _strip_json_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{client_name}: response was not valid JSON.\nError: {e}\nRaw response:\n{raw}"
        ) from e


def _groq_fallback_available() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


class _LazyLLMClient:
    """Routes to Groq or Ollama; optional Groq fallback when Ollama fails."""

    _instance: GroqClient | OllamaClient | None = None
    _provider: str | None = None
    _groq_fallback: GroqClient | None = None

    def _get(self) -> GroqClient | OllamaClient:
        provider = get_provider_name()
        if self._instance is None or self._provider != provider:
            self._provider = provider
            if use_ollama():
                print(f"[LLM] Using Ollama ({self._build_ollama()})", file=sys.stderr)
                self._instance = OllamaClient()
            else:
                print("[LLM] Using Groq", file=sys.stderr)
                self._instance = GroqClient()
        return self._instance

    def _get_groq_fallback(self) -> GroqClient:
        if self._groq_fallback is None:
            self._groq_fallback = GroqClient()
        return self._groq_fallback

    def _build_ollama(self) -> str:
        model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        base = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        return f"{model} @ {base}"

    def _with_fallback(self, fn_name: str, *args, **kwargs):
        stream_kwargs = {}
        if fn_name == "complete":
            stream_kwargs = {
                k: kwargs.pop(k)
                for k in ("session_id", "stream_node")
                if k in kwargs
            }
        client = self._get()
        try:
            if fn_name == "complete" and stream_kwargs:
                kwargs.update(stream_kwargs)
            return getattr(client, fn_name)(*args, **kwargs)
        except (ConnectionError, httpx.ConnectError, httpx.TimeoutException) as e:
            if (
                use_ollama()
                and _fallback_enabled()
                and _groq_fallback_available()
            ):
                print(
                    f"[LLM] Ollama unavailable — falling back to Groq ({e})",
                    file=sys.stderr,
                )
                fallback = self._get_groq_fallback()
                if fn_name == "complete" and stream_kwargs:
                    kwargs.update(stream_kwargs)
                return getattr(fallback, fn_name)(*args, **kwargs)
            raise

    def complete(self, *args, **kwargs) -> str:
        return self._with_fallback("complete", *args, **kwargs)

    def complete_json(self, *args, **kwargs) -> dict:
        return self._with_fallback("complete_json", *args, **kwargs)


llm_client = _LazyLLMClient()
groq_client = llm_client  # backward-compatible alias
