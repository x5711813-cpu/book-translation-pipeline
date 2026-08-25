from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
from pathlib import Path

from common import load_project, write_json


def rapid_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise RuntimeError("Install rapidocr_onnxruntime in the configured OCR Python environment") from error
    return RapidOCR()


def order_regions(regions: list[dict]) -> list[dict]:
    return sorted(regions, key=lambda item: (item["box"][0][1], item["box"][0][0]))


def suspicious_line_gaps(regions: list[dict]) -> list[dict]:
    body = [item for item in regions if len(item["text"]) >= 35]
    if len(body) < 5:
        return []
    gaps = [body[index + 1]["box"][0][1] - body[index]["box"][0][1] for index in range(len(body) - 1)]
    positive = [gap for gap in gaps if gap > 0]
    if not positive:
        return []
    median = statistics.median(positive)
    findings = []
    for index, gap in enumerate(gaps):
        left, right = body[index], body[index + 1]
        same_column = abs(left["box"][0][0] - right["box"][0][0]) < 120
        if same_column and median * 1.7 < gap < median * 3.5:
            findings.append({"after": left["text"][-80:], "before": right["text"][:80], "gap": round(gap, 2), "median_gap": round(median, 2)})
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR selected scanned PDF pages with local RapidOCR.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pages", default="", help="Comma/range list such as 1-20,25; defaults to weak pages")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    configured_python = config.get("ocr", {}).get("python", "")
    if configured_python and Path(configured_python).resolve() != Path(sys.executable).resolve():
        command = [configured_python, str(Path(__file__).resolve()), *sys.argv[1:]]
        raise SystemExit(subprocess.run(command).returncode)
    source = Path(config["source"]["path"])
    if source.suffix.lower() != ".pdf":
        raise ValueError("OCR input must be a PDF")

    import pypdfium2 as pdfium
    from PIL import Image

    manifest_path = project_dir / "source" / "source-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Run inspect_source.py first")
    from common import read_json
    manifest = read_json(manifest_path)
    document = pdfium.PdfDocument(source)
    if args.all:
        selected = list(range(1, len(document) + 1))
    elif args.pages:
        selected = []
        for part in args.pages.split(","):
            if "-" in part:
                start, end = map(int, part.split("-", 1))
                selected.extend(range(start, end + 1))
            else:
                selected.append(int(part))
    else:
        selected = manifest.get("weak_pages", [])

    engine = rapid_engine()
    scale = float(config["ocr"].get("render_scale", 4.0))
    threshold = float(config["ocr"].get("confidence_threshold", 0.9))
    reports = []
    for page_no in selected:
        page = document[page_no - 1]
        image = page.render(scale=scale).to_pil().convert("RGB")
        image_path = project_dir / "source" / "images" / f"page-{page_no:04d}.png"
        image.save(image_path, optimize=True)
        raw, elapsed = engine(str(image_path))
        regions = []
        for item in raw or []:
            box, text, score = item
            regions.append({"box": [[round(float(x), 2), round(float(y), 2)] for x, y in box], "text": text, "confidence": round(float(score), 5)})
        regions = order_regions(regions)
        scores = [item["confidence"] for item in regions]
        low = [index for index, item in enumerate(regions) if item["confidence"] < threshold]
        gaps = suspicious_line_gaps(regions)
        text = "\n".join(item["text"] for item in regions)
        (project_dir / "source" / "pages" / f"page-{page_no:04d}.ocr.txt").write_text(text + "\n", encoding="utf-8")
        record = {
            "page": page_no,
            "image": str(image_path),
            "regions": regions,
            "mean_confidence": round(statistics.fmean(scores), 5) if scores else 0.0,
            "low_confidence_regions": low,
            "suspicious_line_gaps": gaps,
            "status": "REVIEW" if low or gaps or not regions else "PASS",
            "engine_timing": elapsed,
        }
        write_json(project_dir / "source" / "pages" / f"page-{page_no:04d}.ocr.json", record)
        reports.append({key: record[key] for key in ("page", "mean_confidence", "low_confidence_regions", "suspicious_line_gaps", "status")})
        print(f"page {page_no}: {record['status']} confidence={record['mean_confidence']}")
    write_json(project_dir / "reports" / "ocr-report.json", {"provider": "rapidocr", "pages": reports})


if __name__ == "__main__":
    main()
