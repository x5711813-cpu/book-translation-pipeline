from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


IGNORE_MARKER = "<!-- book-proofread-disable-line -->"
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")
URL_RE = re.compile(r"https?://\S+")
LINK_TARGET_RE = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")
NOTE_REF = re.compile(r"\[\^([^\]]+)\](?!:)")
NOTE_DEF = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
TERMINAL = re.compile(r"[。！？!?…：:][”’\"'）】》〉」』]*?(?:\[\^[^\]]+\])*$")
LEADING_BAD = re.compile(r"^[\s　]*[，；：、。！？,.!?;:]{1,}")
RAW_OR_GARBLE = re.compile(r"<\/?(?:sup|sub|think|html|body)\b|�|[\u200b-\u200f\u2060\ufeff]", re.I)
NOTE_BEFORE_TERMINAL = re.compile(r"\[\^[^\]]+\][。！？!?]")
PUNCT_ADJACENCY = re.compile(r"(?:[，；：、][。！？]|[。！？][，；：、]|[，；：、。！？]{2,})")
ASCII_WORD = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'-]{2,}(?![A-Za-z])")
NUMBER_TOKEN = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?(?![A-Za-z0-9])")
NUMBER_UNITS = re.compile(r"^(?:年|月|日|世纪|卷|期|页|章|节|号|封|人|位|名|次|个|所|条|英镑|先令|便士|公里|英里|%|％)")
REPEATED_PHRASE = re.compile(r"([\u3400-\u9fff]{4,16})[，、；：\s]*\1")
ASCII_PUNCT_IN_CHINESE = re.compile(r"(?<=[\u3400-\u9fff])[,;:!?](?=[\u3400-\u9fff])")

ERROR_CATEGORIES = {
    "duplicate_note_definition",
    "missing_note_definition",
    "unreferenced_note_body",
    "raw_markup_or_garble",
    "note_before_terminal_punctuation",
}
STYLE_CATEGORIES = {"mixed_ascii_punctuation_candidate"}


def severity_for(category: str) -> str:
    if category in ERROR_CATEGORIES:
        return "error"
    if category in STYLE_CATEGORIES:
        return "style"
    return "warning"


def add(findings: list[dict], category: str, line: int, text: str, evidence: str = "") -> None:
    findings.append({
        "severity": severity_for(category),
        "category": category,
        "line": line,
        "evidence": evidence,
        "text": text[:500],
        "status": "PENDING",
    })


def mask_match(text: str, regex: re.Pattern[str]) -> str:
    return regex.sub(lambda match: " " * (match.end() - match.start()), text)


def prepare_visible_line(line: str) -> str:
    visible = mask_match(line, INLINE_CODE_RE)
    visible = LINK_TARGET_RE.sub(
        lambda match: f"{match.group(1)}{' ' * len(match.group(2))}{match.group(3)}",
        visible,
    )
    return mask_match(visible, URL_RE)


def visible_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    fence: str | None = None
    for number, raw in enumerate(lines, 1):
        if in_frontmatter:
            result.append("")
            if number != 1 and raw.strip() in {"---", "..."}:
                in_frontmatter = False
            continue
        match = FENCE_RE.match(raw)
        if match:
            delimiter = match.group(1)
            if fence is None:
                fence = delimiter
            elif delimiter[0] == fence[0] and len(delimiter) >= len(fence):
                fence = None
            result.append("")
            continue
        if fence is not None or IGNORE_MARKER in raw:
            result.append("")
            continue
        result.append(prepare_visible_line(raw))
    return result


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return text.strip()


