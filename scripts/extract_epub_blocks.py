from __future__ import annotations

import argparse
import html
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from common import load_project, read_json, sha256_text, write_jsonl


TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "figcaption", "td", "th"}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract semantic XHTML blocks from a reflowable EPUB.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    manifest = read_json(project_dir / "source" / "source-manifest.json")
    if not manifest["detected_format"].startswith("epub"):
        raise ValueError("Source is not EPUB")
    source = Path(config["source"]["path"])
    blocks = []
    with zipfile.ZipFile(source) as archive:
        for href in manifest["spine"]:
            root = ET.fromstring(archive.read(href))
            node_index = 0
            for node in root.iter():
                if local(node.tag) not in TEXT_TAGS:
                    continue
                text = re.sub(r"\s+", " ", "".join(node.itertext())).strip()
                if not text:
                    continue
                node_index += 1
                kind = "heading" if local(node.tag).startswith("h") else "table" if local(node.tag) in {"td", "th"} else "prose"
                block_id = f"epub-block-{len(blocks) + 1:06d}"
                blocks.append({
                    "block_id": block_id,
                    "section": href,
                    "kind": kind,
                    "source": text,
                    "provenance": [{"href": href, "node": f"{local(node.tag)}[{node_index}]"}],
                    "boundary_status": "READY",
                    "source_sha256": sha256_text(text),
                })
    write_jsonl(project_dir / "source" / "blocks.jsonl", blocks)
    print(f"blocks={len(blocks)}")


if __name__ == "__main__":
    main()
