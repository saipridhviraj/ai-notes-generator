"""Unified LLM client — Groq cloud or local Ollama, with optional Groq fallback."""
import os
import re
import sys
import json
import time
import httpx
from groq import Groq

from services.llm_config import get_provider_name, use_ollama

GROQ_MODELS = {
    "small":     "llama-3.1-8b-instant",
    "large":     "llama-3.3-70b-versatile",
    "reasoning": "llama-3.3-70b-versatile",
}

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
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        self.client = Groq(api_key=api_key)

    def complete(
        self,
        prompt: str,
        size: str = "large",
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        session_id: str | None = None,
        stream_node: str | None = None,
        think: bool | None = None,
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
                    think=think,
                    llm_options=llm_options,
                ),
                session_id,
                stream_node,
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                create_kwargs: dict = {
                    "model": GROQ_MODELS[size],
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if llm_options and "top_p" in llm_options:
                    create_kwargs["top_p"] = llm_options["top_p"]
                response = self.client.chat.completions.create(**create_kwargs)
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "rate_limit_exceeded" in error_str or "429" in error_str
                if is_rate_limit and attempt < max_attempts:
                    wait = 15.0
                    match = re.search(r"try again in ([\d.]+)s", error_str)
                    if match:
                        wait = float(match.group(1)) + 1.0
                    print(
                        f"[GroqClient] Rate limit hit — waiting {wait:.0f}s "
                        f"(attempt {attempt}/{max_attempts})",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                print(f"[GroqClient] Error calling {GROQ_MODELS[size]}: {e}", file=sys.stderr)
                raise

    def iter_complete(
        self,
        prompt: str,
        size: str = "large",
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        think: bool | None = None,
        llm_options: dict | None = None,
    ):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        create_kwargs: dict = {
            "model": GROQ_MODELS[size],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if llm_options and "top_p" in llm_options:
            create_kwargs["top_p"] = llm_options["top_p"]
        stream = self.client.chat.completions.create(**create_kwargs)
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