def paragraph_records(lines: list[str]) -> list[tuple[int, str, str]]:
    records: list[tuple[int, str, str]] = []
    start = 0
    buffer: list[str] = []
    kind = "body"

    def flush() -> None:
        nonlocal start, buffer, kind
        if buffer:
            records.append((start, " ".join(item.strip() for item in buffer), kind))
        start, buffer, kind = 0, [], "body"

    in_index = False
    for number, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if heading in {"索引", "index", "general index"} or heading.endswith("索引"):
                in_index = True
            elif in_index and stripped.startswith("# "):
                in_index = False
        if in_index:
            flush()
            continue
        if re.match(r"^(?:作者|author)\s*[:：]", stripped, re.I) or re.match(r"^\*图\s*[:：].*\*$", stripped):
            flush()
            continue
        if stripped.startswith(("#", "|", "![", "```", "---")):
            flush()
            continue
        match = NOTE_DEF.match(stripped)
        current_kind = "note" if match else ("blockquote" if stripped.startswith(">") else "body")
        if buffer and current_kind != kind:
            flush()
        if not buffer:
            start, kind = number, current_kind
        buffer.append(stripped[1:].lstrip() if current_kind == "blockquote" else stripped)
    flush()
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate contextual proofreading candidates from a Chinese Markdown manuscript.")
    parser.add_argument("manuscript", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--english-allow", action="append", default=[], help="Allowed ASCII word; repeat as needed")
    parser.add_argument("--strict", action="store_true", help="Fail on warning/style candidates as well as errors")
    args = parser.parse_args()

    path = args.manuscript.resolve()
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = visible_lines(raw_lines)
    findings: list[dict] = []
    definitions: list[tuple[str, int]] = []
    references: list[tuple[str, int]] = []
    allowed = {word.lower() for word in args.english_allow}

    for number, raw in enumerate(lines, 1):
        for note_id in NOTE_REF.findall(raw):
            references.append((note_id, number))
        definition = NOTE_DEF.match(raw)
        if definition:
            definitions.append((definition.group(1), number))

    definition_counts = Counter(note_id for note_id, _ in definitions)
    reference_counts = Counter(note_id for note_id, _ in references)
    for note_id, count in sorted(definition_counts.items()):
        if count > 1:
            add(findings, "duplicate_note_definition", next(line for item, line in definitions if item == note_id), note_id, str(count))
    for note_id, line in references:
        if note_id not in definition_counts:
            add(findings, "missing_note_definition", line, note_id)
    for note_id, line in definitions:
        if note_id not in reference_counts:
            add(findings, "unreferenced_note_body", line, note_id)

    for line_no, paragraph, kind in paragraph_records(lines):
        plain = strip_markdown(paragraph)
        if not plain:
            continue
        if LEADING_BAD.search(plain):
            add(findings, "abnormal_leading_punctuation", line_no, paragraph)
        if kind != "note" and not TERMINAL.search(plain):
            add(findings, "missing_terminal_punctuation", line_no, paragraph)
        for match in RAW_OR_GARBLE.finditer(paragraph):
            add(findings, "raw_markup_or_garble", line_no, paragraph, match.group(0))
        for match in NOTE_BEFORE_TERMINAL.finditer(paragraph):
            add(findings, "note_before_terminal_punctuation", line_no, paragraph, match.group(0))
        for match in PUNCT_ADJACENCY.finditer(plain):
            add(findings, "punctuation_adjacency", line_no, paragraph, match.group(0))
        for match in ASCII_PUNCT_IN_CHINESE.finditer(plain):
            add(findings, "mixed_ascii_punctuation_candidate", line_no, paragraph, match.group(0))
        if "；" in plain:
            add(findings, "semicolon_context_review", line_no, paragraph, str(plain.count("；")))
        for match in REPEATED_PHRASE.finditer(plain):
            add(findings, "repeated_phrase_candidate", line_no, paragraph, match.group(0))
        masked = re.sub(r"https?://\S+|\[\^[^\]]+\]|\([^)]*[A-Za-z][^)]*\)", "", paragraph)
        if kind != "note":
            compact = re.sub(r"\s", "", masked)
            ascii_ratio = sum(character.isascii() and character.isalpha() for character in compact) / max(1, len(compact))
            if len(compact) > 40 and ascii_ratio > 0.60:
                add(findings, "source_language_paragraph_candidate", line_no, paragraph, f"ratio={ascii_ratio:.2f}")
            for match in ASCII_WORD.finditer(masked):
                word = match.group(0)
                if word.lower() in allowed:
                    continue
                left = masked[:match.start()].rstrip()
                right = masked[match.end():].lstrip()
                adjacent = (left and re.match(r"[\u3400-\u9fff]$", left)) or (right and re.match(r"^[\u3400-\u9fff]", right))
                embedded = left and right and re.match(r"[\u3400-\u9fff]$", left) and re.match(r"^[\u3400-\u9fff]", right)
                if embedded or (adjacent and word.islower()):
                    add(findings, "source_language_candidate", line_no, paragraph, word)
            for match in NUMBER_TOKEN.finditer(plain):
                token = match.group(0)
                before = plain[:match.start()]
                after = plain[match.end():]
                if NUMBER_UNITS.match(after) or re.match(r"^(?:[—–-]|至|到)\d", after) or re.search(r"(?:第|至|到)$", before):
                    continue
                left_chinese = bool(before and re.search(r"[\u3400-\u9fff]$", before))
                right_chinese = bool(after and re.match(r"^[\u3400-\u9fff]", after))
                if left_chinese or right_chinese:
                    add(findings, "number_context_review", line_no, paragraph, token)

    quote_state = {"double": 0, "single": 0}
    last_line = {"double": 0, "single": 0}
    for line_no, paragraph, kind in paragraph_records(lines):
        if kind == "note":
            continue
        plain = strip_markdown(paragraph)
        for label, opening, closing in (("double", "“", "”"), ("single", "‘", "’")):
            opens, closes = plain.count(opening), plain.count(closing)
            if closes > quote_state[label] + opens:
                add(findings, "stray_closing_quote_candidate", line_no, paragraph, label)
                quote_state[label] = 0
            else:
                quote_state[label] += opens - closes
            if opens:
                last_line[label] = line_no
    for label, balance in quote_state.items():
        if balance:
            add(findings, "unclosed_quote_candidate", last_line[label], label, str(balance))

    counts = Counter(item["category"] for item in findings)
    severity_counts = Counter(item["severity"] for item in findings)
    failed = bool(severity_counts["error"] or (args.strict and findings))
    status = "FAIL" if failed else ("PASS_WITH_CANDIDATES" if findings else "CLEAR")
    report = {
        "manuscript": str(path),
        "status": status,
        "strict": args.strict,
        "paragraphs_checked": len(paragraph_records(lines)),
        "note_references": len(references),
        "note_definitions": len(definitions),
        "finding_counts": dict(sorted(counts.items())),
        "severity_counts": {key: severity_counts.get(key, 0) for key in ("error", "warning", "style")},
        "findings": findings,
        "policy": "Errors are high-confidence structural failures. Warnings and style findings require contextual/source adjudication; do not auto-rewrite from this report.",
    }
    output = args.output or path.with_name(path.stem + "-proofreading-candidates.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "paragraphs_checked", "note_references", "note_definitions", "severity_counts", "finding_counts")}, ensure_ascii=False))
    print(output)
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
