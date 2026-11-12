"""Thin Anthropic client wrapper shared by the agents."""
import base64, os
from pathlib import Path
import anthropic

MODEL = os.environ.get("DRISHTI_MODEL", "claude-opus-5-5")
_client = None

def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY / profile from env
    return _client

def png_block(path: Path) -> dict:
    data = base64.standard_b64encode(Path(path).read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}

def parse(system: str, content: list, schema, effort: str = "medium"):
    """One structured call. Returns schema instance (raises on refusal)."""
    resp = client().messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort},
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"refusal: {getattr(resp.stop_details, 'category', None)}")
    return resp.parsed_output

def text(system: str, content: list, effort: str = "medium") -> str:
    resp = client().messages.create(
        model=MODEL, max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": effort},
        messages=[{"role": "user", "content": content}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("refusal")
    return "".join(b.text for b in resp.content if b.type == "text")
