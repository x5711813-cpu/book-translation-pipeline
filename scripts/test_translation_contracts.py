from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import sha256_file, sha256_text, write_json, write_jsonl
from translate_blocks import approved_items, context_package, load_approved_blocks, pilot_block_ids, relevant_items


def block(block_id: str, page: int, source: str) -> dict:
    return {
        "block_id": block_id,
        "section": "chapter-01",
        "kind": "prose",
        "source": source,
        "provenance": [{"page": page, "bbox": None}],
        "boundary_status": "READY",
        "source_sha256": sha256_text(source),
    }


class TranslationContractsTest(unittest.TestCase):
    def test_project_initializer_creates_knowledge_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            script = Path(__file__).with_name("init_project.py")
            subprocess.run([
                sys.executable, str(script), str(project), "--source", str(Path(__file__)), "--model", "translator",
            ], check=True, capture_output=True, text=True)
            config = (project / "project.json").read_text(encoding="utf-8")
            self.assertIn('"require_source_approval": true', config)
            self.assertTrue((project / "shared" / "glossary.json").exists())
            self.assertTrue((project / "shared" / "entities.json").exists())
            self.assertTrue((project / "shared" / "style-guide.md").exists())

    def test_pilot_counts_actual_pages(self) -> None:
        blocks = [block("b1", 1, "one"), block("b2", 1, "two"), block("b3", 2, "three")]
        self.assertEqual(pilot_block_ids(blocks, {"pilot_pages": 1}), {"b1", "b2"})

    def test_relevant_entries_are_selected_by_alias(self) -> None:
        entries = [{"name": "Richard", "aliases": ["Dick"]}, {"name": "Alice", "aliases": []}]
        self.assertEqual(relevant_items(entries, "Dick entered.", ("name", "aliases")), [entries[0]])

    def test_unapproved_knowledge_is_not_injected(self) -> None:
        entries = [{"source": "cousin", "target": "表兄", "status": "proposed"},
                   {"source": "Winterfell", "target": "临冬城", "status": "approved"}]
        self.assertEqual(approved_items(entries), [entries[1]])

    def test_context_changes_with_previous_approved_translation(self) -> None:
        blocks = [block("b1", 1, "Richard entered."), block("b2", 2, "He sat down.")]
        knowledge = {
            "legacy_terminology": {}, "glossary": {"entries": []}, "entities": {"entities": []},
            "decisions": {"decisions": []}, "continuity": {"sections": {}}, "style_guide": "",
        }
        config = {"workflow": {"neighbor_context_chars": 500, "knowledge_context_chars": 8000}}
        first = context_package(blocks, 1, {}, "r001", knowledge, config)
        existing = {"b1": {"status": "PASS", "source_revision": "r001", "translation": "理查德走了进来。"}}
        second = context_package(blocks, 1, existing, "r001", knowledge, config)
        self.assertNotEqual(first, second)

    def test_approved_revision_is_immutable_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "source").mkdir()
            blocks = [block("b1", 1, "Source text.")]
            write_jsonl(project / "source" / "blocks.jsonl", blocks)
            write_json(project / "source" / "source-manifest.json", {"source_sha256": sha256_file(Path(__file__))})
            script = Path(__file__).with_name("approve_source.py")
            subprocess.run([sys.executable, str(script), str(project)], check=True, capture_output=True, text=True)
            loaded, revision = load_approved_blocks(project, {"workflow": {"require_source_approval": True}})
            self.assertEqual(revision, "r001")
            self.assertEqual(loaded, blocks)
            write_json(project / "source" / "source-manifest.json", {"source_sha256": "changed"})
            with self.assertRaises(ValueError):
                load_approved_blocks(project, {"workflow": {"require_source_approval": True}})

    def test_dry_run_uses_approved_pilot_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            init = Path(__file__).with_name("init_project.py")
            subprocess.run([
                sys.executable, str(init), str(project), "--source", str(Path(__file__)), "--model", "translator",
            ], check=True, capture_output=True, text=True)
            blocks = [block("b1", 1, "one"), block("b2", 1, "two"), block("b3", 2, "three")]
            write_jsonl(project / "source" / "blocks.jsonl", blocks)
            write_json(project / "source" / "source-manifest.json", {"source_sha256": sha256_file(Path(__file__))})
            approve = Path(__file__).with_name("approve_source.py")
            subprocess.run([sys.executable, str(approve), str(project)], check=True, capture_output=True, text=True)
            config_path = project / "project.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["workflow"]["pilot_pages"] = 1
            write_json(config_path, config)
            translate = Path(__file__).with_name("translate_blocks.py")
            result = subprocess.run([
                sys.executable, str(translate), str(project), "--pilot", "--dry-run",
            ], check=True, capture_output=True, text=True)
            self.assertIn("READY b1", result.stdout)
            self.assertIn("READY b2", result.stdout)
            self.assertNotIn("READY b3", result.stdout)


if __name__ == "__main__":
    unittest.main()
