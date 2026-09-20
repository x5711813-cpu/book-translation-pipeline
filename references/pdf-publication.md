# PDF publication: navigation, mathematics, and illustrations

Use when the user requests a fixed-page PDF edition or its repair. Reuse the approved manuscript and assets; layout work does not imply another translation pass. Keep book-specific equation overrides, counts, fonts, device dimensions and source paths in the project, not in skill defaults.

## Semantic preparation

Review the heading inventory before rendering. Separate real chapters/sections from code comments, captions, figure-label translations, running heads, and translator instructions. Markdown `#` is not evidence of chapter status. Confirm duplicate split chapter headings against their surrounding source. In a verified numeric scheme, validate both section depth and the actual parent number. Allow documented parts, unnumbered headings and appendix schemes.

Keep code/comment translations as ordinary prose or code when they remain useful; do not delete them merely to clean the TOC. Remove redundant editorial label lists or duplicate table transcriptions only after confirming the retained figure/table carries their information. Record removals by stable source ID. Move a caption with its complete inline math children; flattening it to text destroys notation.

## Device layout

Record physical dimensions and aspect ratio, body font size, margins and paragraph-class indentation. If only diagonal is known, state the assumed aspect ratio. Pixels = inches × device ppi; vector PDF content has no fixed image ppi. Check raster figures at their placed size, not only the source rendering dpi. A 300 dpi extraction cannot recover detail absent from a scanned source.

Use the supplied style reference as evidence for typography. Keep figure/caption groups together when they fit; check oversized groups and narrow tables explicitly. Embed the used fonts and inspect actual final pages for missing glyphs, low contrast, clipping and header/footer collisions. Do not describe desktop rendering as a physical-device test.

## Mathematics

Read [math-and-formulas.md](math-and-formulas.md). Retain stable math IDs, original equation numbers and TeX/MathML sources. For EPUB, use valid MathML namespaces and package declarations where supported. When parsing text/html, serialize real `<math>` elements; prefixed XML tags such as `<m:math>` can be treated as unknown HTML instead of MathML.

PDF may use a verified TeX renderer to produce vector glyphs while the EPUB retains MathML. Record the conversion and check multiline alignment, matrices, cases, limits and tags. Do not claim the PDF itself preserves MathML semantics merely because its source does.

Inspect the installed renderer's DOM before selecting classes. KaTeX releases can expose `katex-base` / `katex-tag` instead of older `base` / `tag`; a selector that matches nothing can falsely report no overlap. Wait for fonts and images before measuring. Check equation-body versus tag bounding boxes as well as page-width overflow. For centered formulas with a right-aligned tag, reserve space on both sides (approximately body width + 2 × (tag width + gap)); body + one tag width can still overlap. Re-measure after fitting.

Prefer meaningful multiline breaks over excessive shrinking. Preserve every term, operator and grouping in reflow overrides and source-check the changed expressions. Record minimum rendered size and inspect the smallest formulas at target viewing scale. Counts and parsing success cannot establish symbolic accuracy.

## SVG and tables

Prefer author-provided vectors where authorized. Localize editable labels while preserving mathematical symbols, geometry and data. Text may be converted to paths; a search yielding no English text does not prove full translation. Visually inspect axes, legends and boundaries. A loaded image with a valid naturalWidth can still crop tick labels inside its SVG viewBox. Repair the canvas extent or layout based on visible evidence without stretching or changing data.

For recreated tables, verify every row, column, unit and symbol against the source, and include one authoritative table plus its caption. Follow the user's approval requirement for newly generated images; deterministic table recreation is a separate workflow when authorized. Keep pending assets out of the final build until required approval arrives.

## Navigation and final validation

- Build printed TOC links and nested bookmarks from the same reviewed outline and final pagination. Do not infer correctness from counts alone: read back labels, parentage, order, destinations and default open/closed state from the output PDF.
- PDF collapse behavior belongs to the bookmark panel, not static printed TOC pages. Verify actual serialized outline child counts/state; a library's `is_open=False` flag may not produce the intended result. Verify link destinations resolve to real page objects rather than trusting annotation construction arguments.
- Chapter hierarchy must survive later corrections; regenerate page numbers and all dependent targets when pagination changes. Preserve the earlier deliverable for rollback or record replacement hashes.
- Source index and bibliography back-reference page numbers need a verified mapping to new pages. If unavailable, label them as original-page locators in the book and delivery note; never imply they address the new PDF.
- Final gates: semantic TOC review, valid links, correct parents, preserved figure/equation inventory, embedded fonts, no measured formula/tag overlap or page overflow, and visual review of the delivered bytes. Inspect unusual layouts and any changed region; a parser PASS is not publication PASS.
- Record actual checks, render samples, unresolved limitations, final page count/size and hash. Recompute delivery notes from final reports rather than retaining earlier hard-coded counts. Report full textual review separately from layout QA.
