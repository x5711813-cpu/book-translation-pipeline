from __future__ import annotations

import argparse
import datetime as dt
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from common import load_project, sha256_file, write_json


CONTAINER = "{urn:oasis:names:tc:opendocument:xmlns:container}"
OPF = "{http://www.idpf.org/2007/opf}"


def inspect_pdf(path: Path, project_dir: Path) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    weak = []
    for index, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            text = page.extract_text() or ""
        chars = len("".join(text.split()))
        replacement_chars = text.count("\ufffd")
        rotation = int(page.rotation or 0) % 360
        record = {
            "page": index, "text_chars": chars, "replacement_chars": replacement_chars,
            "rotation": rotation, "needs_ocr": chars < 80,
            "needs_layout_review": rotation in {90, 270} or replacement_chars > max(5, chars * 0.01),
        }
        pages.append(record)
        if record["needs_ocr"]:
            weak.append(index)
        out = project_dir / "source" / "pages" / f"page-{index:04d}.text.txt"
        out.write_text(text, encoding="utf-8")
    ratio = len(weak) / len(pages) if pages else 1.0
    detected = "pdf-scan" if ratio >= 0.8 else "pdf-mixed" if weak else "pdf-text"
    return {"detected_format": detected, "page_count": len(pages), "weak_pages": weak, "pages": pages}


def inspect_epub(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(f".//{CONTAINER}rootfile")
        if rootfile is None:
            raise ValueError("EPUB container has no rootfile")
        opf_name = rootfile.attrib["full-path"]
        opf = ET.fromstring(archive.read(opf_name))
        manifest = {item.attrib["id"]: item for item in opf.findall(f".//{OPF}manifest/{OPF}item")}
        spine = []
        opf_dir = posixpath.dirname(opf_name)
        for itemref in opf.findall(f".//{OPF}spine/{OPF}itemref"):
            item = manifest.get(itemref.attrib.get("idref", ""))
            if item is not None:
                spine.append(posixpath.normpath(posixpath.join(opf_dir, item.attrib["href"])))
        fixed = any("pre-paginated" in (meta.text or "") for meta in opf.findall(f".//{OPF}metadata/{OPF}meta"))
        return {
            "detected_format": "epub-fixed" if fixed else "epub-reflowable",
            "opf": opf_name,
            "spine": spine,
            "spine_count": len(spine),
            "resource_count": len(manifest),
            "encrypted": "META-INF/encryption.xml" in names,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect PDF or EPUB input and create a source manifest.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    path = Path(config["source"]["path"])
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        details = inspect_pdf(path, project_dir)
    elif suffix == ".epub":
        details = inspect_epub(path)
    else:
        raise ValueError(f"Unsupported source format: {suffix}")
    manifest = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_path": str(path.resolve()),
        "source_sha256": sha256_file(path),
        **details,
    }
    config["source"]["format"] = details["detected_format"]
    write_json(project_dir / "project.json", config)
    output = project_dir / "source" / "source-manifest.json"
    write_json(output, manifest)
    print(output)


if __name__ == "__main__":
    main()
