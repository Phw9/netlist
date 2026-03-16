"""Vision LLM analyzer: extract circuit components and connections from images."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from netlist_converter.core.document_loader import LoadedDocument, LoadedPage, image_to_bytes
from netlist_converter.llm.provider import LLMProvider
from netlist_converter.models import Netlist, NetlistMetadata

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("data/debug")

# ──────────────────────────────────────────────────────────────────────────────
# Prompt — no concrete example values to prevent pattern-copy hallucination.
# Uses <angle-bracket> placeholders that the model must replace with real data.
# We also hint the net labels that are typical in schematics.
# ──────────────────────────────────────────────────────────────────────────────
CIRCUIT_ANALYSIS_PROMPT = """\
Analyze this electronic circuit schematic image.

Extract every visible component and every electrical connection.

Output ONLY raw JSON starting with { and ending with }. No markdown, no text outside JSON.

{
  "components": [
    {
      "reference": "<component ref from image e.g. R41, U3A, C19>",
      "component_type": "<type>",
      "value": "<value shown in image e.g. 100K, LM124, 1uF>",
      "pins": [
        {"number": "1", "pin_type": "passive"},
        {"number": "2", "pin_type": "passive"}
      ]
    }
  ],
  "nets": [
    {
      "name": "<net label from image e.g. VDD, GND, or NET001>",
      "pins": [
        {"component_ref": "<ref>", "pin": "1"},
        {"component_ref": "<ref2>", "pin": "2"}
      ]
    }
  ],
  "confidence": 0.8
}

component_type options: resistor|capacitor|inductor|diode|transistor|ic|connector|led|crystal|fuse|relay|transformer|switch|voltage_regulator|opamp|other
For op-amps use pins: 2(input-), 3(input+), 1(output), 4(V+), 11(V-)
For resistors/capacitors use pins: 1 and 2 (both passive)
Do NOT copy the placeholder text literally. Replace every <...> with actual image data.
"""

MERGE_PAGES_PROMPT = """\
Merge these partial circuit netlists into one consistent netlist.
Deduplicate components with the same reference. Merge net connections.

{partial_results}

Output ONLY raw JSON with keys: components, nets, confidence.
"""

_EMPTY_RESULT: dict = {"components": [], "nets": [], "confidence": 0.0}


def _clean_json_keys(text: str) -> str:
    """Fix malformed JSON keys that have a leading space: ' key' -> 'key'.

    Some Ollama models insert a space after the opening double-quote of a key,
    producing ' "key"' which is valid JSON for the string value ' key' but not
    a valid key name.  This regex corrects the most common pattern.
    """
    # Replace ": "<space>+ followed by word chars" with ": "word"
    cleaned = re.sub(r'"(\s+)(\w)', lambda m: f'"{m.group(2)}', text)
    return cleaned


def _repair_truncated_json(text: str) -> str:
    """Attempt to close any unclosed JSON structures at the end of text."""
    open_brace = text.count("{") - text.count("}")
    open_bracket = text.count("[") - text.count("]")

    if open_brace <= 0 and open_bracket <= 0:
        return text

    # Trim trailing incomplete token (partial string or key)
    # Find the last complete value-ending character
    last_good = max(
        text.rfind("}"),
        text.rfind("]"),
        text.rfind('"'),
    )
    if last_good > len(text) // 2:
        text = text[: last_good + 1]

    # Recount and close
    open_brace = text.count("{") - text.count("}")
    open_bracket = text.count("[") - text.count("]")

    # Remove trailing commas before closing (common in truncated JSON)
    text = re.sub(r",\s*$", "", text.rstrip())

    text += "]" * max(0, open_bracket)
    text += "}" * max(0, open_brace)
    return text


def _parse_llm_json(raw_text: str) -> dict:
    """Extract and repair JSON from LLM response.

    Handles:
    - Markdown code fences (```json ... ```)
    - Leading prose before the JSON object
    - Trailing prose after the JSON object
    - Truncated JSON (closes open brackets/braces)
    - Extra leading spaces in JSON key names
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        inner = []
        for line in lines[1:]:
            if line.strip() == "```":
                break
            inner.append(line)
        text = "\n".join(inner).strip()

    # Find the outermost JSON object
    start = text.find("{")
    if start == -1:
        logger.warning("No JSON object found in LLM response (len=%d)", len(raw_text))
        return dict(_EMPTY_RESULT)

    # Take from first { to last } (handles trailing prose)
    end = text.rfind("}") + 1
    if end <= start:
        text = text[start:]
    else:
        text = text[start:end]

    # Clean malformed keys
    text = _clean_json_keys(text)

    # Try parsing as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt repair of truncated JSON
    repaired = _repair_truncated_json(text)
    try:
        result = json.loads(repaired)
        logger.info("JSON repaired (original %d chars -> repaired %d chars)", len(text), len(repaired))
        return result
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed after repair: %s. Snippet:\n%s", exc, text[:400])
        return dict(_EMPTY_RESULT)


