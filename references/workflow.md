# Workflow

This is the translation workflow. For an existing ebook that only needs proofreading, a TOC, or formatting, use [ebook-maintenance.md](ebook-maintenance.md) instead; do not require a translation pilot or regenerate approved translations.

## 1. Preflight and input routing

Create a project, hash the source, and inspect its structure. Classify it as `pdf-text`, `pdf-scan`, `pdf-mixed`, `epub-reflowable`, or `epub-fixed`. Inventory chapters, notes, bibliography, index, figures, tables, maps, rotated pages, multi-column pages, and blank/front-matter pages. Record decisions in project files.

For a requested edition update, verify the designated author's release or supplied snapshot, record its version/hash, and compare semantic blocks and visual identities rather than page offsets alone. Map additions, deletions, moved sections, equations and figures; reuse translations only where source and context remain valid. An older translation or illustration is a comparison witness, not authority over the chosen edition. Keep physical PDF pages, printed pages, old-edition pages and approximate matches explicitly distinct; never relabel an approximate locator as exact.

## 2. Visuals before prose

Build `visuals/visuals.json` before translation. Extract originals, detect multi-page tables, and replace flattened visual text in the prose stream with stable placeholders. Keep the true placement anchor even when a visual interrupts a paragraph. Do not localize labels until the pilot terminology is approved.

For mathematical books, also inventory displayed equations, inline notation at extraction-risk locations, and equation references before prose translation. Follow [math-and-formulas.md](math-and-formulas.md); equation images are source evidence, not prose to be guessed from a flattened text layer.

## 3. Reconstruct the source book

Extract pages with source coordinates where available. Remove repeated running-header/footer candidates, repair line-end hyphenation, restore reading order, and join paragraphs that cross physical pages. Store semantic blocks in JSONL with stable IDs and page/bounding-box provenance.

Use deterministic boundary rules first. Ask the configured model only about ambiguous boundaries. Preserve its decision and reasoning as structured data. After structural and completeness review, freeze the blocks with `scripts/approve_source.py`. Translate only from that immutable revision and only after no blocking source boundary remains. The completeness audit should not reuse the extractor's filtering and ordering logic wholesale; otherwise both paths can omit the same material.

Before reconstruction, configure `sections` using [schemas.md](schemas.md#sections). Resolve unmatched page ranges before approving the source.

For offline/manual review, list ambiguous boundaries with `python scripts/resolve_boundaries.py <project> --dry-run`, inspect the original pages, then record an evidence-based decision:

```text
python scripts/resolve_boundaries.py <project> --decide page-0001-to-0002=SPLIT --reason "Original page shows a new paragraph"
python scripts/build_blocks.py <project>
python scripts/approve_source.py <project>
```

`--decide KEY=JOIN|SPLIT` can be repeated; `--reason` is required and applies to those decisions. All keys are validated before writing. Add `--dry-run` to preview without changes. Manual mode needs no model and does not process other pending boundaries. Decisions retain `method: manual` and their evidence after rebuilding. A model run also retains its method and timing. With no pending boundaries, the resolver exits successfully without requiring a model. The existing `build_blocks.py --accept-ambiguous-splits` is a bulk split override, suitable only after verifying that all pending seams should be split.

## 4. Knowledge baseline and pilot

Create versioned project knowledge under `shared/`: glossary, entities, style guide, decisions, and bounded continuity summaries. Treat model-extracted terms and identities as proposals until source-checked. For narrative or entity-dense books, read [translation-context.md](translation-context.md).

Translate 20 actual source pages by default, or explicit pilot block IDs for EPUB and other pageless input. Include ordinary prose plus representative risks such as a difficult boundary, entity-dense or dialogue material, a note-heavy passage, structured content, and a visual if available. Record issue counts and acceptance thresholds before full production. Update project knowledge and prompts without overwriting the pilot evidence.

## 5. Chapter translation

Schedule by chapter and translate by semantic block. Supply a hashed context package—bounded neighboring source, previous approved translation, relevant glossary/entities, style guide, and section continuity—but require output only for the current block. Use distinct policies for prose, headings, notes, bibliography, index, captions, tables, and lists. Cache by approved source revision, source/context/knowledge hashes, exact model options, and prompt hashes.

### Offline handoff to an external translator

When the user chooses a translator that cannot communicate with this agent (for example Qoder), use a self-contained folder instead of assuming an API or live coordination. Include a task file, ordered manifest of stable block IDs and source hashes, source chunks with clearly separated read-only context, glossary/style rules, formula/figure placeholders, expected output paths and a completion checklist. Require translation of every assigned block, no invented completion of uncertain text, and a list of unresolved items. Record the engine/version as reported; unknown model identity remains unknown.

Use the approved pilot rules for the remaining batch. On return, match IDs and hashes, check missing/duplicate/stale outputs and chunk seams, then source-review the translation; a translator's “done” message is not acceptance. If the user excludes copyright/front-matter material from the handoff, scope and record that exclusion without deleting adjoining prose or automatically removing it from unrelated deliverables.

## 6. Review and bounded revision

Run a separate review request returning structured JSON with issue category, severity, source/translation evidence, and explanation. Check omissions, additions, reversals, entities and pronouns, numbers, notes, contamination, and terminology. Use a separately configured reviewer model when the project requires model independence; otherwise record that independence is prompt-only. Preserve the full revision chain. Retry only failed blocks, at most the configured number of rounds.

For equation-bearing blocks, compare the rendered source and target notation independently of prose review. Check every numbered equation and its cross-references, plus the risk-prone inline expressions identified during extraction. A matching equation number alone never proves the formula is correct.

After block review, assemble a review manuscript and run a second pass over paragraph seams and chapter context. Generate deterministic candidates first with `scripts/audit_manuscript.py`, then use a local model to adjudicate contextual issues. The script's English, number, semicolon, quotation, and punctuation findings are candidates, not automatic replacements. Read [publication-proofreading.md](publication-proofreading.md) for quotation, punctuation, note, paragraph, and end-matter checks.

## 7. Visual localization

Translate captions, axes, legends, table headers, annotations, and units. Prefer data-driven redraw for charts/tables, text-layer replacement for maps/diagrams, and original images plus translated captions for photographs. Never infer missing data. Produce a contact sheet for review.

## 8. Publication assembly

Assemble chapters from approved blocks, apply replayable repair records, link notes bidirectionally, create a hierarchy-aware TOC, make index entries separate paragraphs, include a visual index, and generate EPUB 3 resources. Print page numbers are excluded unless requested.

## 9. Audit and delivery

Run approval-revision, structural, link, continuity, visual-count, note-count, contamination, number, punctuation-candidate, heading, end-matter, and rendering checks. Source-check every accepted late repair, rebuild from intermediates, and rerun the full audit on the rebuilt artifact. When auditability or user review matters, keep the bilingual block record as the canonical translation master and mechanically derive the Chinese manuscript from approved records. Deliver the requested artifacts, QA/adjudication reports, hashes, and a concise disclosure of unresolved or approximated items.
