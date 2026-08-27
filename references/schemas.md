# Intermediate schemas

Use UTF-8. Write JSON atomically and JSONL one object per line. Stable IDs must survive retries and rebuilding.

## Project configuration

`project.json` owns book-specific choices: source path/format, target metadata, translator and optional reviewer model/options, OCR backend/interpreter/thresholds, pilot selection, revision limit, knowledge files, sections, and output name. Configured models and tools are the project allowlist; adding or substituting one requires user authorization.

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
