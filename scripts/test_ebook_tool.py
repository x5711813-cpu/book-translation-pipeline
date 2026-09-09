from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from ebook_tool import Book, H, E, N, O, audit, content, nodes, outline, rewrite


class EbookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def book(self, version="3.0", fixed=False, ncx=False, prefix=False):
        path = self.root / "input.epub"
        ns = 'xmlns:x="' + H + '"' if prefix else 'xmlns="' + H + '"'

        def xhtml(body):
            raw = f'<html xmlns="{H}" xmlns:epub="{E}"><head><title>样书</title></head><body>{body}</body></html>'
            if prefix:
                import re
                raw = raw.replace(f'xmlns="{H}"', ns)
                raw = re.sub(r"(<\/?)(html|head|title|body|h1|h2|h3|p|em|a|aside|img)(?=[\s>/])", r"\1x:\2", raw)
            return raw.encode()

        fixed_meta = '<meta property="rendition:layout">pre-paginated</meta>' if fixed else ""
        nav_item = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>' if version.startswith("3") else ""
        ncx_item = '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>' if ncx else ""
        toc_attr = ' toc="ncx"' if ncx else ""
        files = {
            "mimetype": b"application/epub+zip",
            "META-INF/container.xml": b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
            "OPS/package.opf": f'<package xmlns="{O}" version="{version}" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">test-book</dc:identifier><dc:title>样书</dc:title><dc:language>zh-CN</dc:language>{fixed_meta}</metadata><manifest><item id="c1" href="text/第一%20章.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="text/second.xhtml" media-type="application/xhtml+xml"/><item id="img" href="images/a.bin" media-type="application/octet-stream"/>{nav_item}{ncx_item}</manifest><spine{toc_attr}><itemref idref="c1"/><itemref idref="c2"/></spine></package>'.encode(),
            "OPS/text/第一 章.xhtml": xhtml('<h1 id="chapter-one">同名章</h1><h2>小节 &amp; 引文</h2><p id="ref">正文<em>强调</em>内容。<a epub:type="noteref" href="#note">1</a></p><aside id="note" epub:type="footnote">注释。<a href="#ref">↩</a></aside><img src="../images/a.bin" alt="示意图"/>'),
            "OPS/text/second.xhtml": xhtml('<h1 id="chapter-two">同名章</h1><h2>另一节</h2><h3>子节</h3><p>末尾正文。</p>'),
            "OPS/images/a.bin": bytes(range(256)),
        }
        if version.startswith("3"):
            files["OPS/nav.xhtml"] = f'<html xmlns="{H}" xmlns:epub="{E}"><head><title>目录</title></head><body><nav id="toc" epub:type="toc"><ol><li><a href="text/second.xhtml#chapter-two">旧目录</a></li></ol></nav><nav epub:type="landmarks"><ol><li><a epub:type="bodymatter" href="text/第一%20章.xhtml#chapter-one">正文</a></li></ol></nav></body></html>'.encode()
        if ncx:
            files["OPS/toc.ncx"] = f'<ncx xmlns="{N}" version="2005-1"><head><meta name="dtb:uid" content="test-book"/></head><docTitle><text>样书</text></docTitle><navMap><navPoint id="old" playOrder="1"><navLabel><text>旧目录</text></navLabel><content src="text/second.xhtml#chapter-two"/></navPoint></navMap></ncx>'.encode()
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in files.items():
                archive.writestr(name, data, compress_type=zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
        return Book(path)

    def plan(self, book):
        path = self.root / "outline.json"
        path.write_text(json.dumps(outline(book), ensure_ascii=False), encoding="utf-8")
        return path

    def test_nested_toc_ncx_resources_and_notes_preserved(self):
        book = self.book(ncx=True)
        original = dict(book.files)
        output = self.root / "final.epub"
        report = rewrite(book, output, toc=self.plan(book))
        self.assertEqual(report["errors"], [])
        final = Book(output)
        toc = [n for n in nodes(final.doc("OPS/nav.xhtml"), H, "nav") if n.getAttributeNS(E, "type") == "toc"][0]
        self.assertEqual(len(nodes(toc, H, "a")), 5)
        self.assertEqual(len(nodes(toc, H, "ol")), 4)
        self.assertEqual(toc.getAttribute("id"), "toc")
        labels = [content(n) for n in nodes(toc, H, "a")]
        self.assertEqual(labels.count("同名章"), 2)
        self.assertEqual([content(n) for n in nodes(final.doc("OPS/toc.ncx"), N, "navLabel")], labels)
        self.assertEqual(final.files["OPS/images/a.bin"], original["OPS/images/a.bin"])
        self.assertEqual(nodes(final.doc("OPS/text/第一 章.xhtml"), H, "aside")[0].getAttribute("id"), "note")
        self.assertEqual(len([n for n in nodes(final.doc("OPS/nav.xhtml"), H, "nav") if n.getAttributeNS(E, "type") == "landmarks"]), 1)
        self.assertEqual(Book(book.path).files, original)

    def test_css_only_preserves_text_and_prefixed_namespaces(self):
        book = self.book(prefix=True)
        plan_before = outline(book)
        css = self.root / "style.css"
        css.write_text("body { line-height: 1.75; }", encoding="utf-8")
        output = self.root / "styled.epub"
        report = rewrite(book, output, css=css)
        self.assertEqual(report["errors"], [])
        result = Book(output)
        self.assertEqual(outline(result)["entries"], plan_before["entries"])
        self.assertIn(b"x:html", result.files["OPS/text/第一 章.xhtml"])
        self.assertEqual(result.files["OPS/nav.xhtml"], book.files["OPS/nav.xhtml"])
        links = nodes(result.doc("OPS/text/second.xhtml"), H, "link")
        self.assertEqual(len(links), 1)

    def test_epub2_adds_ncx_without_upgrading(self):
        book = self.book(version="2.0")
        output = self.root / "epub2.epub"
        self.assertEqual(rewrite(book, output, toc=self.plan(book))["errors"], [])
        final = Book(output)
        self.assertFalse(final.version3)
        item = final.items[final.spine.getAttribute("toc")]
        self.assertEqual(len(nodes(final.doc(final.item_path(item)), N, "navPoint")), 5)
        self.assertFalse(any("nav" in item.getAttribute("properties").split() for item in final.items.values()))

    def test_missing_nav_can_be_created(self):
        book = self.book()
        nav = book.items.pop("nav")
        book.manifest.removeChild(nav)
        del book.files["OPS/nav.xhtml"]
        output = self.root / "new-nav.epub"
        self.assertEqual(rewrite(book, output, toc=self.plan(book))["errors"], [])

    def test_audit_detects_fragment_duplicate_id_and_spine_errors(self):
        book = self.book()
        doc = book.doc("OPS/text/second.xhtml")
        nodes(doc, H, "p")[0].setAttribute("id", "chapter-two")
        nodes(book.doc("OPS/nav.xhtml"), H, "a")[0].setAttribute("href", "text/second.xhtml#missing")
        nodes(book.spine, O, "itemref")[0].setAttribute("idref", "absent")
        errors = "\n".join(audit(book)["errors"])
        self.assertIn("Duplicate ID", errors)
        self.assertIn("Missing anchor", errors)
        self.assertIn("Unknown spine", errors)

    def test_stale_plan_and_invalid_hierarchy_rejected(self):
        book = self.book()
        plan = self.plan(book)
        data = json.loads(plan.read_text(encoding="utf-8"))
        data["source_sha256"] = "stale"
        plan.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            rewrite(book, self.root / "bad.epub", toc=plan)
        data["source_sha256"] = book.sha256
        data["entries"][0]["level"] = 2
        plan.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "levels"):
            rewrite(book, self.root / "bad.epub", toc=plan)
        self.assertFalse((self.root / "bad.epub").exists())

    def test_fixed_layout_css_and_overwrites_rejected(self):
        book = self.book(fixed=True)
        css = self.root / "style.css"
        css.write_text("body { margin: 5%; }", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Fixed-layout"):
            rewrite(book, self.root / "bad.epub", css=css)
        with self.assertRaisesRegex(ValueError, "never overwritten"):
            rewrite(book, book.path, css=css)
        self.assertFalse((self.root / "bad.epub").exists())

    def test_rerun_keeps_heading_anchors(self):
        book = self.book()
        first = self.root / "first.epub"
        rewrite(book, first, toc=self.plan(book))
        book2 = Book(first)
        anchors = [e.get("anchor") for e in outline(book2)["entries"]]
        rewrite(book2, self.root / "second.epub", toc=self.plan(book2))
        self.assertEqual(anchors, [e.get("anchor") for e in outline(Book(self.root / "second.epub"))["entries"]])

    def test_cli_errors_are_concise_and_exit_nonzero(self):
        path = self.root / "invalid.epub"
        path.write_bytes(b"not a zip")
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("ebook_tool.py")), "audit", str(path), "--output", str(self.root / "audit.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(json.loads((self.root / "audit.json").read_text(encoding="utf-8"))["status"], "FAIL")

    def test_combined_toc_css_and_out_of_order_plan(self):
        book = self.book()
        plan = self.plan(book)
        css = self.root / "style.css"
        css.write_bytes((Path(__file__).parents[1] / "assets/epub-template/reflow.css").read_bytes())
        output = self.root / "combined.epub"
        report = rewrite(book, output, toc=plan, css=css)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["unedited_resources_preserved"])
        result = Book(output)
        plan = self.plan(result)
        data = json.loads(plan.read_text(encoding="utf-8"))
        data["entries"] = list(reversed(data["entries"]))
        for entry in data["entries"]:
            entry["level"] = 1
        plan.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "order"):
            rewrite(result, self.root / "wrong-order.epub", toc=plan)

    def test_encryption_and_resource_css_need_separate_handling(self):
        book = self.book()
        book.files["META-INF/encryption.xml"] = b"<encryption/>"
        with self.assertRaisesRegex(ValueError, "Encrypted"):
            rewrite(book, self.root / "encrypted.epub", toc=self.plan(book))
        del book.files["META-INF/encryption.xml"]
        css = self.root / "style.css"
        css.write_text("body { background: url(missing.png); }", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "imports"):
            rewrite(book, self.root / "css.epub", css=css)

    def test_heading_id_collision_is_avoided(self):
        book = self.book()
        doc = book.doc("OPS/text/第一 章.xhtml")
        nodes(doc, H, "em")[0].setAttribute("id", "ebook-heading-2")
        book.store("OPS/text/第一 章.xhtml")
        output = self.root / "anchors.epub"
        self.assertEqual(rewrite(book, output, toc=self.plan(book))["errors"], [])
        final = Book(output)
        self.assertEqual(final.headings("OPS/text/第一 章.xhtml")[1].getAttribute("id"), "ebook-heading-2-1")


if __name__ == "__main__":
    unittest.main()
