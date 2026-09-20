"""Inspect EPUBs and apply reviewed TOCs/CSS without a translation project."""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import posixpath
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from xml.dom import minidom as DOM
from xml.parsers.expat import ExpatError
import zipfile

H = "http://www.w3.org/1999/xhtml"
O = "http://www.idpf.org/2007/opf"
E = "http://www.idpf.org/2007/ops"
N = "http://www.daisy.org/z3986/2005/ncx/"
DC = "http://purl.org/dc/elements/1.1/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def nodes(root, ns, tag):
    return list(root.getElementsByTagNameNS(ns, tag))


def content(node):
    if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
        return node.data
    return "".join(content(child) for child in node.childNodes)


def parse(data):
    if b"<!ENTITY" in data.upper():
        raise ValueError("XML entity declarations require manual handling")
    return DOM.parseString(data)


def element(doc, ns, tag, text=None, **attrs):
    prefix = doc.documentElement.prefix if doc.documentElement.namespaceURI == ns else None
    node = doc.createElementNS(ns, f"{prefix}:{tag}" if prefix else tag)
    for key, value in attrs.items():
        node.setAttribute(key, str(value))
    if text is not None:
        node.appendChild(doc.createTextNode(text))
    return node


def resolve(base, href):
    url = urlsplit(href)
    if url.scheme or url.netloc:
        return None, None
    name = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(url.path))) if url.path else base
    if name.startswith(("../", "/")) or "\\" in name:
        raise ValueError(f"Unsafe EPUB resource path: {href}")
    return name, unquote(url.fragment)


def relative(base, target, anchor=""):
    link = quote(posixpath.relpath(target, posixpath.dirname(base)), safe="/")
    return link + ("#" + quote(anchor, safe="") if anchor else "")


