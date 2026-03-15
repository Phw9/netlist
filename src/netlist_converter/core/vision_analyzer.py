"""Vision LLM analyzer: extract circuit components and connections from images."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from netlist_converter.core.document_loader import LoadedDocument, LoadedPage, image_to_bytes
from netlist_converter.llm.provider import LLMProvider
from netlist_converter.models import Netlist, NetlistMetadata

logger = logging.getLogger(__name__)

# Compact prompt: schema-only, no verbose examples, minimal rules.
# Fewer input tokens -> faster first-token latency.
CIRCUIT_ANALYSIS_PROMPT = """\
Analyze this PCB circuit image. Extract all components and nets.
Return ONLY valid JSON (no markdown), schema:
{"components":[{"reference":"R1","component_type":"resistor","value":"10k","footprint":"","manufacturer":"","part_number":"","description":"","pins":[{"number":"1","name":"","pin_type":"passive"}]}],"nets":[{"name":"VCC","pins":[{"component_ref":"R1","pin":"1"}]}],"confidence":0.8}
component_type: resistor|capacitor|inductor|diode|transistor|ic|connector|led|crystal|fuse|relay|transformer|switch|voltage_regulator|opamp|other
pin_type: input|output|passive|power
"""

MERGE_PAGES_PROMPT = """\
Merge these partial circuit netlists into one. Deduplicate by reference.
Return ONLY valid JSON with keys: components, nets, confidence.
{partial_results}
"""

_EMPTY_RESULT: dict = {"components": [], "nets": [], "confidence": 0.0}


def _parse_llm_json(raw_text: str) -> dict:
    """Extract JSON from LLM response. Returns empty result on any parse failure."""
    text = raw_text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        end_idx = len(lines) - 1
        if lines[end_idx].strip() == "```":
            text = "\n".join(lines[1:end_idx])
        else:
            text = "\n".join(lines[1:])

    # Find the outermost JSON object in case of leading/trailing prose
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("No JSON object found in LLM response, using empty result")
        return dict(_EMPTY_RESULT)

    text = text[start:end]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON decode failed (%s), returning empty result", exc)
        return dict(_EMPTY_RESULT)

    return parsed


def _analyze_single_page(page: LoadedPage, llm: LLMProvider, debug: bool = False) -> dict:
    """Run vision analysis on one page image."""
    img_bytes = image_to_bytes(page.image, fmt="JPEG")
    logger.info("Sending page %d (%d bytes) to vision model", page.page_number, len(img_bytes))
    response = llm.analyze_image_bytes(img_bytes, CIRCUIT_ANALYSIS_PROMPT)
    logger.info(
        "Got response from %s (%d chars)",
        response.model_name, len(response.raw_text),
    )
    if debug:
        logger.info("--- RAW LLM RESPONSE ---\n%s\n--- END ---", response.raw_text)
    return _parse_llm_json(response.raw_text)


def _merge_partial_results(partials: list[dict], llm: LLMProvider) -> dict:
    """Merge results from multiple pages into one netlist."""
    combined = json.dumps(partials, separators=(",", ":"))
    merged_text = llm.generate_text(MERGE_PAGES_PROMPT.format(partial_results=combined))
    return _parse_llm_json(merged_text)


def analyze_document(document: LoadedDocument, llm: LLMProvider, debug: bool = False) -> Netlist:
    """Analyze all pages of a loaded document and produce a unified Netlist."""
    partial_results: list[dict] = []
    for page in document.pages:
        result = _analyze_single_page(page, llm, debug=debug)
        partial_results.append(result)

    if len(partial_results) == 1:
        merged = partial_results[0]
    else:
        merged = _merge_partial_results(partial_results, llm)

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
