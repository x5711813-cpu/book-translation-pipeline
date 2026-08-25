# Intermediate schemas

Use UTF-8. Write JSON atomically and JSONL one object per line. Stable IDs must survive retries and rebuilding.

## Project configuration

`project.json` owns book-specific choices: source path/format, target metadata, model endpoint/name/options, OCR backend/interpreter/thresholds, pilot size, revision limit, terminology, sections, and output name.

## Source manifest

`source/source-manifest.json` records source SHA-256, detected format, page or spine counts, extraction quality, encryption flags, and tool versions.

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
  "cache_key": "...",
  "model": "local-model",
  "prompt_sha256": "...",
  "review": {"status": "PASS", "issues": [], "missing": ""},
  "metrics": {"seconds": 12.1, "prompt_tokens": 900, "output_tokens": 420}
}
```

## Boundary and visual records

`repairs/boundary-decisions.json` stores deterministic signals, join/split decision, method, and confidence. `repairs/boundary-rewrites.json` stores exact anchors, replacements, and reasons so the build is replayable.

Use separate replayable records for document flow, heading structure, note overrides, publication layout, and external-review adjudication when those concerns arise. A repair record should identify stable block/note IDs, old and new text or structural action, source evidence, reason, reviewer, and the source/output hash to which it applies. Exact replacements should either be idempotent or fail loudly when their expected anchor is absent; a clean rebuild must not apply the same insertion twice.

Store whole-book proofreading candidates separately from accepted repairs. Each candidate should contain location, category, surrounding context, evidence, proposed action, confidence, and status (`PENDING`, `ACCEPTED`, `MODIFIED`, `REJECTED`, or `ALREADY_FIXED`).

`visuals/visuals.json` records stable ID, kind, source pages or EPUB resource, crop/rotation, chapter placement, source/target caption, localization method, asset files, alt text, and status. Do not place copyrighted book content in the reusable skill.
