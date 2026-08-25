# Workflow

## 1. Preflight and input routing

Create a project, hash the source, and inspect its structure. Classify it as `pdf-text`, `pdf-scan`, `pdf-mixed`, `epub-reflowable`, or `epub-fixed`. Inventory chapters, notes, bibliography, index, figures, tables, maps, rotated pages, multi-column pages, and blank/front-matter pages. Record decisions in project files.

## 2. Visuals before prose

Build `visuals/visuals.json` before translation. Extract originals, detect multi-page tables, and replace flattened visual text in the prose stream with stable placeholders. Keep the true placement anchor even when a visual interrupts a paragraph. Do not localize labels until the pilot terminology is approved.

## 3. Reconstruct the source book

Extract pages with source coordinates where available. Remove repeated running-header/footer candidates, repair line-end hyphenation, restore reading order, and join paragraphs that cross physical pages. Store semantic blocks in JSONL with stable IDs and page/bounding-box provenance.

Use deterministic boundary rules first. Ask the local model only about ambiguous boundaries. Preserve its decision and reasoning as structured data. Translate only after no blocking source boundary remains.

## 4. Pilot and terminology lock

Translate 20 pages by default, including ordinary prose, at least one boundary, a note-heavy page, and a visual if available. Review completeness, tone, names, terminology, quotations, and reference handling. Update project terminology and prompts without overwriting the pilot's evidence.

## 5. Chapter translation

Schedule by chapter and translate by semantic block. Supply previous/next context for coherence but require output only for the current block. Use distinct policies for prose, notes, bibliography, and index. Cache by source hash, model, prompt hash, and terminology hash.

## 6. Review and bounded revision

Run a separate review request returning JSON. Check omissions, additions, reversals, names, numbers, notes, contamination, and terminology. Preserve the original translation before revision. Retry only failed blocks, at most the configured number of rounds.

After block review, assemble a review manuscript and run a second pass over paragraph seams and chapter context. Generate deterministic candidates first with `scripts/audit_manuscript.py`, then use a local model to adjudicate contextual issues. The script's English, number, semicolon, quotation, and punctuation findings are candidates, not automatic replacements. Read [publication-proofreading.md](publication-proofreading.md) for quotation, punctuation, note, paragraph, and end-matter checks.

## 7. Visual localization

Translate captions, axes, legends, table headers, annotations, and units. Prefer data-driven redraw for charts/tables, text-layer replacement for maps/diagrams, and original images plus translated captions for photographs. Never infer missing data. Produce a contact sheet for review.

## 8. Publication assembly

Assemble chapters from approved blocks, apply replayable repair records, link notes bidirectionally, create a hierarchy-aware TOC, make index entries separate paragraphs, include a visual index, and generate EPUB 3 resources. Print page numbers are excluded unless requested.

## 9. Audit and delivery

Run structural, link, continuity, visual-count, note-count, contamination, number, punctuation-candidate, heading, end-matter, and rendering checks. Source-check every accepted late repair, rebuild from intermediates, and rerun the full audit on the rebuilt artifact. Deliver the EPUB, an editable Markdown manuscript, QA/adjudication reports, hashes, and a concise disclosure of unresolved or approximated items.
