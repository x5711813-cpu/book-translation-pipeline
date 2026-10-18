from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.parsers.expat import ExpatError

from common import load_project, read_json, read_jsonl, sha256_file, write_json
from translate_blocks import load_approved_blocks, stale_translation_ids
from ebook_tool import Book, audit


CONTAMINATION = re.compile(r"<think>|</think>|作为AI|我无法翻译|system prompt|```", re.I)


def audit_epub(path: Path) -> list[str]:
    try:
        return audit(Book(path))["errors"]
    except (ValueError, KeyError, IndexError, ExpatError, zipfile.BadZipFile) as error:
        return [f"Invalid EPUB: {error}"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit reusable book-translation project invariants.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    errors = []
    warnings = []
    manifest_path = project_dir / "source" / "source-manifest.json"
    if not manifest_path.exists():
        errors.append("Missing source manifest")
        manifest = {}
    else:
        manifest = read_json(manifest_path)
        source = Path(config["source"]["path"])
        if source.exists() and sha256_file(source) != manifest.get("source_sha256"):
            errors.append("Source hash changed after extraction")
    try:
        blocks, source_revision = load_approved_blocks(project_dir, config)
    except (FileNotFoundError, ValueError, KeyError) as error:
        errors.append(f"Source approval invalid: {error}")
        blocks = read_jsonl(project_dir / "source" / "blocks.jsonl")
        source_revision = "invalid"
    ids = [item.get("block_id") for item in blocks]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate block IDs")
    unresolved = [item["block_id"] for item in blocks if item.get("boundary_status") != "READY"]
    if unresolved:
        errors.append(f"Unresolved source boundaries: {len(unresolved)}")
    translations = {item["block_id"]: item for item in read_jsonl(project_dir / "translations" / "translations.jsonl")}
    current_ids = set(ids)
    orphan_ids = sorted(set(translations) - current_ids)
    if orphan_ids:
        warnings.append(f"Historical translation rows outside current source: {len(orphan_ids)} (retained)")
    translations = {key: item for key, item in translations.items() if key in current_ids}
    missing = [item["block_id"] for item in blocks if item.get("boundary_status") == "READY" and item["block_id"] not in translations]
    stale = stale_translation_ids(project_dir, config, blocks, source_revision, translations)
    review = [key for key, item in translations.items() if item.get("status") != "PASS"]
    contaminated = [key for key, item in translations.items() if CONTAMINATION.search(item.get("translation", ""))]
    if missing:
        errors.append(f"Missing translations: {len(missing)}")
    if stale:
        errors.append(f"Stale translations: {len(stale)}")
    if review:
        errors.append(f"Translations needing review: {len(review)}")
    if contaminated:
        errors.append(f"Contaminated translations: {len(contaminated)}")
    visuals = read_json(project_dir / "visuals" / "visuals.json").get("visuals", [])
    incomplete_visuals = [item.get("id") for item in visuals if item.get("status") != "LOCALIZED"]
    if incomplete_visuals:
        errors.append(f"Visuals not localized: {len(incomplete_visuals)}")
    output = project_dir / config["target"]["output"]
    if output.exists():
        errors.extend(audit_epub(output))
    else:
        warnings.append("EPUB has not been built")
    report = {
        "status": "PASS" if not errors else "INCOMPLETE",
        "errors": errors,
        "warnings": warnings,
        "orphan_translation_ids": orphan_ids,
        "source_format": manifest.get("detected_format"), "source_revision": source_revision,
        "blocks": len(blocks), "translations": len(translations), "visuals": len(visuals),
        "epub": str(output) if output.exists() else None,
        "epub_sha256": sha256_file(output) if output.exists() else None,
    }
    write_json(project_dir / "reports" / "project-audit.json", report)
    print(report["status"])
    for error in errors:
        print("ERROR", error)
    for warning in warnings:
        print("WARN", warning)
    if errors and not args.allow_incomplete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
