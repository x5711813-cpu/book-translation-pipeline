from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

from common import load_project, read_json, sha256_text, write_json, write_jsonl


TERMINAL = re.compile(r"[.!?。！？][\"'’”\)\]]*$")
LOWER_START = re.compile(r"^[\"'‘“\(\[]*[a-z]")
PAGE_LABEL_ONLY = re.compile(r"^[\[〔(]?\s*(?:\d+|[ivxlcdm]+)\s*[\]〕)]?$", re.I)
PAGE_LABEL_INLINE = re.compile(r"[\[〔]\s*(?:\d+|[ivxlcdm]+)\s*[\]〕]", re.I)


def normalize(text: str) -> str:
    for old, new in {"\u00ad": "", "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\u00a0": " "}.items():
        text = text.replace(old, new)
    text = re.sub(r"(?<=\w)-\s*\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def paragraphs(text: str) -> list[str]:
    # Layout-mode PDF extraction usually preserves paragraph first-line indents
    # even where it does not emit a blank line. Keep that signal until grouping.
    raw_lines = normalize(text).splitlines()
    groups: list[list[str]] = []
    current: list[str] = []
    previous_indent = 0
    for raw in raw_lines:
        if not raw.strip():
            if current:
                groups.append(current)
                current = []
            previous_indent = 0
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        paragraph_indent = 3 <= indent <= 8
        if current and paragraph_indent and previous_indent < 3:
            groups.append(current)
            current = []
        current.append(raw.strip())
        previous_indent = indent
    if current:
        groups.append(current)
    result = []
    for group in groups:
        joined = " ".join(group)
        joined = re.sub(r"(?<=\w)-\s+(?=[a-z])", "", joined)
        joined = re.sub(r"\s+", " ", joined).strip()
        if joined:
            result.append(joined)
    return result


def edge_lines(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (lines[0], lines[-1]) if lines else ("", "")


def edge_key(line: str) -> str:
    line = re.sub(r"[\[〔(]\s*(?:\d+|[ivxlcdm]+)\s*[\]〕)]", "", line, flags=re.I)
    return re.sub(r"[^a-z\u3400-\u9fff]+", "", line.lower())


def boundary_decision(left: str, right: str) -> tuple[str, str]:
    if TERMINAL.search(left):
        return "SPLIT", "left ends with terminal punctuation"
    if LOWER_START.search(right):
        return "JOIN", "right begins with lowercase continuation"
    if left.endswith(("-", "–", "—", ",", ";", ":")):
        return "JOIN", "left ends with continuation punctuation"
    if len(left) < 90 and not re.search(r"[,:;]", left):
        return "SPLIT", "left resembles a heading or short standalone line"
    return "REVIEW", "ambiguous page boundary"


def section_for_page(config: dict, page: int) -> tuple[str, str]:
    for section in config.get("sections", []):
        start = section.get("start_page")
        end = section.get("end_page")
        if start is not None and end is not None and int(start) <= page <= int(end):
            return section.get("slug", "unassigned"), section.get("kind", "prose")
    return "unassigned", "prose"


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct page text into provenance-aware semantic blocks.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--accept-ambiguous-splits", action="store_true")
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    manifest = read_json(project_dir / "source" / "source-manifest.json")
    if not manifest["detected_format"].startswith("pdf"):
        raise ValueError("This extractor handles PDF pages; EPUB uses the XHTML adapter")

    page_texts: dict[int, str] = {}
    firsts: list[str] = []
    lasts: list[str] = []
    weak = set(manifest.get("weak_pages", []))
    for page_no in range(1, manifest["page_count"] + 1):
        ocr = project_dir / "source" / "pages" / f"page-{page_no:04d}.ocr.txt"
        text_layer = project_dir / "source" / "pages" / f"page-{page_no:04d}.text.txt"
        chosen = ocr if page_no in weak and ocr.exists() else text_layer
        text = chosen.read_text(encoding="utf-8") if chosen.exists() else ""
        page_texts[page_no] = text
        first, last = edge_lines(text)
        firsts.append(first)
        lasts.append(last)

    # Running heads usually repeat within a chapter, not across the whole book.
    minimum = 3
    header_counts = collections.Counter(edge_key(line) for line in firsts if edge_key(line))
    footer_counts = collections.Counter(edge_key(line) for line in lasts if edge_key(line))
    header_candidates = {key for key, count in header_counts.items() if count >= minimum}
    footer_candidates = {key for key, count in footer_counts.items() if count >= minimum}

    per_page: dict[int, list[str]] = {}
    for page_no, text in page_texts.items():
        lines = text.splitlines()
        if lines and (edge_key(lines[0].strip()) in header_candidates or PAGE_LABEL_ONLY.fullmatch(lines[0].strip()) or (len(lines[0]) < 140 and PAGE_LABEL_INLINE.search(lines[0]))):
            lines = lines[1:]
        if lines and (edge_key(lines[-1].strip()) in footer_candidates or PAGE_LABEL_ONLY.fullmatch(lines[-1].strip()) or (len(lines[-1]) < 140 and PAGE_LABEL_INLINE.search(lines[-1]))):
            lines = lines[:-1]
        per_page[page_no] = paragraphs("\n".join(lines))

    blocks: list[dict] = []
    decision_path = project_dir / "repairs" / "boundary-decisions.json"
    previous_payload = read_json(decision_path) if decision_path.exists() else {"decisions": {}}
    previous_decisions = previous_payload.get("decisions", {})
    decisions: dict[str, dict] = {}
    current: dict | None = None
    for page_no in range(1, manifest["page_count"] + 1):
        parts = per_page[page_no]
        if not parts:
            continue
        if current is not None:
            key = f"page-{page_no - 1:04d}-to-{page_no:04d}"
            saved = previous_decisions.get(key, {})
            if saved.get("decision") in {"JOIN", "SPLIT"}:
                decision, reason = saved["decision"], saved.get("reason", "saved decision")
            else:
                decision, reason = boundary_decision(current["source"], parts[0])
            if decision == "REVIEW" and args.accept_ambiguous_splits:
                decision, reason = "SPLIT", "ambiguous boundary accepted as split by operator"
            decisions[key] = {
                **saved,
                "decision": decision, "reason": reason, "left_page": page_no - 1, "right_page": page_no,
                "left_tail": current["source"][-700:], "right_head": parts[0][:700],
            }
            if decision == "JOIN":
                current["source"] += " " + parts.pop(0)
                current["provenance"].append({"page": page_no, "bbox": None})
            elif decision == "REVIEW":
                current["boundary_status"] = "REVIEW"
        for part in parts:
            if current is not None:
                current["source_sha256"] = sha256_text(current["source"])
                blocks.append(current)
            current = {
                "block_id": "",
                "section": "unassigned",
                "kind": "prose",
                "source": part,
                "provenance": [{"page": page_no, "bbox": None}],
                "boundary_status": "READY",
                "source_sha256": "",
            }
    if current is not None:
        current["source_sha256"] = sha256_text(current["source"])
        blocks.append(current)
    for index, block in enumerate(blocks, 1):
        page = block["provenance"][0]["page"]
        section, kind = section_for_page(config, page)
        block["section"] = section
        block["kind"] = kind
        safe_section = re.sub(r"[^a-z0-9-]+", "-", section.lower()).strip("-") or "book"
        block["block_id"] = f"{safe_section}-block-{index:06d}"

    if config.get("sections"):
        unassigned = sum(block["section"] == "unassigned" for block in blocks)
        if unassigned:
            print(f"WARN {unassigned} blocks unmatched by section page ranges; configure start_page/end_page before approval")

    write_jsonl(project_dir / "source" / "blocks.jsonl", blocks)
    write_json(project_dir / "repairs" / "boundary-decisions.json", {
        "decisions": decisions,
        "running_header_keys_removed": sorted(header_candidates),
        "running_footer_keys_removed": sorted(footer_candidates),
    })
    print(f"blocks={len(blocks)} review_boundaries={sum(v['decision'] == 'REVIEW' for v in decisions.values())}")


if __name__ == "__main__":
    main()
