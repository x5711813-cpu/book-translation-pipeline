from __future__ import annotations

import argparse
import os
from pathlib import Path

from common import read_json, write_json


def find_font(project_dir: Path) -> tuple[str, str]:
    candidates = [
        (Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\msyhbd.ttc")),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")),
        (Path("/System/Library/Fonts/PingFang.ttc"), Path("/System/Library/Fonts/PingFang.ttc")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            return str(regular), str(bold)
    raise FileNotFoundError("No CJK font found; add font and font_bold to the visual render spec")


def wrap(draw, text: str, font, width: int) -> list[str]:
    lines = []
    for paragraph in str(text).split("\n"):
        current = ""
        for char in paragraph:
            if current and draw.textlength(current + char, font=font) > width:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    return lines


def draw_text(draw, box, text, font, align="center", fill="#202020"):
    x0, y0, x1, _ = box
    for index, line in enumerate(wrap(draw, text, font, x1 - x0)):
        x = x0 if align == "left" else x0 + (x1 - x0 - draw.textlength(line, font=font)) / 2
        draw.text((x, y0 + index * (font.size + 7)), line, font=font, fill=fill)


def render_table(spec: dict, fonts):
    from PIL import Image, ImageDraw, ImageFont
    widths = spec.get("widths") or [260] * len(spec["headers"])
    rows = spec["rows"]
    pad, title_h, header_h, row_h = 32, 90, 190, int(spec.get("row_height", 120))
    note_h = 120 if spec.get("note") else 20
    image = Image.new("RGB", (sum(widths) + pad * 2, pad + title_h + header_h + row_h * len(rows) + note_h + pad), "white")
    draw = ImageDraw.Draw(image)
    body = ImageFont.truetype(fonts[0], 25)
    bold = ImageFont.truetype(fonts[1], 27)
    title = ImageFont.truetype(fonts[1], 36)
    draw.text((pad, pad), spec["title"], font=title, fill="#202020")
    y = pad + title_h
    for row_index, row in enumerate([spec["headers"], *rows]):
        x = pad
        height = header_h if row_index == 0 else row_h
        for column, value in enumerate(row):
            draw.rectangle((x, y, x + widths[column], y + height), fill="#f1f1f1" if row_index == 0 else "white", outline="#888888", width=2)
            draw_text(draw, (x + 10, y + 12, x + widths[column] - 10, y + height), str(value), bold if row_index == 0 else body)
            x += widths[column]
        y += height
    if spec.get("note"):
        draw_text(draw, (pad, y + 18, image.width - pad, image.height - pad), "说明：" + spec["note"], ImageFont.truetype(fonts[0], 22), align="left")
    return image


def render_bar(spec: dict, fonts, horizontal: bool):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1700, 1050), "white")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(fonts[1], 40)
    label_font = ImageFont.truetype(fonts[0], 27)
    title_w = draw.textlength(spec["title"], font=title_font)
    draw.text(((1700 - title_w) / 2, 35), spec["title"], font=title_font, fill="#202020")
    categories = spec["categories"]
    series = spec["series"]
    maximum = float(spec.get("maximum", max(max(item["values"]) for item in series)))
    left, top, right, bottom = (500, 150, 1600, 820) if horizontal else (140, 150, 1620, 810)
    colors = ["#888888", "#bebebe", "#555555"]
    if horizontal:
        row = (bottom - top) / len(categories)
        for tick in range(0, int(maximum) + 1, int(spec.get("tick", 10))):
            x = left + (right - left) * tick / maximum
            draw.line((x, top, x, bottom), fill="#d2d2d2", width=2)
            draw.text((x - 10, bottom + 18), str(tick), font=label_font, fill="#202020")
        values = series[0]["values"]
        for index, (category, value) in enumerate(zip(categories, values)):
            y0 = top + index * row + 12
            y1 = top + (index + 1) * row - 12
            x1 = left + (right - left) * float(value) / maximum
            draw.rectangle((left, y0, x1, y1), fill=colors[0])
            width = draw.textlength(category, font=label_font)
            draw.text((left - width - 25, (y0 + y1) / 2 - 18), category, font=label_font, fill="#202020")
    else:
        group = (right - left) / len(categories)
        bar_w = min(70, group / (len(series) + 1))
        for index, category in enumerate(categories):
            center = left + group * (index + 0.5)
            for series_index, item in enumerate(series):
                value = float(item["values"][index])
                x0 = center + (series_index - (len(series) - 1) / 2) * (bar_w + 8) - bar_w / 2
                y0 = bottom - (bottom - top) * value / maximum
                draw.rectangle((x0, y0, x0 + bar_w, bottom), fill=colors[series_index % len(colors)])
            width = draw.textlength(category, font=label_font)
            draw.text((center - width / 2, bottom + 20), category, font=label_font, fill="#202020")
    if spec.get("note"):
        draw_text(draw, (80, 915, 1620, 1030), "说明：" + spec["note"], ImageFont.truetype(fonts[0], 23))
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Render data-driven localized tables and bar charts from visual specs.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project_dir = args.project.resolve()
    path = project_dir / "visuals" / "visuals.json"
    payload = read_json(path)
    defaults = None
    output_dir = project_dir / "visuals" / "localized"
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for visual in payload.get("visuals", []):
        spec = visual.get("render")
        if not spec:
            continue
        if not spec.get("font") or not spec.get("font_bold"):
            defaults = defaults or find_font(project_dir)
        fonts = (spec.get("font") or defaults[0], spec.get("font_bold") or defaults[1])
        kind = spec.get("type")
        if kind == "table":
            image = render_table(spec, fonts)
        elif kind == "bar-horizontal":
            image = render_bar(spec, fonts, True)
        elif kind == "bar-vertical":
            image = render_bar(spec, fonts, False)
        else:
            raise ValueError(f"Unsupported render type for {visual.get('id')}: {kind}")
        output = output_dir / spec.get("output", f"{visual['id']}.png")
        image.save(output, optimize=True)
        visual["localized_assets"] = [str(output.relative_to(project_dir))]
        visual["status"] = "LOCALIZED"
        rendered += 1
        print(output)
    write_json(path, payload)
    print(f"rendered={rendered}")


if __name__ == "__main__":
    main()