def _save_debug_artifacts(
    page_num: int, raw_text: str, parsed: dict, stem: str
) -> None:
    """Write raw LLM text and parsed JSON to data/debug/ for inspection."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = DEBUG_DIR / f"{stem}_page{page_num}_raw.txt"
    parsed_path = DEBUG_DIR / f"{stem}_page{page_num}_parsed.json"
    raw_path.write_bytes(raw_text.encode("utf-8", errors="replace"))
    parsed_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Debug artifacts: %s, %s", raw_path, parsed_path)


def _analyze_single_page(
    page: LoadedPage,
    llm: LLMProvider,
    debug: bool = False,
    source_stem: str = "page",
) -> dict:
    """Run vision analysis on one page image."""
    img_bytes = image_to_bytes(page.image, fmt="JPEG")
    w, h = page.image.size
    logger.info(
        "Page %d: image %dx%d -> %d bytes -> vision model",
        page.page_number, w, h, len(img_bytes),
    )

    response = llm.analyze_image_bytes(img_bytes, CIRCUIT_ANALYSIS_PROMPT)
    logger.info(
        "Page %d: model '%s' returned %d chars",
        page.page_number, response.model_name, len(response.raw_text),
    )

    if debug:
        logger.info(
            "=== RAW LLM RESPONSE (page %d) ===\n%s\n=== END ===",
            page.page_number, response.raw_text,
        )

    parsed = _parse_llm_json(response.raw_text)

    if debug:
        _save_debug_artifacts(page.page_number, response.raw_text, parsed, source_stem)

    n_comps = len(parsed.get("components", []))
    n_nets = len(parsed.get("nets", []))
    conf = float(parsed.get("confidence", 0.0))
    logger.info(
        "Page %d: extracted %d components, %d nets, confidence=%.2f",
        page.page_number, n_comps, n_nets, conf,
    )
    return parsed


def _merge_partial_results(partials: list[dict], llm: LLMProvider) -> dict:
    """Merge results from multiple pages into one netlist."""
    combined = json.dumps(partials, indent=2)
    merged_text = llm.generate_text(MERGE_PAGES_PROMPT.format(partial_results=combined))
    return _parse_llm_json(merged_text)


def analyze_document(document: LoadedDocument, llm: LLMProvider, debug: bool = False) -> Netlist:
    """Analyze all pages of a loaded document and produce a unified Netlist."""
    source_stem = document.source_path.stem
    partial_results: list[dict] = []
    for page in document.pages:
        result = _analyze_single_page(page, llm, debug=debug, source_stem=source_stem)
        partial_results.append(result)

    merged = partial_results[0] if len(partial_results) == 1 else _merge_partial_results(partial_results, llm)

    confidence = float(merged.get("confidence", 0.0))
    model_name = getattr(llm, "_model_name", "")
    metadata = NetlistMetadata(
        source_file=document.source_path.name,
        llm_model=model_name,
        confidence=confidence,
    )

    netlist = Netlist.model_validate({
        "metadata": metadata.model_dump(),
        "components": merged.get("components", []),
        "nets": merged.get("nets", []),
    })

    return netlist


def analyze_file(file_path: Path, llm: LLMProvider) -> Netlist:
    """Convenience wrapper: load a file and analyze it in one call."""
    from netlist_converter.core.document_loader import load_document
    document = load_document(file_path)
    return analyze_document(document, llm)
