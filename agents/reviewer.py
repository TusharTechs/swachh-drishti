"""Agent 3 - Reviewer gate (deterministic checks + LLM critic).

A pack is publishable only if:
  * every number in the pack appears in the source data (deterministic check),
  * no banned wording (allegations / certification language),
  * the LLM critic finds no unsupported claim, blame, or personal / company names.
Packs that fail stay in review/ and are never published to the web map.
"""
import json, re
from agents.llm import parse
from agents.schemas import ReviewVerdict

BANNED = re.compile(r"\b(fraud|scam|false claim|lied|corrupt|certif(y|ied|icate)|failure of|negligen)", re.I)
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")

SYSTEM = """You are the reviewer for Swachh Drishti evidence packs. Compare the pack with the source data.
Flag: any number not present in the source data; any statement of intent, blame or wrongdoing; any named
individual or company; any claim beyond what satellite data can show (e.g. tonnage, cause of fire).
passed=true only if there are no problems."""

def _numbers(s: str) -> set[str]:
    return {n.replace(",", "") for n in NUM.findall(s)}

def review(site_id: str, pack_md: str, source: dict, use_llm: bool = True) -> ReviewVerdict:
    problems = []
    if m := BANNED.search(pack_md):
        problems.append(f"banned wording: '{m.group(0)}'")
    src_nums = _numbers(json.dumps(source))
    allowed_small = {str(i) for i in range(0, 13)} | {str(y) for y in range(2015, 2031)} | {"1", "2", "5", "10", "375"}
    unknown = sorted(n for n in _numbers(pack_md) - src_nums - allowed_small
                     if not any(n in s or s.startswith(n) for s in src_nums))
    if unknown:
        problems.append("numbers not found in source data: " + ", ".join(unknown[:15]))
    if use_llm:
        v = parse(SYSTEM, [{"type": "text", "text": "SOURCE DATA:\n" + json.dumps(source) + "\n\nPACK:\n" + pack_md}],
                  ReviewVerdict)
        problems += v.problems
    return ReviewVerdict(site_id=site_id, passed=not problems, problems=problems)
