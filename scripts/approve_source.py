from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from common import read_json, read_jsonl, sha256_file, write_json


def next_revision(approved_dir: Path) -> str:
    revisions = []
    for path in approved_dir.glob("r[0-9][0-9][0-9]"):
        try:
            revisions.append(int(path.name[1:]))
        except ValueError:
            continue
    return f"r{(max(revisions, default=0) + 1):03d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze current semantic blocks as an immutable approved source revision.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--revision", help="Explicit unused revision such as r002")
    args = parser.parse_args()

    project = args.project.resolve()
    blocks_path = project / "source" / "blocks.jsonl"
    manifest_path = project / "source" / "source-manifest.json"
    if not blocks_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("Source manifest and source/blocks.jsonl are required")
    blocks = read_jsonl(blocks_path)
    if not blocks:
        raise ValueError("Cannot approve an empty blocks file")
    unresolved = [item.get("block_id") for item in blocks if item.get("boundary_status") != "READY"]
    if unresolved:
        raise ValueError(f"Cannot approve with unresolved blocks: {len(unresolved)}")
    ids = [item.get("block_id") for item in blocks]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("Every approved block needs a unique non-empty block_id")

    approved_dir = project / "source" / "approved"
    revision = args.revision or next_revision(approved_dir)
    if not revision.startswith("r") or not revision[1:].isdigit():
        raise ValueError("Revision must look like r001")
    target = approved_dir / revision
    if target.exists():
        raise FileExistsError(f"Approved revision already exists: {target}")
    target.mkdir(parents=True)
    shutil.copy2(blocks_path, target / "blocks.jsonl")
    manifest = read_json(manifest_path)
    approval = {
        "source_revision": revision,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "blocks_sha256": sha256_file(target / "blocks.jsonl"),
        "block_count": len(blocks),
        "source_manifest_sha256": sha256_file(manifest_path),
        "source_sha256": manifest.get("source_sha256"),
    }
    write_json(target / "approval.json", approval)
    write_json(approved_dir / "current.json", {
        "source_revision": revision,
        "approval": f"source/approved/{revision}/approval.json",
        "blocks": f"source/approved/{revision}/blocks.jsonl",
    })
    print(target / "approval.json")


if __name__ == "__main__":
    main()
