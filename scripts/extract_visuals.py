from __future__ import annotations

import argparse
from pathlib import Path

from common import load_project, read_json, write_json


def trim(image, margin: int = 24):
    gray = image.convert("L")
    mask = gray.point(lambda value: 255 if value < 245 else 0)
    box = mask.getbbox()
    if box is None:
        return image
    return image.crop((max(0, box[0] - margin), max(0, box[1] - margin), min(image.width, box[2] + margin), min(image.height, box[3] + margin)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract configured figure/table crops and create a contact sheet.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--scale", type=float, default=4.0)
    args = parser.parse_args()
    project_dir = args.project.resolve()
    config = load_project(project_dir)
    source = Path(config["source"]["path"])
    if source.suffix.lower() != ".pdf":
        raise ValueError("Configured crop extraction currently requires PDF input")
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw

    manifest_path = project_dir / "visuals" / "visuals.json"
    payload = read_json(manifest_path)
    document = pdfium.PdfDocument(source)
    output_dir = project_dir / "visuals" / "originals"
    output_dir.mkdir(parents=True, exist_ok=True)
    previews = []
    for visual in payload.get("visuals", []):
        assets = []
        for index, part in enumerate(visual.get("parts", []), 1):
            page_no = int(part["page"])
            image = document[page_no - 1].render(scale=args.scale).to_pil().convert("RGB")
            crop = part.get("crop")
            if crop:
                image = image.crop(tuple(round(float(value) * args.scale) for value in crop))
            rotation = int(part.get("rotation", 0))
            if rotation:
                image = image.rotate(rotation, expand=True, fillcolor="white")
            image = trim(image)
            suffix = f"-{index:02d}" if len(visual.get("parts", [])) > 1 else ""
            path = output_dir / f"{visual['id']}{suffix}.png"
            image.save(path, optimize=True)
            assets.append(str(path.relative_to(project_dir)))
            preview = image.copy()
            preview.thumbnail((600, 420))
            previews.append((visual["id"] + suffix, preview))
        visual["original_assets"] = assets
        if visual.get("status") not in {"LOCALIZED", "BLOCKED"}:
            visual["status"] = "EXTRACTED"
    write_json(manifest_path, payload)

    if previews:
        cell_w, cell_h = 640, 470
        columns = 3
        rows = (len(previews) + columns - 1) // columns
        sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), "#e5e5e5")
        draw = ImageDraw.Draw(sheet)
        for index, (label, preview) in enumerate(previews):
            x = (index % columns) * cell_w
            y = (index // columns) * cell_h
            draw.text((x + 12, y + 10), label, fill="#8b0000")
            sheet.paste(preview, (x + (cell_w - preview.width) // 2, y + 38))
        contact = project_dir / "visuals" / "contact-sheet.png"
        sheet.save(contact, optimize=True)
        print(contact)
    print(f"visuals={len(payload.get('visuals', []))}")


if __name__ == "__main__":
    main()
