"""
Unified LLM Client — task-based routing + per-model quota fallback.

Task types and their model chains:
  "planning"      → Gemini-2.5-flash → Qwen3-32B → Qwen3.6-27B → Llama-3.3-70B
  "json"          → Qwen3-32B → Qwen3.6-27B → Llama-3.3-70B → Gemini-2.5-flash
  "code"          → Qwen3.6-27B → Qwen3-32B → Llama-3.3-70B → Gemini-2.5-flash
  "classify"      → Llama-3.1-8B → Qwen3.6-27B → Qwen3-32B
  "chat"          → Llama-3.3-70B → Qwen3-32B → Gemini-2.5-flash

Each model tracks its own exhaustion independently with a cooldown window.
When a model returns 429/quota error it is skipped for COOLDOWN_SECONDS,
then tried again automatically.

Public API:
  llm_call(prompt, task="json", ...)   → str
  llm_json(prompt, task="json", ...)   → dict | list
  llm_code(prompt, ...)                → str  (task="code")
  provider_status()                    → dict
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

# ── Model definitions ─────────────────────────────────────────────────────────

TaskType = Literal["planning", "json", "code", "classify", "chat"]

# Each provider entry: (provider, model_id, env_key_var, supports_json_mode)
@dataclass
class ModelDef:
    provider: str        # "gemini" | "groq"
    model_id: str        # actual API model string
    env_key: str         # which env var holds the API key
    json_mode: bool      # supports native JSON mode
    max_tokens: int = 8192

# All available models
_MODELS: dict[str, ModelDef] = {
    "gemini-2.5-flash": ModelDef(
        provider="gemini",
        model_id=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        env_key="GEMINI_API_KEY",
        json_mode=True,
        max_tokens=8192,
    ),
    "qwen3-32b": ModelDef(
        provider="groq",
        model_id="qwen/qwen3-32b",
        env_key="GROQ_API_KEY",
        json_mode=True,
        max_tokens=8192,
    ),
    "qwen3.6-27b": ModelDef(
        provider="groq",
        model_id="qwen/qwen3.6-27b",
        env_key="GROQ_API_KEY",
        json_mode=True,
        max_tokens=8192,
    ),
    "llama-3.3-70b": ModelDef(
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        env_key="GROQ_API_KEY",
        json_mode=True,
        max_tokens=8192,
    ),
    "llama-3.1-8b": ModelDef(
        provider="groq",
        model_id="llama-3.1-8b-instant",
        env_key="GROQ_API_KEY",
        json_mode=False,
        max_tokens=4096,
    ),
}

# Task → ordered model chain (first = preferred, rest = fallbacks)
# Qwen3 models are NOT used for classify — they have thinking overhead unsuitable
# for tiny fast classification calls.
_TASK_CHAINS: dict[TaskType, list[str]] = {
    # Gemini excels at long-context reasoning and structured planning
    "planning":  ["gemini-2.5-flash", "qwen3-32b",    "qwen3.6-27b",  "llama-3.3-70b"],
    # Qwen3-32B is excellent at strict JSON output
    "json":      ["qwen3-32b",        "qwen3.6-27b",  "llama-3.3-70b", "gemini-2.5-flash"],
    # llama-3.3-70b first for code — fast, no thinking overhead, reliable run() output.
    # Qwen3 models as fallback — strong but add 5-15s thinking latency per call.
    "code":      ["llama-3.3-70b",    "qwen3.6-27b",  "qwen3-32b",    "gemini-2.5-flash"],
    # Llama models only for classify — fast, no thinking overhead
    "classify":  ["llama-3.1-8b",     "llama-3.3-70b"],
    # Llama-3.3-70B is strong at conversational / chat tasks
    "chat":      ["llama-3.3-70b",    "qwen3-32b",    "gemini-2.5-flash"],
}

# Minimum token budget for models that use extended thinking.
# Without enough tokens the thinking block consumes the budget before the answer.
_MIN_TOKENS_THINKING = 1024   # raised: 512 was too small — thinking consumed all tokens
_THINKING_MODELS = {"qwen3-32b", "qwen3.6-27b"}


# ── Per-model exhaustion tracker ──────────────────────────────────────────────

COOLDOWN_SECONDS = 60 * 3    # 3 minutes — short enough to recover within a single run

@dataclass
class _ModelState:
    exhausted_at: float = 0.0   # timestamp when this model was exhausted (0 = not exhausted)

    def is_exhausted(self) -> bool:
        if self.exhausted_at == 0.0:
            return False
        if time.time() - self.exhausted_at > COOLDOWN_SECONDS:
            self.exhausted_at = 0.0   # cooldown expired — reset
            return False
        return True

    def mark_exhausted(self):
        self.exhausted_at = time.time()

    def remaining_cooldown(self) -> int:
        remaining = COOLDOWN_SECONDS - (time.time() - self.exhausted_at)
        return max(0, int(remaining))


_model_states: dict[str, _ModelState] = {name: _ModelState() for name in _MODELS}


# ── Public API ────────────────────────────────────────────────────────────────

def llm_call(
    prompt: str,
    task: TaskType = "json",
    system: str = "You are a helpful assistant.",
    temperature: float = 0.1,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """
    Make an LLM call routed by task type.
    Automatically falls back through the model chain on quota errors.
    Returns raw text response.

    This is a synchronous function. When called from async code that runs
    multiple tasks concurrently, wrap with asyncio.to_thread() to prevent
    blocking the event loop during the HTTP round-trip.
    """
    chain = _TASK_CHAINS.get(task, _TASK_CHAINS["json"])
    last_err = None

    for model_name in chain:
        model_def = _MODELS[model_name]
        state     = _model_states[model_name]

        # Skip if API key not configured
        key = os.getenv(model_def.env_key)
        if not key:
            continue

        # Skip if currently exhausted
        if state.is_exhausted():
            print(f"[LLM] {model_name} is exhausted (cooldown {state.remaining_cooldown()}s) — skipping")
            continue

        try:
            tokens = max_tokens or model_def.max_tokens
            # Thinking models (Qwen3) need a minimum token budget or the
            # thinking block exhausts the limit before producing an answer
            if model_name in _THINKING_MODELS:
                tokens = max(tokens, _MIN_TOKENS_THINKING)
            use_json = json_mode and model_def.json_mode

            result = _dispatch(model_def, key, prompt, system, temperature, tokens, use_json)
            # Success — log which model was used if it's not the first in chain
            if model_name != chain[0]:
                print(f"[LLM] task={task} using fallback: {model_name}")

            # Guard against empty response (can happen when thinking tokens
            # consume the entire budget — treat as a quota-style soft failure)
            if not result or not result.strip():
                print(f"[LLM] {model_name} returned empty response — trying next")
                continue

            return result

        except Exception as e:
            err_str = str(e).lower()
            last_err = e

            if _is_quota_error(err_str):
                print(f"[LLM] {model_name} quota/rate exhausted — marking cooldown, trying next")
                state.mark_exhausted()
                continue   # try next in chain
            elif _is_model_error(err_str):
                # Bad request / validation error from this model — try next without marking exhausted
                print(f"[LLM] {model_name} returned model error ({type(e).__name__}) — trying next")
                continue
            else:
                # Non-recoverable error (bad API key, etc.) — raise immediately
                raise

    # All models in the chain failed
    msg = f"All models in '{task}' chain exhausted or unavailable."
    if last_err:
        msg += f" Last error: {last_err}"
    raise RuntimeError(msg)


def llm_json(
    prompt: str,
    task: TaskType = "json",
    system: str = "You are a senior data analyst. Respond with valid JSON only.",
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> dict | list:
    """LLM call returning parsed JSON. Uses JSON mode when the model supports it."""
    raw = llm_call(
        prompt, task=task, system=system,
        temperature=temperature, max_tokens=max_tokens, json_mode=True,
    )
    return _parse_json(raw)


def llm_code(
    prompt: str,
    system: str = "You are a Python data analysis expert. Return only valid Python code.",
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """LLM call for code generation. Strips markdown fences automatically."""
    raw = llm_call(
        prompt, task="code", system=system,
        temperature=temperature, max_tokens=max_tokens, json_mode=False,
    )
    raw = re.sub(r"```python\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    return raw.strip()


def provider_status() -> dict:
    """Return status of all configured models — useful for /health/llm endpoint."""
    result = {}
    for name, defn in _MODELS.items():
        key_configured = bool(os.getenv(defn.env_key))
        state = _model_states[name]
        result[name] = {
            "provider":   defn.provider,
            "model_id":   defn.model_id,
            "configured": key_configured,
            "exhausted":  state.is_exhausted(),
            "cooldown_remaining_s": state.remaining_cooldown() if state.is_exhausted() else 0,
        }
    return result


def task_chain_status() -> dict:
    """Show which model would be used right now for each task type."""
    result = {}
    for task, chain in _TASK_CHAINS.items():
        active = None
        for name in chain:
            key = os.getenv(_MODELS[name].env_key)
            if key and not _model_states[name].is_exhausted():
                active = name
                break
        result[task] = {
            "chain":  chain,
            "active": active,   # None means all models in chain are unavailable
        }
    return result


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _dispatch(
    model_def: ModelDef,
    api_key: str,
    prompt: str,
    system: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> str:
    if model_def.provider == "gemini":
        return _gemini_call(model_def.model_id, api_key, prompt, system, temperature, max_tokens, json_mode)
    elif model_def.provider == "groq":
        return _groq_call(model_def.model_id, api_key, prompt, system, temperature, max_tokens, json_mode)
    raise ValueError(f"Unknown provider: {model_def.provider}")


# ── Gemini ────────────────────────────────────────────────────────────────────

def _gemini_call(
    model_id: str, api_key: str,
    prompt: str, system: str,
    temperature: float, max_tokens: int, json_mode: bool,
) -> str:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    gen_config = genai.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        **({"response_mime_type": "application/json"} if json_mode else {}),
    )
    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=system,
        generation_config=gen_config,
    )
    raw = model.generate_content(prompt).text.strip()
    # Strip thinking tags if present (Gemini 2.5 may emit them)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    return raw


# ── Groq ──────────────────────────────────────────────────────────────────────

def _groq_call(
    model_id: str, api_key: str,
    prompt: str, system: str,
    temperature: float, max_tokens: int, json_mode: bool,
) -> str:
    from groq import Groq

    client = Groq(api_key=api_key)

    # Groq json_object mode requires the word "JSON" in the prompt
    # and not all models support it — safer to request it only when supported
    _JSON_MODE_MODELS = {
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
        "qwen/qwen3.6-27b",
    }
    use_json_mode = json_mode and model_id in _JSON_MODE_MODELS

    kwargs: dict[str, Any] = {
        "model":    model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**kwargs)
    raw = completion.choices[0].message.content.strip()

    # Strip Qwen3 / reasoning model thinking blocks.
    # Case 1: closed block  <think>...</think>
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Case 2: unclosed block (token limit cut off before </think>)
    # If the response starts with <think> and has no closing tag, drop everything up to
    # the last newline that precedes actual content (best effort).
    if raw.startswith("<think>"):
        # Drop the whole thing — the model didn't produce usable output
        raw = ""

    return raw


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_quota_error(err_str: str) -> bool:
    return any(kw in err_str for kw in [
        "quota", "rate", "429", "exhausted",
        "ratelimit", "rate_limit", "too many",
        "resource_exhausted", "overloaded", "503",
    ])

def _is_model_error(err_str: str) -> bool:
    """Errors specific to a model that another model might not have."""
    return any(kw in err_str for kw in [
        "json_validate_failed", "failed_generation",
        "invalid_request", "bad request", "400",
        "context_length", "context length", "token",
    ])


def _parse_json(raw: str) -> dict | list:
    """Parse JSON with multiple fallback strategies."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM JSON. Raw preview: {raw[:300]}")
