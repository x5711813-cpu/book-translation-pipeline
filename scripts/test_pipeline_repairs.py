from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from common import read_json, read_jsonl, sha256_file, sha256_text, write_json, write_jsonl
from translate_blocks import load_knowledge, translation_metadata
from audit_project import audit_epub
import ocr_pdf


SCRIPTS = Path(__file__).parent


class PipelineRepairsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "project"
        self.source = Path(self.temporary.name) / "source.txt"
        self.source.write_text("Source fixture", encoding="utf-8")
        self.run_cli("init_project.py", "--source", str(self.source))
        self.config = read_json(self.project / "project.json")
        self.config["sections"] = [self.section()]
        self.save_config()
        self.blocks = [{"block_id": "ch1-block-000001", "section": "ch1", "kind": "prose",
                        "source": "Source paragraph.", "source_sha256": sha256_text("Source paragraph."),
                        "boundary_status": "READY", "provenance": [{"page": 1}]}]
        write_jsonl(self.project / "source/blocks.jsonl", self.blocks)
        write_json(self.project / "source/source-manifest.json", {
            "detected_format": "pdf-text", "page_count": 2, "weak_pages": [],
            "source_sha256": sha256_file(self.source)})
        self.translations = [{"block_id": self.blocks[0]["block_id"], "status": "PASS", "translation": "BODY_SENTINEL"}]
        self.save_translations()
        self.approve_translations()

    def approve_translations(self) -> None:
        self.run_cli("approve_source.py")
        revision = read_json(self.project / "source/approved/current.json")["source_revision"]
        blocks = read_jsonl(self.project / "source/blocks.jsonl")
        knowledge, knowledge_hash = load_knowledge(self.project, self.config)
        records = {item["block_id"]: item for item in self.translations}
        for index, block in enumerate(blocks):
            records[block["block_id"]].update(translation_metadata(blocks, index, records, revision, knowledge, knowledge_hash, self.config))
        self.save_translations()

    @staticmethod
    def section(**overrides) -> dict:
        return {"slug": "ch1", "label": "Chapter 1", "start_page": 1, "end_page": 2, **overrides}

    def save_config(self) -> None:
        write_json(self.project / "project.json", self.config)

    def save_translations(self) -> None:
        write_jsonl(self.project / "translations/translations.jsonl", self.translations)

    def run_cli(self, script: str, *args: str, success: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), str(self.project), *args],
                                capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_orphan_review_does_not_block_build_and_is_retained(self) -> None:
        self.translations.append({"block_id": "old-block", "status": "REVIEW", "translation": "<think>old"})
        self.save_translations()
        result = self.run_cli("build_epub.py")
        self.assertIn("Historical translation rows", result.stdout)
        self.assertEqual(read_jsonl(self.project / "translations/translations.jsonl"), self.translations)
        report = read_json((self.project / self.config["target"]["output"]).with_suffix(".build.json"))
        self.assertEqual(report["orphan_translation_ids"], ["old-block"])

    def test_current_review_still_blocks_build(self) -> None:
        self.translations[0]["status"] = "REVIEW"
        self.save_translations()
        result = self.run_cli("build_epub.py", success=False)
        self.assertIn("Translations still need review", result.stderr)

    def test_changed_source_and_stale_translation_block_build(self) -> None:
        self.blocks[0]["source"] = "Different source."
        write_jsonl(self.project / "source/blocks.jsonl", self.blocks)
        self.assertIn("Working blocks changed", self.run_cli("build_epub.py", success=False).stderr)
        write_jsonl(self.project / "source/blocks.jsonl", [{**self.blocks[0], "source": "Source paragraph."}])
        self.translations[0]["context_sha256"] = "stale"
        self.save_translations()
        self.assertIn("Stale translations", self.run_cli("build_epub.py", success=False).stderr)

    def test_unresolved_source_blocks_build(self) -> None:
        self.blocks[0]["boundary_status"] = "REVIEW"
        write_jsonl(self.project / "source/blocks.jsonl", self.blocks)
        self.assertIn("Working blocks changed", self.run_cli("build_epub.py", success=False).stderr)

    def test_audit_orphans_do_not_add_review_or_contamination_errors(self) -> None:
        self.run_cli("approve_source.py")
        self.run_cli("audit_project.py", "--allow-incomplete")
        before = read_json(self.project / "reports/project-audit.json")
        self.translations.append({"block_id": "old-block", "status": "REVIEW", "translation": "<think>old"})
        self.save_translations()
        self.run_cli("audit_project.py", "--allow-incomplete")
        after = read_json(self.project / "reports/project-audit.json")
        self.assertEqual(after["errors"], before["errors"])
        self.assertEqual(after["orphan_translation_ids"], ["old-block"])
        self.assertTrue(any("Historical translation rows" in item for item in after["warnings"]))

    def test_slug_default_includes_body(self) -> None:
        self.run_cli("build_epub.py")
        with zipfile.ZipFile(self.project / self.config["target"]["output"]) as archive:
            self.assertIn("BODY_SENTINEL", archive.read("EPUB/text/ch1.xhtml").decode("utf-8"))

    def test_explicit_source_section_and_block_ids(self) -> None:
        for selection in ({"source_section": "ch1"}, {"block_ids": [self.blocks[0]["block_id"]]}):
            with self.subTest(selection=selection):
                self.config["sections"] = [self.section(slug="renamed", **selection)]
                self.save_config()
                self.run_cli("build_epub.py")
                with zipfile.ZipFile(self.project / self.config["target"]["output"]) as archive:
                    self.assertIn("BODY_SENTINEL", archive.read("EPUB/text/renamed.xhtml").decode("utf-8"))

    def test_chapter_coverage_rejects_omissions_duplicates_empty_unknown(self) -> None:
        second = {**self.blocks[0], "block_id": "ch2-block-000002", "section": "ch2"}
        write_jsonl(self.project / "source/blocks.jsonl", [*self.blocks, second])
        self.translations.append({"block_id": second["block_id"], "status": "PASS", "translation": "SECOND"})
        self.save_translations()
        self.approve_translations()
        cases = [
            ([self.section()], "omitted="),
            ([self.section(), {"slug": "copy", "label": "Copy", "source_section": "ch1"}], "duplicated="),
            ([self.section(block_ids=[])], "Empty section"),
            ([self.section(block_ids=["unknown"])], "Unknown block IDs"),
        ]
        for sections, message in cases:
            with self.subTest(message=message):
                self.config["sections"] = sections
                self.save_config()
                result = self.run_cli("build_epub.py", success=False)
                self.assertIn(message, result.stderr)
                self.assertFalse((self.project / self.config["target"]["output"]).exists())

    def test_invalid_sections_fail_with_actionable_errors(self) -> None:
        cases = [
            ([{"slug": "ch1", "label": "Chapter", "pages": [1, 2]}], "start_page/end_page"),
            ([self.section(end_page=0)], "start_page/end_page"),
            ([self.section(), self.section(slug="ch2")], "Overlapping"),
            ([self.section(), self.section()], "Duplicate section slug"),
        ]
        for sections, message in cases:
            with self.subTest(message=message):
                self.config["sections"] = sections
                self.save_config()
                result = self.run_cli("build_blocks.py", success=False)
                self.assertIn(message, result.stderr)

    def prepare_pages(self) -> None:
        for page in (1, 2):
            (self.project / f"source/pages/page-{page:04d}.text.txt").write_text(f"Paragraph {page}.", encoding="utf-8")

    def test_unmatched_pages_warn(self) -> None:
        self.prepare_pages()
        self.config["sections"] = [self.section(start_page=10, end_page=20)]
        self.save_config()
        result = self.run_cli("build_blocks.py")
        self.assertIn("2 blocks unmatched", result.stdout)

    def test_no_pending_needs_no_model(self) -> None:
        self.assertIn("pending=0", self.run_cli("resolve_boundaries.py").stdout)

    def test_manual_decision_survives_rebuild_without_model(self) -> None:
        self.prepare_pages()
        key = "page-0001-to-0002"
        path = self.project / "repairs/boundary-decisions.json"
        write_json(path, {"decisions": {key: {"decision": "REVIEW"}}})
        self.run_cli("resolve_boundaries.py", "--decide", key + "=SPLIT", "--reason", "Source checked")
        self.run_cli("build_blocks.py")
        decision = read_json(path)["decisions"][key]
        self.assertEqual(decision["method"], "manual")
        self.assertEqual(decision["reason"], "Source checked")
        self.assertEqual(decision["decision"], "SPLIT")
        self.run_cli("approve_source.py")
        self.run_cli("resolve_boundaries.py")

    def test_manual_validation_is_atomic_and_dry_run_does_not_write(self) -> None:
        key = "page-0001-to-0002"
        path = self.project / "repairs/boundary-decisions.json"
        write_json(path, {"decisions": {key: {"decision": "REVIEW"}}})
        before = path.read_bytes()
        self.run_cli("resolve_boundaries.py", "--decide", key + "=JOIN", success=False)
        self.assertEqual(path.read_bytes(), before)
        self.run_cli("resolve_boundaries.py", "--decide", key + "=JOIN", "--decide", "missing=SPLIT", "--reason", "Checked", success=False)
        self.assertEqual(path.read_bytes(), before)
        self.run_cli("resolve_boundaries.py", "--decide", key + "=JOIN", "--reason", "Checked", "--dry-run")
        self.assertEqual(path.read_bytes(), before)

    def test_nested_epub_text_once_and_broken_fragment_detected(self) -> None:
        self.run_cli("build_epub.py")
        path = self.project / "nested.epub"
        built = self.project / self.config["target"]["output"]
        with zipfile.ZipFile(built) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files["EPUB/text/ch1.xhtml"] = files["EPUB/text/ch1.xhtml"].replace(b"</body>", b'<a href="#missing">note</a></body>')
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in files.items():
                archive.writestr(name, data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
        self.assertTrue(any("Missing anchor" in error for error in audit_epub(path)))
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("EPUB/text/nested.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><blockquote><p>Alpha.</p><p>Beta.</p></blockquote><p>Tail <em>inline</em> text.</p></body></html>')
        self.config["source"]["path"] = str(path)
        self.save_config()
        write_json(self.project / "source/source-manifest.json", {"detected_format": "epub-reflowable", "spine": ["EPUB/text/nested.xhtml"]})
        self.run_cli("extract_epub_blocks.py")
        self.assertEqual([block["source"] for block in read_jsonl(self.project / "source/blocks.jsonl")], ["Alpha.", "Beta.", "Tail inline text."])

    def test_ocr_cache_skips_unchanged_page_and_rechecks_changed_source(self) -> None:
        source = self.project / "scan.pdf"
        source.write_bytes(b"fixture")
        self.config["source"]["path"] = str(source)
        self.config["ocr"]["python"] = ""
        self.save_config()
        write_json(self.project / "source/source-manifest.json", {"source_sha256": sha256_file(source), "weak_pages": [1]})

        class Image:
            def convert(self, mode):
                return self

            def save(self, path, **kwargs):
                Path(path).write_bytes(b"rendered")

        page = SimpleNamespace(render=lambda **kwargs: SimpleNamespace(to_pil=Image))
        document = lambda source: [page]
        calls = []

        def engine(path):
            calls.append(path)
            return [([[0, 0], [1, 0], [1, 1], [0, 1]], "Sample text", 0.99)], 0.1

        with (patch.dict(sys.modules, {"pypdfium2": SimpleNamespace(PdfDocument=document), "PIL": SimpleNamespace(Image=Image)}),
              patch.object(ocr_pdf, "rapid_engine", return_value=engine),
              patch.object(ocr_pdf, "version", return_value="test"),
              patch.object(sys, "argv", ["ocr_pdf.py", str(self.project)])):
            ocr_pdf.main()
            ocr_pdf.main()
            self.assertEqual(len(calls), 1)
            source.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Source changed"):
                ocr_pdf.main()


if __name__ == "__main__":
    unittest.main()
