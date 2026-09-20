# Mathematical notation in book translation

Apply this route to books with substantial mathematical notation. PDF text extraction is a search aid: it frequently flattens fractions, summation limits, matrices, superscripts, subscripts, and multi-line equations. The rendered source page is the authority.

## Source contract

Before translation, inventory displayed equations with stable equation IDs or page/block anchors and equation numbers where present. Keep source page crops or a page-range reference, the extracted text, and a `verified` / `ambiguous` transcription status. Record symbol uncertainty explicitly. Separate prose, captions, displayed equations, and figure labels; do not join lines across a displayed equation during paragraph reconstruction. Keep equation-bearing text attached to its surrounding semantic block by an anchor so later layout changes cannot silently move it.

If an equation cannot be read from the text layer, inspect the rendered page at sufficient resolution and transcribe it to LaTeX or MathML. Do not derive a plausible equation from surrounding prose. Preserve the author's notation, including whether a function uses square or round brackets. Keep original equation numbering and references. Never silently normalize variable case, bold/vector style, Greek letters, subscripts, superscripts, hats/bars, transpose, derivative notation, units, or summation bounds.

## Translation and external handoff

Translate explanatory prose and math vocabulary; carry mathematical expressions unchanged in meaning. Give an external translator the source page reference and mark uncertain extracted formulas as non-authoritative. Ask for displayed equations as standalone math blocks with their original labels and inline expressions as inline math. Maintain per-block/page identity and source hashes so returned text can be matched to the approved source snapshot. Treat formula labels and counts as a completeness check, never as proof of symbolic fidelity.

## Review and publication

First compare equation IDs and cross-references mechanically. Then source-check each displayed expression against the rendered original, focusing on fractions, limits, matrix shapes, multi-line alignment, exponents, signs, and delimiters. Sample inline expressions across every notation style and inspect all extraction-risk locations. Record corrections against equation IDs with old/new text and evidence. Render the target math in the intended manuscript or EPUB and visually inspect unusual layouts and narrow viewport behavior. Mark unresolved symbol readings as blocking rather than publishing a guess.
