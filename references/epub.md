# EPUB input and output

For EPUB input, read `META-INF/container.xml`, the OPF manifest/spine, and navigation documents. Extract text from XHTML nodes while preserving element structure, inline emphasis, links, note semantics, IDs, and resource positions. Use `href` plus a stable node locator as provenance.

Reflowable EPUB normally needs no page-boundary reconstruction. Fixed-layout or image-only EPUB routes through layout/OCR handling. Record `META-INF/encryption.xml`; do not bypass DRM.

For EPUB output, generate EPUB 3 with valid language/metadata, hierarchical nav, spine order, stable note/visual anchors, responsive images, and accessible alt text. Keep print page numbers out of the TOC unless requested. Build from approved intermediate files so styling changes do not invoke translation again.

Validate every internal `href` and `src`, parse all XML/XHTML, confirm visual/note inventories, and render representative content before delivery.
