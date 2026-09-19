# Intermediate schemas

Use UTF-8. Write JSON atomically and JSONL one object per line. Stable IDs must survive retries and rebuilding.

## Project configuration

`project.json` owns book-specific choices: source path/format, target metadata, translator and optional reviewer model/options, OCR backend/interpreter/thresholds, pilot selection, revision limit, knowledge files, sections, and output name. Configured models and tools are the project allowlist; adding or substituting one requires user authorization.

### Sections

Configure PDF sections before building and approving blocks:

```json
"sections": [
  {"slug": "ch1", "label": "第一章", "start_page": 1, "end_page": 12, "kind": "prose"},
  {"slug": "ch2", "label": "第二章", "start_page": 13, "end_page": 24, "kind": "prose"}
]
```

- `slug`: required unique chapter identifier, using letters, digits, underscores or hyphens; begin with a letter or digit. Also assigns the source block's `section` during PDF extraction.
- `label`: required nonempty chapter title used in the EPUB and TOC.
- `start_page`, `end_page`: optional paired positive integers, inclusive physical PDF pages starting at 1. Ranges must not overlap. `pages` is not a supported alias.
- `kind`: optional block type assigned during extraction, default `prose` (other policies include `heading`, `note`, `bibliography`, `index`, `caption`, `table`, `list`).
- `source_section`: optional source block `section` selected for this output chapter; defaults to `slug`. Use when the output chapter slug differs from the source section.
- `block_ids`: optional explicit list of unique block IDs, overriding `source_section` selection. Source order is preserved. An empty list selects nothing and fails the empty-chapter check.

Unknown fields, invalid page ranges and duplicate slugs fail explicitly. Unmatched extracted blocks remain `unassigned` with a warning. EPUB assembly requires every current block to appear in exactly one nonempty chapter; unknown IDs, omissions and duplicate assignments fail before writing output. An empty `sections` list builds one chapter containing all blocks.

Changing page ranges or boundary decisions can change block IDs. Rebuild, inspect and approve a new source revision before resuming translation. Translation rows outside the current source remain in `translations.jsonl` as history; build/audit reports list `orphan_translation_ids` and warn, while quality checks apply to current blocks. Existing source-revision and cache validity checks still apply; historical rows are never automatically deleted.

## Source manifest

`source/source-manifest.json` records source SHA-256, detected format, page or spine counts, extraction quality, encryption flags, and tool versions.

`source/approved/rNNN/approval.json` records the immutable `source_revision`, blocks-file SHA-256, block count, approval time, and source manifest hash. Its adjacent `blocks.jsonl` is the only valid translation input for that revision. Editing working blocks requires a new approved revision; never rewrite an approved directory.

## Semantic block

```json
{
  "block_id": "chapter-03-block-0042",
  "section": "chapter-03",
  "kind": "prose",
  "source": "Complete source paragraph",
  "provenance": [{"page": 88, "bbox": null}, {"page": 89, "bbox": null}],
  "boundary_status": "READY",
  "source_sha256": "..."
}
```

For EPUB input, provenance uses `href` and a stable node locator instead of pages.

## Translation record

```json
{
  "block_id": "chapter-03-block-0042",
  "translation": "完整译文",
  "status": "PASS",
  "source_sha256": "...",
  "source_revision": "r001",
  "cache_key": "...",
  "model": "local-model",
  "prompt_sha256": "...",
  "context_sha256": "...",
  "knowledge_sha256": "...",
  "reviewer_model": "review-model",
  "review_prompt_sha256": "...",
  "review_independence": "model or prompt-only",
  "review": {"status": "PASS", "issues": []},
  "revisions": [],
  "metrics": {"seconds": 12.1, "prompt_tokens": 900, "output_tokens": 420}
}
```

## Shared knowledge

`shared/glossary.json`, `shared/entities.json`, `shared/decisions.json`, `shared/continuity.json`, and `shared/style-guide.md` are project-specific, versioned inputs. Proposed model output must remain distinguishable from approved entries. Conditional translations need context and evidence; forbidden variants and affected blocks support deterministic back-scans.

The exact selected subset sent with a block is its context package. Store its SHA-256 rather than assuming that a stable target block implies stable context.

## Boundary and visual records

`repairs/boundary-decisions.json` stores deterministic signals, join/split decision, method, and confidence. `repairs/boundary-rewrites.json` stores exact anchors, replacements, and reasons so the build is replayable.

Use separate replayable records for document flow, heading structure, note overrides, publication layout, and external-review adjudication when those concerns arise. A repair record should identify stable block/note IDs, old and new text or structural action, source evidence, reason, reviewer, and the source/output hash to which it applies. Exact replacements should either be idempotent or fail loudly when their expected anchor is absent; a clean rebuild must not apply the same insertion twice.

Store whole-book proofreading candidates separately from accepted repairs. Each candidate should contain location, category, surrounding context, evidence, proposed action, confidence, and status (`PENDING`, `ACCEPTED`, `MODIFIED`, `REJECTED`, or `ALREADY_FIXED`).

`visuals/visuals.json` records stable ID, kind, source pages or EPUB resource, crop/rotation, chapter placement, source/target caption, localization method, asset files, alt text, and status. Do not place copyrighted book content in the reusable skill.
