# Workflow

## 1. Preflight and input routing

Create a project, hash the source, and inspect its structure. Classify it as `pdf-text`, `pdf-scan`, `pdf-mixed`, `epub-reflowable`, or `epub-fixed`. Inventory chapters, notes, bibliography, index, figures, tables, maps, rotated pages, multi-column pages, and blank/front-matter pages. Record decisions in project files.

## 2. Visuals before prose

Build `visuals/visuals.json` before translation. Extract originals, detect multi-page tables, and replace flattened visual text in the prose stream with stable placeholders. Keep the true placement anchor even when a visual interrupts a paragraph. Do not localize labels until the pilot terminology is approved.

## 3. Reconstruct the source book

Extract pages with source coordinates where available. Remove repeated running-header/footer candidates, repair line-end hyphenation, restore reading order, and join paragraphs that cross physical pages. Store semantic blocks in JSONL with stable IDs and page/bounding-box provenance.

Use deterministic boundary rules first. Ask the configured model only about ambiguous boundaries. Preserve its decision and reasoning as structured data. After structural and completeness review, freeze the blocks with `scripts/approve_source.py`. Translate only from that immutable revision and only after no blocking source boundary remains. The completeness audit should not reuse the extractor's filtering and ordering logic wholesale; otherwise both paths can omit the same material.

## 4. Knowledge baseline and pilot

Create versioned project knowledge under `shared/`: glossary, entities, style guide, decisions, and bounded continuity summaries. Treat model-extracted terms and identities as proposals until source-checked. For narrative or entity-dense books, read [translation-context.md](translation-context.md).

Translate 20 actual source pages by default, or explicit pilot block IDs for EPUB and other pageless input. Include ordinary prose plus representative risks such as a difficult boundary, entity-dense or dialogue material, a note-heavy passage, structured content, and a visual if available. Record issue counts and acceptance thresholds before full production. Update project knowledge and prompts without overwriting the pilot evidence.

## 5. Chapter translation

Schedule by chapter and translate by semantic block. Supply a hashed context package—bounded neighboring source, previous approved translation, relevant glossary/entities, style guide, and section continuity—but require output only for the current block. Use distinct policies for prose, headings, notes, bibliography, index, captions, tables, and lists. Cache by approved source revision, source/context/knowledge hashes, exact model options, and prompt hashes.

## 6. Review and bounded revision

Run a separate review request returning structured JSON with issue category, severity, source/translation evidence, and explanation. Check omissions, additions, reversals, entities and pronouns, numbers, notes, contamination, and terminology. Use a separately configured reviewer model when the project requires model independence; otherwise record that independence is prompt-only. Preserve the full revision chain. Retry only failed blocks, at most the configured number of rounds.

After block review, assemble a review manuscript and run a second pass over paragraph seams and chapter context. Generate deterministic candidates first with `scripts/audit_manuscript.py`, then use a local model to adjudicate contextual issues. The script's English, number, semicolon, quotation, and punctuation findings are candidates, not automatic replacements. Read [publication-proofreading.md](publication-proofreading.md) for quotation, punctuation, note, paragraph, and end-matter checks.

## 7. Visual localization

Translate captions, axes, legends, table headers, annotations, and units. Prefer data-driven redraw for charts/tables, text-layer replacement for maps/diagrams, and original images plus translated captions for photographs. Never infer missing data. Produce a contact sheet for review.

## 8. Publication assembly

Assemble chapters from approved blocks, apply replayable repair records, link notes bidirectionally, create a hierarchy-aware TOC, make index entries separate paragraphs, include a visual index, and generate EPUB 3 resources. Print page numbers are excluded unless requested.

## 9. Audit and delivery

Run approval-revision, structural, link, continuity, visual-count, note-count, contamination, number, punctuation-candidate, heading, end-matter, and rendering checks. Source-check every accepted late repair, rebuild from intermediates, and rerun the full audit on the rebuilt artifact. When auditability or user review matters, keep the bilingual block record as the canonical translation master and mechanically derive the Chinese manuscript from approved records. Deliver the requested artifacts, QA/adjudication reports, hashes, and a concise disclosure of unresolved or approximated items.
