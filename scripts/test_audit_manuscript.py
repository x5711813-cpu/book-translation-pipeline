from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_manuscript.py")


class AuditManuscriptTests(unittest.TestCase):
    def run_audit(self, text: str, *options: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manuscript = root / "book.md"
            report = root / "report.json"
            manuscript.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(manuscript), "--output", str(report), *options],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            return result, json.loads(report.read_text(encoding="utf-8"))

    def test_missing_note_definition_is_blocking_error(self) -> None:
        result, report = self.run_audit("正文。[^missing]\n")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["severity_counts"]["error"], 1)
        self.assertEqual(report["findings"][0]["category"], "missing_note_definition")

    def test_warning_passes_default_but_strict_fails(self) -> None:
        normal, report = self.run_audit("这一段没有句号\n")
        self.assertEqual(normal.returncode, 0)
        self.assertEqual(report["status"], "PASS_WITH_CANDIDATES")
        strict, strict_report = self.run_audit("这一段没有句号\n", "--strict")
        self.assertEqual(strict.returncode, 2)
        self.assertEqual(strict_report["status"], "FAIL")

    def test_protected_markdown_is_not_scanned(self) -> None:
        text = """---
title: <sup>ignored</sup>
---

正文包含 `错误；` 和 [链接](https://example.com/a；b)。

```html
<sup>ignored</sup>
```

这一行含有<sup>但已豁免</sup>。 <!-- book-proofread-disable-line -->
"""
        result, report = self.run_audit(text)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "CLEAR")

    def test_repetition_is_contextual_warning(self) -> None:
        result, report = self.run_audit("他们竞相表达他们竞相表达友好之意。\n")
        self.assertEqual(result.returncode, 0)
        finding = next(item for item in report["findings"] if item["category"] == "repeated_phrase_candidate")
        self.assertEqual(finding["severity"], "warning")

    def test_ascii_punctuation_is_style_candidate(self) -> None:
        result, report = self.run_audit("这是前句,这是后句。\n")
        self.assertEqual(result.returncode, 0)
        finding = next(item for item in report["findings"] if item["category"] == "mixed_ascii_punctuation_candidate")
        self.assertEqual(finding["severity"], "style")


if __name__ == "__main__":
    unittest.main()
