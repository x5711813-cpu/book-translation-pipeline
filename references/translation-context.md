# Translation context and knowledge baselines

Use this reference for narrative, literary, biographical, historical, game/rule, or terminology-dense books. The objective is reliable disambiguation, not a larger undifferentiated prompt.

## Project knowledge baseline

Keep project-specific knowledge under `shared/` and version it independently from the reusable skill:

- `glossary.json`: approved source term, target term, context, forbidden variants, evidence, and status.
- `entities.json`: people, aliases, titles, gender or pronoun evidence where relevant, relationships, places, organizations, and first occurrence.
- `style-guide.md`: audience, register, narrative perspective, dialogue policy, language-pair decisions, punctuation, and content-type rules.
- `decisions.json`: ambiguous or conditional choices with evidence, reason, affected blocks, and required back-scan.
- `continuity.json`: bounded section/chapter summaries and unresolved references; never treat a generated summary as source evidence.

Model-extracted entries are proposals until source-checked or user-approved. Do not turn a guessed entity, relationship, gender, historical identity, or conventional translation into an approved fact.

## Context package

For each target block, provide only relevant context:

1. the target block and bounded neighboring source text;
2. the previous approved target-language block when available;
3. the current section's continuity summary;
4. glossary and entity entries whose source forms or aliases occur in the local context;
5. the style rule for the block kind.

Hash the exact package. A change to neighbors, approved translation context, glossary, entity data, style guide, or continuity summary makes the cached result stale.

Long context is not a substitute for selection. For entity-dense books, search all occurrences of an ambiguous name or alias and adjudicate it before approving the entry. Keep unresolved ambiguity visible rather than forcing one translation globally.

## Language-pair and genre risks

Record only risks relevant to the project. Examples include omitted subjects and gendered pronouns, tense/aspect mapping, kinship distinctions, aliases, abbreviations, titles that resemble common nouns, culturally established translations, and names that collide across places or people.

For literary work, separate fidelity correction from chapter-level literary polishing. A polish may change syntax, rhythm, and diction but must not change entities, actions, negation, conditions, degree, time, numbers, quotations, or foreshadowing. Re-run fidelity review after polishing.

## Pilot acceptance

The pilot must cover ordinary prose plus representative risks such as entity density, dialogue, notes, a difficult seam, structured content, or an unusual layout. Record counts of confirmed omission, addition, reversal, entity/pronoun, terminology, numeric, structural, and style failures. Set the project's acceptance thresholds before full production; do not declare success from fluency alone.

Use deterministic checks for exact invariants and human or independently configured contextual review for meaning. A reviewer using the same model is prompt-isolated, not model-independent; record that distinction.
