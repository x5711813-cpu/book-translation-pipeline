from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import html
import mimetypes
import posixpath
import re
import uuid
import zipfile
from pathlib import Path

from common import load_project, read_json, read_jsonl, sha256_file, write_json
from translate_blocks import load_approved_blocks, stale_translation_ids


def xhtml(title: str, body: str, lang: str) -> str:
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}"><head><title>{html.escape(title)}</title><link rel="stylesheet" href="../styles/stylesheet.css" type="text/css"/></head><body>{body}</body></html>'''


NOTE_REF = re.compile(r"\[\^([^\]]+)\]")


def inline_text(value: str) -> str:
    parts = []
    cursor = 0
    for match in NOTE_REF.finditer(value):
        parts.append(html.escape(value[cursor:match.start()]))
        note_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", match.group(1))
        parts.append(f'<sup><a id="ref-{note_id}" href="#note-{note_id}" epub:type="noteref">{html.escape(match.group(1))}</a></sup>')
        cursor = match.end()
    parts.append(html.escape(value[cursor:]))
    return "".join(parts).replace("\n", "<br/>")


def block_html(block: dict, translation: str) -> str:
    text = inline_text(translation)
    if block.get("kind") == "heading":
        return f'<h2 id="{block["block_id"]}">{text}</h2>'
    css = ' class="index-entry"' if block.get("kind") == "index" else ""
    return f'<p id="{block["block_id"]}"{css}>{text}</p>'


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a simple EPUB 3 from approved semantic blocks.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--allow-review", action="store_true")
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    blocks, source_revision = load_approved_blocks(project_dir, config)
    if not blocks or any(block.get("boundary_status") != "READY" for block in blocks):
        raise ValueError("Source must contain only resolved READY blocks before building")
    translations = {item["block_id"]: item for item in read_jsonl(project_dir / "translations" / "translations.jsonl")}
    missing = [block["block_id"] for block in blocks if block.get("boundary_status") == "READY" and block["block_id"] not in translations]
    current_ids = {block["block_id"] for block in blocks}
    orphan_ids = sorted(set(translations) - current_ids)
    if orphan_ids:
        print(f"WARN Historical translation rows outside current source: {len(orphan_ids)} (retained)")
    review = [key for key, item in translations.items() if key in current_ids and item.get("status") != "PASS"]
    if missing:
        raise RuntimeError(f"Missing translations: {missing[:20]}")
    stale = stale_translation_ids(project_dir, config, blocks, source_revision, translations)
    if stale:
        raise RuntimeError(f"Stale translations; translate the approved source again: {stale[:20]}")
    if review and not args.allow_review:
        raise RuntimeError(f"Translations still need review: {review[:20]}")

    configured = config.get("sections") or [{"slug": "book", "label": config["target"].get("title") or "译文", "block_ids": [b["block_id"] for b in blocks]}]
    chapter_blocks = []
    for section in configured:
        ids = section.get("block_ids")
        if ids is None:
            ids = [b["block_id"] for b in blocks if b.get("section") == section.get("source_section", section["slug"])]
        selected_ids = set(ids)
        unknown = selected_ids - current_ids
        if unknown:
            raise ValueError(f"Unknown block IDs in section {section['slug']}: {sorted(unknown)}")
        selected = [b for b in blocks if b["block_id"] in selected_ids]
        if not selected:
            raise ValueError(f"Empty section: {section['slug']}; check page ranges, source_section or block_ids")
        chapter_blocks.append(selected)
    counts = Counter(b["block_id"] for selected in chapter_blocks for b in selected)
    omitted = sorted(current_ids - set(counts))
    duplicated = sorted(key for key, count in counts.items() if count > 1)
    if omitted or duplicated:
        raise ValueError(f"Invalid chapter coverage: omitted={omitted}, duplicated={duplicated}")
    chapter_files = []
    block_chapter: dict[str, str] = {}
    files: dict[str, str | bytes] = {}
    visual_data = read_json(project_dir / "visuals" / "visuals.json").get("visuals", [])
    visuals_after = {}
    for visual in visual_data:
        visuals_after.setdefault(visual.get("placement_after_block"), []).append(visual)
    for section, selected in zip(configured, chapter_blocks):
        for block in selected:
            block_chapter[block["block_id"]] = section["slug"]
        body = [f'<h1>{html.escape(section["label"])}</h1>']
        note_markup = []
        for block in selected:
            record = translations.get(block["block_id"])
            if record and block.get("kind") == "note":
                note_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(block.get("note_id", block["block_id"])))
                note_markup.append(f'<li id="note-{note_id}">{inline_text(record["translation"])} <a href="#ref-{note_id}">↩</a></li>')
            elif record:
                body.append(block_html(block, record["translation"]))
            for visual in visuals_after.get(block["block_id"], []):
                images = visual.get("localized_assets", [])
                image_markup = "".join(f'<img src="../images/{html.escape(Path(name).name)}" alt="{html.escape(visual.get("alt", visual.get("caption_target", "")))}"/>' for name in images)
                body.append(f'<figure id="{html.escape(visual["id"])}">{image_markup}<figcaption>{html.escape(visual.get("caption_target", ""))}</figcaption></figure>')
        if note_markup:
            body.append('<section class="notes" epub:type="endnotes"><h2>注释</h2><ol>' + "".join(note_markup) + '</ol></section>')
        name = f'EPUB/text/{section["slug"]}.xhtml'
        files[name] = xhtml(section["label"], "\n".join(body), config["target"]["language"])
        chapter_files.append((section["slug"], section["label"]))

    nav_items = "".join(f'<li><a href="text/{slug}.xhtml">{html.escape(label)}</a></li>' for slug, label in chapter_files)
    default_slug = next((slug for slug, _ in chapter_files), "book")
    visual_items = "".join(
        f'<li><a href="text/{block_chapter.get(v.get("placement_after_block"), default_slug)}.xhtml#{html.escape(v["id"])}">{html.escape(v.get("caption_target", v["id"]))}</a></li>'
        for v in visual_data
    )
    files["EPUB/nav.xhtml"] = f'''<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目录</title></head><body><nav epub:type="toc"><h1>目录</h1><ol>{nav_items}</ol></nav><nav><h2>图表索引</h2><ol>{visual_items}</ol></nav></body></html>'''
    stylesheet = project_dir / "output" / "stylesheet.css"
    files["EPUB/styles/stylesheet.css"] = stylesheet.read_text(encoding="utf-8")
    for visual in visual_data:
        for asset in visual.get("localized_assets", []):
            path = Path(asset)
            if not path.is_absolute():
                path = project_dir / path
            files[f"EPUB/images/{path.name}"] = path.read_bytes()
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>', '<item id="css" href="styles/stylesheet.css" media-type="text/css"/>']
    spine = []
    for slug, _ in chapter_files:
        manifest.append(f'<item id="{slug}" href="text/{slug}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{slug}"/>')
    for index, name in enumerate(key for key in files if key.startswith("EPUB/images/")):
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        manifest.append(f'<item id="img-{index}" href="images/{Path(name).name}" media-type="{mime}"/>')
    book_id = str(uuid.uuid5(uuid.NAMESPACE_URL, config["target"].get("title", "translated-book")))
    modified = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files["EPUB/package.opf"] = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier><dc:title>{html.escape(config["target"].get("title", ""))}</dc:title><dc:creator>{html.escape(config["target"].get("author", ""))}</dc:creator><dc:language>{config["target"]["language"]}</dc:language><meta property="dcterms:modified">{modified}</meta></metadata><manifest>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>'''
    files["META-INF/container.xml"] = '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    output = project_dir / config["target"]["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, value in files.items():
            archive.writestr(name, value.encode("utf-8") if isinstance(value, str) else value, compress_type=zipfile.ZIP_DEFLATED)
    write_json(output.with_suffix(".build.json"), {"status": "REVIEW" if review else "BUILT", "source_revision": source_revision, "epub": str(output), "sha256": sha256_file(output), "chapters": len(chapter_files), "visuals": len(visual_data), "orphan_translation_ids": orphan_ids})
    print(output)


if __name__ == "__main__":
    main()
