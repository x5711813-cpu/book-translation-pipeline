from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from common import write_json


DIRECTORIES = [
    "source/pages", "source/images", "source/epub", "sections", "translations",
    "assembled/chapters", "repairs", "visuals/originals", "visuals/localized", "output", "reports",
]


def default_ocr_python() -> str:
    if os.environ.get("BOOK_OCR_PYTHON"):
        return os.environ["BOOK_OCR_PYTHON"]
    runtime = Path.home() / "codex" / ".local-tools" / "book-ocr" / "runtime.json"
    if runtime.exists():
        try:
            candidate = json.loads(runtime.read_text(encoding="utf-8")).get("python", "")
            if candidate and Path(candidate).exists():
                return candidate
        except (OSError, json.JSONDecodeError):
            pass
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reusable book-translation project.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ocr-python", default=default_ocr_python())
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    project = args.project.resolve()
    config_path = project / "project.json"
    if config_path.exists() and not args.force:
        raise FileExistsError(f"Project already initialized: {config_path}")

    template = Path(__file__).parent.parent / "assets" / "project-template" / "project.json"
    config = json.loads(template.read_text(encoding="utf-8"))
    config["source"]["path"] = str(source)
    config["target"]["title"] = args.title
    config["target"]["author"] = args.author
    config["model"]["name"] = args.model
    config["model"]["base_url"] = args.base_url.rstrip("/")
    config["ocr"]["python"] = args.ocr_python
    for name in DIRECTORIES:
        (project / name).mkdir(parents=True, exist_ok=True)
    write_json(config_path, config)
    write_json(project / "visuals" / "visuals.json", {"visuals": []})
    write_json(project / "repairs" / "boundary-decisions.json", {"decisions": {}})
    write_json(project / "repairs" / "boundary-rewrites.json", {"rewrites": {}})
    stylesheet = Path(__file__).parent.parent / "assets" / "epub-template" / "stylesheet.css"
    shutil.copy2(stylesheet, project / "output" / "stylesheet.css")
    print(config_path)


if __name__ == "__main__":
    main()
