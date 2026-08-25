# Quality gates

The final status is `PASS` only when every applicable blocking gate passes.

## Source and OCR

- Source hash and detected format recorded; all planned pages/spine items accounted for.
- OCR confidence, low-confidence regions, suspicious line gaps, and text-region coverage recorded; high confidence alone is not a completeness guarantee.
- Multi-column order, notes, rotated pages, and table regions checked.
- No blocking illegible text or guessed numeric/tabular content.

## Structure and continuity

- Figures/tables isolated before prose translation.
- No unresolved source boundaries, sentence fragments, or duplicated seam text caused by batching.
- Running headers, footers, and print page labels absent from publication text.
- Headings and section order match the approved structure.
- Paragraph reconstruction is checked after assembly, not only per extraction block; no duplicated seam phrase, swallowed connective text, or false paragraph/list boundary remains.
- Front matter, first section, final chapter, blockquotes, and every unusual layout class have explicit rendered spot checks.

## Translation

- Every required block has a current translation matching its source hash.
- Independent review passed or unresolved issues are disclosed.
- No prompt, reasoning, refusal, or code-fence contamination.
- Numbers, dates, citations, note markers, names, and glossary terms checked.
- No untranslated source-language prose, raw tags, replacement/zero-width characters, OCR/page-label debris, or unexplained ellipses remain.
- Every accepted external-review correction is source-adjudicated and replayable; the old bad pattern is absent from the rebuilt output.

## Chinese publication text

- Eligible prose paragraphs have valid terminal punctuation and no abnormal leading punctuation.
- Quotation levels, closing marks, sentence punctuation, and sentence-final note-marker placement follow one declared house style.
- Semicolon and paragraph-boundary candidates have been reviewed in context; regex absence alone does not satisfy this gate.
- Number candidates are classified by role so months, dates, units, currencies, page references, regnal numbers, lists, and index locators are not mistaken for notes.
- Heading numbering and hierarchy are consistent across chapters; headings are not fused into prose.
- First-line indentation is correct by paragraph class, including exceptions for headings, blockquotes, lists, notes, and project-specific first-paragraph styling.
- The manuscript checker has no `error` findings. Every remaining `warning` or `style` finding is either resolved or recorded with source-based adjudication; use `--strict` only after legitimate exceptions have been explicitly handled.

## Notes, index, and visuals

- Note references and bodies are linked and count-consistent.
- Note IDs are unique; no missing targets, duplicate definitions, unreferenced bodies, body-note contamination, or bibliography fragments in prose remain.
- Index entries are one entry per paragraph and retain cross-references.
- Pope/office-holder lists, chronologies, tables, and indexes pass structure-specific numeric and column audits.
- Visual inventory count matches localized assets.
- Captions, axes, legends, table headers, internal annotations, and units are localized.
- Visual IDs, alt text, image files, and visual-index links resolve.

## EPUB

- `mimetype` is first and stored uncompressed.
- Container, OPF, spine, nav, XHTML, href, and src targets validate.
- TOC has no print page numbers unless requested.
- EPUB opens after a clean rebuild from intermediate files.
- Representative pages and every unusual layout class are visually inspected.
- The final Markdown/EPUB artifacts—not an earlier build—match the delivered audit hashes.
- Build report and SHA-256 are delivered.
