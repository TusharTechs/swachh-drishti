"""LLM backends shared by the agents.

DRISHTI_LLM selects the backend (default: auto):
  * anthropic - Claude via the Anthropic SDK (needs ANTHROPIC_API_KEY or an `ant` profile)
  * local     - any open-weight model served locally with an OpenAI-compatible API
                (LM Studio default http://localhost:1234/v1; set DRISHTI_LOCAL_URL / DRISHTI_LOCAL_MODEL)
  * none      - no LLM; agents fall back to deterministic rules (agents/rules.py)
auto = anthropic if a key is set, else local if the local server answers, else none.
"""
from __future__ import annotations
import base64, json, os
from pathlib import Path
import requests

LOCAL_URL = os.environ.get("DRISHTI_LOCAL_URL", "http://localhost:1234/v1")
LOCAL_MODEL = os.environ.get("DRISHTI_LOCAL_MODEL", "google/gemma-4-e4b")
CLAUDE_MODEL = os.environ.get("DRISHTI_MODEL", "claude-opus-5-5")

def backend() -> str:
    b = os.environ.get("DRISHTI_LLM", "auto")
    if b != "auto":
        return b
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    try:
        requests.get(LOCAL_URL + "/models", timeout=2).raise_for_status()
        return "local"
    except Exception:
        return "none"

def model_name() -> str:
    return {"anthropic": CLAUDE_MODEL, "local": LOCAL_MODEL}.get(backend(), "rules")

def png_block(path: Path) -> dict:
    """Neutral image block; converted per backend."""
    return {"type": "image_png", "data": base64.standard_b64encode(Path(path).read_bytes()).decode()}

# ---------------- anthropic ----------------
_client = None
def _anthropic_content(content):
    out = []
    for c in content:
        if c["type"] == "image_png":
            out.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": c["data"]}})
        else:
            out.append(c)
    return out

def _anthropic_parse(system, content, schema, effort):
    global _client
    import anthropic
    _client = _client or anthropic.Anthropic()
    resp = _client.messages.parse(
        model=CLAUDE_MODEL, max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort},
        messages=[{"role": "user", "content": _anthropic_content(content)}],
        output_format=schema)
    if resp.stop_reason == "refusal":
        raise RuntimeError("refusal")
    return resp.parsed_output

def _anthropic_text(system, content, effort):
    global _client
    import anthropic
    _client = _client or anthropic.Anthropic()
    resp = _client.messages.create(
        model=CLAUDE_MODEL, max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort},
        messages=[{"role": "user", "content": _anthropic_content(content)}])
    if resp.stop_reason == "refusal":
        raise RuntimeError("refusal")
    return "".join(b.text for b in resp.content if b.type == "text")

# ---------------- local (OpenAI-compatible, e.g. LM Studio) ----------------
def _local_content(content):
    out = []
    for c in content:
        if c["type"] == "image_png":
            out.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + c["data"]}})
        else:
            out.append({"type": "text", "text": c["text"]})
    return out

def _local_call(system, content, response_format=None, max_tokens=4000):
    body = {"model": LOCAL_MODEL, "temperature": 0.2, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": _local_content(content)}]}
    if response_format:
        body["response_format"] = response_format
    r = requests.post(LOCAL_URL + "/chat/completions", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _local_parse(system, content, schema):
    js = schema.model_json_schema()
    txt = _local_call(system, content, {"type": "json_schema", "json_schema": {"name": schema.__name__, "strict": True, "schema": js}})
    return schema.model_validate_json(txt)

# ---------------- public API ----------------
def parse(system: str, content: list, schema, effort: str = "medium"):
    b = backend()
    if b == "anthropic":
        return _anthropic_parse(system, content, schema, effort)
    if b == "local":
        return _local_parse(system, content, schema)
    raise RuntimeError("no LLM backend")

def text(system: str, content: list, effort: str = "medium") -> str:
    b = backend()
    if b == "anthropic":
        return _anthropic_text(system, content, effort)
    if b == "local":
        return _local_call(system, content)
    raise RuntimeError("no LLM backend")
