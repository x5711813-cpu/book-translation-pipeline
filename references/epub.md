# EPUB input and output

For standalone ebook proofreading, TOC rebuilding, or typography changes, follow [ebook-maintenance.md](ebook-maintenance.md). Use its `ebook_tool.py` commands on existing EPUBs without creating a translation project. The basic translation builder emits section-level navigation; when a reviewed multi-level TOC is required, run `outline`, review the heading plan, then `rewrite --toc` on the built EPUB and audit that final file.

For EPUB input, read `META-INF/container.xml`, the OPF manifest/spine, and navigation documents. Extract text from XHTML nodes while preserving element structure, inline emphasis, links, note semantics, IDs, and resource positions. Use `href` plus a stable node locator as provenance.

Reflowable EPUB normally needs no page-boundary reconstruction. Fixed-layout or image-only EPUB routes through layout/OCR handling. Record `META-INF/encryption.xml`; do not bypass DRM.

For EPUB output, generate EPUB 3 with valid language/metadata, hierarchical nav, spine order, stable note/visual anchors, responsive images, and accessible alt text. Keep print page numbers out of the TOC unless requested. Build from approved intermediate files so styling changes do not invoke translation again.

Validate every internal `href` and `src`, parse all XML/XHTML, confirm visual/note inventories, and render representative content before delivery.
