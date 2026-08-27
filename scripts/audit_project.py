from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from common import load_project, read_json, read_jsonl, sha256_file, sha256_text, write_json
from translate_blocks import (KIND_POLICIES, REVIEW, SYSTEM, configured_model,
                              context_package, load_approved_blocks, load_knowledge)


CONTAMINATION = re.compile(r"<think>|</think>|作为AI|我无法翻译|system prompt|```", re.I)


def audit_epub(path: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if not names or names[0] != "mimetype" or archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            errors.append("EPUB mimetype must be first and uncompressed")
        for name in names:
            if name.endswith((".xhtml", ".opf", ".xml")):
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError as error:
                    errors.append(f"Invalid XML {name}: {error}")
                    continue
                base = posixpath.dirname(name)
                for node in root.iter():
                    for attribute in ("href", "src"):
                        target = node.attrib.get(attribute, "").split("#", 1)[0]
                        if target and ":" not in target and not target.startswith("#"):
                            resolved = posixpath.normpath(posixpath.join(base, target))
                            if resolved not in names:
                                errors.append(f"Broken {attribute} in {name}: {target}")
    return errors


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
    missing = [item["block_id"] for item in blocks if item.get("boundary_status") == "READY" and item["block_id"] not in translations]
    knowledge, knowledge_hash = load_knowledge(project_dir, config)
    translator = configured_model(config, "translator")
    reviewer_model = configured_model(config, "reviewer")
    translator_hash = sha256_text(json.dumps(translator, sort_keys=True))
    reviewer_hash = sha256_text(json.dumps(reviewer_model, sort_keys=True))
    review_prompt_hash = sha256_text(REVIEW)
    stale = []
    for index, block in enumerate(blocks):
        record = translations.get(block["block_id"])
        if not record:
            continue
        kind = block.get("kind", "prose")
        prompt_hash = sha256_text(SYSTEM + "\nBLOCK POLICY: " + KIND_POLICIES.get(kind, KIND_POLICIES["prose"]))
        package = context_package(blocks, index, translations, source_revision, knowledge, config)
        context_hash = sha256_text(json.dumps(package, ensure_ascii=False, sort_keys=True))
        expected = {
            "source_sha256": block.get("source_sha256"),
            "source_revision": source_revision,
            "context_sha256": context_hash,
            "knowledge_sha256": knowledge_hash,
            "model_config_sha256": translator_hash,
            "reviewer_model_config_sha256": reviewer_hash,
            "prompt_sha256": prompt_hash,
            "review_prompt_sha256": review_prompt_hash,
        }
        if any(record.get(key) != value for key, value in expected.items()):
            stale.append(block["block_id"])
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
