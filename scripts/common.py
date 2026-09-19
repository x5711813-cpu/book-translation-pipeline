from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, values: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values), encoding="utf-8")
    os.replace(temporary, path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_project(project_dir: Path) -> dict:
    path = project_dir / "project.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing project configuration: {path}")
    config = read_json(path)
    validate_sections(config.get("sections", []))
    return config


def validate_sections(sections: list) -> None:
    if not isinstance(sections, list):
        raise ValueError("sections must be a list")
    allowed = {"slug", "label", "kind", "start_page", "end_page", "source_section", "block_ids"}
    slugs = set()
    ranges = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("Each section must be an object")
        unknown = set(section) - allowed
        if unknown:
            raise ValueError(f"Unknown sections keys: {sorted(unknown)}; use start_page/end_page for PDF page ranges")
        slug = section.get("slug")
        if not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", slug):
            raise ValueError("Each section needs a safe, nonempty slug (letters, digits, underscore or hyphen)")
        if slug in slugs:
            raise ValueError(f"Duplicate section slug: {slug}")
        slugs.add(slug)
        if not isinstance(section.get("label"), str) or not section["label"].strip():
            raise ValueError(f"Section {slug} needs a label")
        if "start_page" in section or "end_page" in section:
            start, end = section.get("start_page"), section.get("end_page")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise ValueError(f"Section {slug}: start_page/end_page must be positive integers with start_page <= end_page")
            if any(start <= other_end and other_start <= end for other_start, other_end in ranges):
                raise ValueError(f"Overlapping PDF page range in section {slug}")
            ranges.append((start, end))
        if "block_ids" in section:
            ids = section["block_ids"]
            if not isinstance(ids, list) or any(not isinstance(key, str) or not key for key in ids) or len(ids) != len(set(ids)):
                raise ValueError(f"Section {slug}: block_ids must contain unique nonempty strings")
        if "source_section" in section and (not isinstance(section["source_section"], str) or not section["source_section"]):
            raise ValueError(f"Section {slug}: source_section must be a nonempty string")
