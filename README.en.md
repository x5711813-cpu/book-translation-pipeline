# Book Translation Pipeline

**Language: [中文](README.md) | English**

A Codex skill for translating, proofreading, and delivering complete books as EPUBs. It supports text PDFs, scanned PDFs, and EPUBs. The workflow emphasizes resumable processing, paragraph reconstruction, complete notes and indexes, Chinese publication proofreading, and auditable use of local models.

It can also **proofread an existing ebook, generate or repair a hierarchical table of contents, and reformat its layout** without translating it again. See [Ebook maintenance](references/ebook-maintenance.md) for the procedure and its limits. For example: “Proofread this EPUB, repair its table of contents, and make the body text and footnotes consistent.”

## Installation

Python 3.12 is recommended. Text PDF inspection uses `pypdf`; scanned PDFs use `pypdfium2`, Pillow, and local RapidOCR. Translation calls an Ollama-compatible `/api/chat` endpoint configured in the project. This repository does not download a model. Redrawing charts requires a local Chinese font, or `font` and `font_bold` paths in the visual configuration.

On Windows PowerShell, install the dependencies and copy the repository into the Codex skills directory:

```powershell
git clone https://github.com/x5711813-cpu/book-translation-pipeline.git
cd book-translation-pipeline
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$skillDir = "$env:USERPROFILE\.codex\skills\book-translation-pipeline"
New-Item -ItemType Directory -Force $skillDir | Out-Null
Copy-Item -Force SKILL.md $skillDir
Copy-Item -Recurse -Force agents,assets,references,scripts $skillDir
```

You can continue to run scripts with the cloned directory's `.venv`. Restart or refresh Codex, then invoke `$book-translation-pipeline` explicitly; suitable book translation requests may also trigger it automatically.

On macOS/Linux, create the environment with `python3.12 -m venv .venv` and use `.venv/bin/python` in the commands below. Make sure you have the right to process your input books. No book content is included in this repository.

## Minimal examples

To run a read-only structural audit on an existing EPUB, no translation model is needed:

```powershell
.\.venv\Scripts\python.exe scripts/ebook_tool.py audit --help
.\.venv\Scripts\python.exe scripts/ebook_tool.py audit "C:\books\input.epub" --output "C:\books\audit.json"
```

For a PDF translation, initialize a project and inspect the source first. Edit `project.json` to configure sections and the local model. Run OCR only for scanned pages. Then reconstruct semantic blocks, resolve boundaries, approve the source revision, run a translation pilot and review, build the EPUB, and audit it. Each script documents its arguments with `--help`. See the [translation workflow](references/workflow.md) for the full sequence and the [data contract](references/schemas.md#sections) for section settings.

```powershell
.\.venv\Scripts\python.exe scripts/init_project.py "C:\books\project" --source "C:\books\input.pdf" --title "Example Book" --model "your-local-model"
.\.venv\Scripts\python.exe scripts/inspect_source.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/ocr_pdf.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/build_blocks.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/resolve_boundaries.py "C:\books\project" --dry-run
.\.venv\Scripts\python.exe scripts/approve_source.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/translate_blocks.py "C:\books\project" --pilot
.\.venv\Scripts\python.exe scripts/build_epub.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/audit_project.py "C:\books\project"
```

If `--dry-run` lists unresolved boundaries, resolve them according to the [manual or model review instructions](references/workflow.md#3-reconstruct-the-source-book), then rebuild and approve the source revision. `build_epub.py` checks source approval, translation states, and cache metadata. Its build record means only that the file was built. Final delivery still requires `audit_project.py` and human review of content and layout. For independent work on an existing EPUB, see [Ebook maintenance](references/ebook-maintenance.md).

## Repository contents

- `SKILL.md`: skill entry point, routing, and essential constraints.
- `scripts/`: project setup, source inspection, OCR, semantic block reconstruction, translation and review, visual processing, EPUB building, and quality audits.
- `references/`: workflow, data contracts, OCR, EPUB, Chinese publication proofreading, and quality gates.
- `assets/`: project and EPUB style templates.
- `agents/openai.yaml`: Codex interface metadata.
- `CHANGELOG.md`: user-facing changes.
- `docs/iteration-history.md`: design decisions developed through real projects.
- `docs/reuse-inventory.md`: reusable tools, their inputs and outputs, and their limits.

The repository contains no source PDFs, translated books, model caches, project reports, or hard-coded fixes for a particular book.

## Validation

```powershell
python scripts/test_audit_manuscript.py
python scripts/test_ebook_tool.py
python scripts/test_translation_contracts.py
python scripts/test_pipeline_repairs.py
python scripts/audit_manuscript.py --help
python path\to\skill-creator\scripts\quick_validate.py .
```

By default, `audit_manuscript.py` blocks delivery only on high-confidence errors. With `--strict`, warnings and style suggestions also cause a nonzero exit code. Review suggestions in context rather than mechanically rewriting text to clear a report.

This repository is open source under the [MIT license](LICENSE). The OCR cache depends on the source, page numbers, parameters, script version, and output file hashes. Complex formulas, multiple columns, notes, charts, and visual layout still need human inspection. Automated tests and basic EPUB audits do not replace a page-by-page publication review.

## Design influences

The Chinese proofreader's severity levels, protected Markdown regions, strict mode, and regression tests were conceptually influenced by the MIT-licensed [Tech-Doc-Style-Chinese](https://github.com/Fenng/tech-doc-style-chinese). Its rules specific to technical documentation, such as quotation marks and spacing between Chinese and Latin text, were not copied directly; this skill follows the conventions of Chinese translated books.