def save_json(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


class Book:
    def __init__(self, path):
        self.path = path
        self.sha256 = digest(path.read_bytes())
        with zipfile.ZipFile(path) as archive:
            self.infos = archive.infolist()
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP member names")
            self.files = {name: archive.read(name) for name in names}
        self.docs = {}
        container = self.doc("META-INF/container.xml")
        roots = nodes(container, "urn:oasis:names:tc:opendocument:xmlns:container", "rootfile")
        if len(roots) != 1:
            raise ValueError("Expected one rendition; multiple rootfiles need explicit selection")
        self.opf = roots[0].getAttribute("full-path")
        self.package = self.doc(self.opf)
        self.version3 = self.package.documentElement.getAttribute("version").startswith("3")
        self.manifest = nodes(self.package, O, "manifest")[0]
        self.spine = nodes(self.package, O, "spine")[0]
        self.items = {node.getAttribute("id"): node for node in nodes(self.manifest, O, "item")}

    def doc(self, name):
        if name not in self.docs:
            self.docs[name] = parse(self.files[name])
        return self.docs[name]

    def item_path(self, item):
        return resolve(self.opf, item.getAttribute("href"))[0]

    def reading_files(self):
        result = []
        for ref in nodes(self.spine, O, "itemref"):
            item = self.items[ref.getAttribute("idref")]
            if ref.getAttribute("linear") == "no" or "nav" in item.getAttribute("properties").split():
                continue
            if item.getAttribute("media-type") != "application/xhtml+xml":
                continue
            name = self.item_path(item)
            if name not in result:
                result.append(name)
        return result

    def headings(self, name):
        body = nodes(self.doc(name), H, "body")[0]
        return [n for n in nodes(body, H, "*") if n.localName in {"h1", "h2", "h3", "h4", "h5", "h6"}]

    def store(self, name):
        self.files[name] = self.docs[name].toxml(encoding="utf-8")

    def add_item(self, stem, suffix, mime, properties=""):
        ident = stem
        count = 1
        while ident in self.items or posixpath.join(posixpath.dirname(self.opf), ident + suffix) in self.files:
            ident = f"{stem}-{count}"
            count += 1
        item = element(self.package, O, "item", id=ident, href=ident + suffix, **{"media-type": mime})
        if properties:
            item.setAttribute("properties", properties)
        self.manifest.appendChild(item)
        self.items[ident] = item
        return item


def audit(book):
    errors, warnings = [], []
    if not book.infos or book.infos[0].filename != "mimetype" or book.infos[0].compress_type != zipfile.ZIP_STORED:
        errors.append("mimetype must be first and uncompressed")
    if book.files.get("mimetype") != b"application/epub+zip":
        errors.append("Invalid mimetype content")
    ids = {}
    for name in book.files:
        if name.endswith((".xml", ".opf", ".xhtml", ".html", ".ncx", ".svg")):
            try:
                doc = book.doc(name)
            except Exception as exc:
                errors.append(f"Invalid XML {name}: {exc}")
                continue
            values = [node.getAttribute("id") for node in doc.getElementsByTagName("*") if node.hasAttribute("id")]
            ids[name] = set(values)
            errors.extend(f"Duplicate ID {name}#{key}" for key, count in Counter(values).items() if count > 1)
    for name, doc in book.docs.items():
        for node in doc.getElementsByTagName("*"):
            if node.hasAttribute("xml:base") or (node.namespaceURI == H and node.localName == "base"):
                warnings.append(f"Base URI override needs manual link validation: {name}")
            for attr in ("href", "src", "xlink:href"):
                if not node.hasAttribute(attr):
                    continue
                href = node.getAttribute(attr)
                try:
                    target, anchor = resolve(name, href)
                    if target is None:
                        continue
                    if target not in book.files:
                        errors.append(f"Missing resource {name}: {href}")
                    elif anchor and target in ids and anchor not in ids[target]:
                        errors.append(f"Missing anchor {name}: {href}")
                except ValueError as exc:
                    errors.append(str(exc))
    refs = nodes(book.spine, O, "itemref")
    if not refs:
        errors.append("Empty spine")
    for ref in refs:
        if ref.getAttribute("idref") not in book.items:
            errors.append(f"Unknown spine idref: {ref.getAttribute('idref')}")
    navs = [i for i in book.items.values() if "nav" in i.getAttribute("properties").split()]
    if book.version3 and len(navs) != 1:
        errors.append("EPUB 3 requires exactly one navigation manifest item")
    for item in navs:
        name = book.item_path(item)
        if name not in book.docs:
            continue
        toc = [n for n in nodes(book.doc(name), H, "nav") if "toc" in n.getAttributeNS(E, "type").split()]
        if len(toc) != 1 or not nodes(toc[0], H, "a"):
            errors.append(f"Missing or empty navigation TOC: {name}")
    if not book.version3 and book.spine.getAttribute("toc") not in book.items:
        errors.append("EPUB 2 spine has no resolvable NCX item")
    for special in ("META-INF/encryption.xml", "META-INF/signatures.xml"):
        if special in book.files:
            warnings.append(f"Special handling required: {special}")
    return {"status": "FAIL" if errors else "BASIC_CHECKS_PASS", "epub": str(book.path), "sha256": book.sha256,
            "errors": errors, "warnings": warnings, "resources": len(book.files), "spine_items": len(refs),
            "scope": "Basic XML, manifest/spine and href/src/fragment checks; not EPUBCheck, textual proofreading or visual QA."}


def outline_warnings(entries):
    """Flag semantic candidates; never silently drop or reparent book content."""
    findings = []
    roots, parents = {}, {}
    for entry in entries:
        name, label, level = entry['file'], entry['label'], entry['level']
        def warn(code):
            findings.append(dict(code=code, file=name, heading_index=entry['heading_index'], label=label))
        if re.search(r'→\s*#|\b(forward pass|backward pass|zero the parameter gradients)\b', label, re.I):
            warn('possible-code-comment-heading')
        if level == 1:
            if name in roots:
                warn('multiple-top-level-headings-review')
            roots[name] = label
        match = re.match(r'^((?:\d+|[A-Z])(?:\.\d+)+)\s', label)
        if match:
            number = match.group(1)
            depth = number.count('.') + 1
            # Advisory: books may have a part/chapter offset or a custom scheme.
            if level != depth:
                warn('numbered-heading-level-review')
            if depth > 2 and parents.get((name, depth - 1)) != number.rsplit('.', 1)[0]:
                warn('numbered-heading-parent-review')
            parents[name, depth] = number
            for key in list(parents):
                if key[0] == name and key[1] > depth:
                    del parents[key]
    return findings


def outline(book):
    entries, levels = [], []
    for name in book.reading_files():
        headings = book.headings(name)
        if not headings:
            titles = nodes(book.doc(name), H, "title")
            entries.append(dict(label=content(titles[0]).strip() if titles else name, level=1, file=name, heading_index=None))
            levels = []
        for index, node in enumerate(headings):
            label = " ".join(content(node).split())
            if not label:
                continue
            raw_level = int(node.localName[1])
            while levels and levels[-1] >= raw_level:
                levels.pop()
            levels.append(raw_level)
            entries.append(dict(label=label, level=len(levels), source_level=raw_level, file=name,
                                heading_index=index, anchor=node.getAttribute("id")))
    return {"source_sha256": book.sha256, "entries": entries,
            "warnings": outline_warnings(entries), "status": "CANDIDATES_REQUIRE_REVIEW"}


def checked_entries(book, plan):
    if plan.get("source_sha256") != book.sha256:
        raise ValueError("TOC plan is stale: input SHA-256 differs")
    entries, seen, previous = [], set(), 0
    reading = book.reading_files()
    for source in plan["entries"]:
        entry = dict(source)
        name, index, level = entry["file"], entry["heading_index"], entry["level"]
        if name not in reading or (name, index) in seen:
            raise ValueError("TOC target is not in reading order or is duplicated")
        if type(level) is not int or not 1 <= level <= 6 or level > previous + 1:
            raise ValueError("TOC levels must start at 1 and cannot skip a level")
        if not isinstance(entry["label"], str) or not entry["label"].strip():
            raise ValueError("Empty TOC label")
        seen.add((name, index))
        previous = level
        entry["anchor"] = ""
        if index is not None:
            headings = book.headings(name)
            if type(index) is not int or not 0 <= index < len(headings):
                raise ValueError("Invalid heading_index")
            node = headings[index]
            if not node.getAttribute("id"):
                existing = {n.getAttribute("id") for n in book.doc(name).getElementsByTagName("*")}
                anchor, count = f"ebook-heading-{index + 1}", 1
                while anchor in existing:
                    anchor = f"ebook-heading-{index + 1}-{count}"
                    count += 1
                node.setAttribute("id", anchor)
                book.store(name)
            entry["anchor"] = node.getAttribute("id")
        entries.append(entry)
    if not entries:
        raise ValueError("Cannot generate an empty TOC")
    positions = [(reading.index(e["file"]), -1 if e["heading_index"] is None else e["heading_index"]) for e in entries]
    if positions != sorted(positions):
        raise ValueError("TOC entries must follow spine and heading order")
    return entries


def update_toc(book, entries):
    if book.version3:
        items = [i for i in book.items.values() if "nav" in i.getAttribute("properties").split()]
        if len(items) > 1:
            raise ValueError("Multiple nav documents require manual repair")
        item = items[0] if items else book.add_item("ebook-nav", ".xhtml", "application/xhtml+xml", "nav")
        name = book.item_path(item)
        if name not in book.files:
            book.files[name] = f'<html xmlns="{H}" xmlns:epub="{E}"><head><title>目录</title></head><body/></html>'.encode()
        doc = book.doc(name)
        old = [n for n in nodes(doc, H, "nav") if "toc" in n.getAttributeNS(E, "type").split()]
        if len(old) > 1:
            raise ValueError("Multiple TOC nav elements require manual repair")
        nav = old[0] if old else element(doc, H, "nav")
        if not old:
            nodes(doc, H, "body")[0].appendChild(nav)
        nav.setAttribute("xmlns:epub", E)
        nav.setAttributeNS(E, "epub:type", "toc")
        # Preserve the nav element's ID and attributes; replace only its contents.
        for child in list(nav.childNodes):
            nav.removeChild(child)
        nav.appendChild(element(doc, H, "h1", "目录"))
        root_list = element(doc, H, "ol")
        nav.appendChild(root_list)
        lists, last = [root_list], None
        for entry in entries:
            while len(lists) > entry["level"]:
                lists.pop()
            if len(lists) < entry["level"]:
                child_list = element(doc, H, "ol")
                last.appendChild(child_list)
                lists.append(child_list)
            last = element(doc, H, "li")
            lists[-1].appendChild(last)
            last.appendChild(element(doc, H, "a", entry["label"], href=relative(name, entry["file"], entry["anchor"])))
        book.store(name)
    ncxs = [i for i in book.items.values() if i.getAttribute("media-type") == "application/x-dtbncx+xml"]
    if len(ncxs) > 1:
        raise ValueError("Multiple NCX documents require manual selection")
    if not book.version3 and not ncxs:
        item = book.add_item("ebook-toc", ".ncx", "application/x-dtbncx+xml")
        ncxs = [item]
        name = book.item_path(item)
        doc = parse(f'<ncx xmlns="{N}" version="2005-1"><head/><docTitle><text/></docTitle><navMap/></ncx>'.encode())
        identifiers = nodes(book.package, DC, "identifier")
        uid_id = book.package.documentElement.getAttribute("unique-identifier")
        uid = next((content(n) for n in identifiers if n.getAttribute("id") == uid_id), "")
        if not uid:
            raise ValueError("Missing package unique identifier")
        head = nodes(doc, N, "head")[0]
        for key, value in (("dtb:uid", uid), ("dtb:totalPageCount", "0"), ("dtb:maxPageNumber", "0")):
            head.appendChild(element(doc, N, "meta", name=key, content=value))
        titles = nodes(book.package, DC, "title")
        nodes(doc, N, "text")[0].appendChild(doc.createTextNode(content(titles[0]) if titles else "目录"))
        book.docs[name] = doc
    for item in ncxs:
        book.spine.setAttribute("toc", item.getAttribute("id"))
        name = book.item_path(item)
        doc = book.doc(name)
        navmap = nodes(doc, N, "navMap")[0]
        for child in list(navmap.childNodes):
            navmap.removeChild(child)
        existing = {n.getAttribute("id") for n in doc.getElementsByTagName("*")}
        parents = [navmap]
        for index, entry in enumerate(entries, 1):
            parents = parents[:entry["level"]]
            ident = f"ebook-nav-{index}"
            while ident in existing:
                ident += "-new"
            existing.add(ident)
            point = element(doc, N, "navPoint", id=ident, playOrder=index)
            parents[-1].appendChild(point)
            label = element(doc, N, "navLabel")
            label.appendChild(element(doc, N, "text", entry["label"]))
            point.appendChild(label)
            point.appendChild(element(doc, N, "content", src=relative(name, entry["file"], entry["anchor"])))
            parents.append(point)
        head = nodes(doc, N, "head")[0]
        depths = [n for n in nodes(head, N, "meta") if n.getAttribute("name") == "dtb:depth"]
        depth = depths[0] if depths else element(doc, N, "meta", name="dtb:depth")
        if not depths:
            head.appendChild(depth)
        depth.setAttribute("content", str(max(e["level"] for e in entries)))
        book.store(name)


def rewrite(book, output, toc=None, css=None):
    if output.resolve() == book.path.resolve() or output.exists() or output.with_suffix(".report.json").exists():
        raise ValueError("Choose a new output path; originals and existing outputs are never overwritten")
    if not toc and not css:
        raise ValueError("Choose --toc and/or --css")
    if any(name in book.files for name in ("META-INF/encryption.xml", "META-INF/signatures.xml")):
        raise ValueError("Encrypted/obfuscated or signed EPUB needs separate handling; no rewrite performed")
    if any(n.hasAttribute("xml:base") or (n.namespaceURI == H and n.localName == "base")
           for name in book.files if name.endswith((".xhtml", ".opf")) for n in book.doc(name).getElementsByTagName("*")):
        raise ValueError("Base URI overrides require manual handling")
    original = dict(book.files)
    bodies = {name: content(nodes(book.doc(name), H, "body")[0]) for name in book.reading_files()}
    if toc:
        update_toc(book, checked_entries(book, json.loads(toc.read_text(encoding="utf-8"))))
    if css:
        fixed = any(n.getAttribute("property") == "rendition:layout" and content(n).strip() == "pre-paginated"
                    for n in nodes(book.package, O, "meta"))
        fixed |= any("rendition:layout-pre-paginated" in n.getAttribute("properties").split() for n in nodes(book.spine, O, "itemref"))
        if fixed:
            raise ValueError("Fixed-layout content cannot be converted by applying reflow CSS")
        css_data = css.read_bytes()
        if b"url(" in css_data.lower() or b"@import" in css_data.lower():
            raise ValueError("CSS resource imports need explicit resource packaging; use a self-contained stylesheet")
        item = book.add_item("ebook-reflow", ".css", "text/css")
        css_name = book.item_path(item)
        book.files[css_name] = css_data
        for name in book.reading_files():
            doc = book.doc(name)
            nodes(doc, H, "head")[0].appendChild(element(doc, H, "link", rel="stylesheet", type="text/css", href=relative(name, css_name)))
            book.store(name)
    if book.version3:
        metadata = nodes(book.package, O, "metadata")[0]
        modified = [n for n in nodes(metadata, O, "meta") if n.getAttribute("property") == "dcterms:modified"]
        meta = modified[0] if modified else element(book.package, O, "meta", property="dcterms:modified")
        if not modified:
            metadata.appendChild(meta)
        for child in list(meta.childNodes):
            meta.removeChild(child)
        meta.appendChild(book.package.createTextNode(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    book.store(book.opf)
    for name, before in bodies.items():
        if content(nodes(book.doc(name), H, "body")[0]) != before:
            raise ValueError(f"Body text changed during navigation/style edit: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in book.files.items():
            if name != "mimetype":
                archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    final = Book(output)
    report = audit(final)
    body_preserved = all(content(nodes(final.doc(name), H, "body")[0]) == before for name, before in bodies.items())
    unchanged = [name for name in original if original[name] == book.files[name]]
    resources_preserved = all(final.files[name] == original[name] for name in unchanged)
    if not body_preserved or not resources_preserved:
        report["errors"].append("Round-trip content/resource preservation failed")
        report["status"] = "FAIL"
    report.update(source_sha256=book.sha256, body_text_preserved=body_preserved,
                  unedited_resources_preserved=resources_preserved,
                  changed_files=[name for name, data in book.files.items() if original.get(name) != data])
    save_json(output.with_suffix(".report.json"), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "outline", "rewrite"):
        cmd = sub.add_parser(command)
        cmd.add_argument("epub", type=Path)
        cmd.add_argument("--output", type=Path, required=True)
        if command == "rewrite":
            cmd.add_argument("--toc", type=Path)
            cmd.add_argument("--css", type=Path)
    args = parser.parse_args()
    try:
        book = Book(args.epub)
        if args.command == "rewrite":
            report = rewrite(book, args.output, args.toc, args.css)
        else:
            report = audit(book) if args.command == "audit" else outline(book)
            save_json(args.output, report)
        print(json.dumps({"output": str(args.output), "status": report.get("status", "CANDIDATE_OUTLINE")}, ensure_ascii=False))
        return 2 if report.get("errors") else 0
    except (ValueError, KeyError, IndexError, OSError, zipfile.BadZipFile, ExpatError) as exc:
        if args.command == "audit" and not args.output.exists():
            save_json(args.output, {"status": "FAIL", "epub": str(args.epub), "errors": [str(exc)],
                                   "scope": "Package could not be fully inspected."})
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
