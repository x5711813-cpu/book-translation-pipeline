# OCR routing

Use OCR only on pages whose text layer is absent or materially incomplete. Cache all results.

The bundled script supports RapidOCR through `rapidocr_onnxruntime` and renders PDF pages through `pypdfium2`. It runs locally after installation. Configure the dedicated OCR Python interpreter in `project.json`.

## Economical mode

1. Render at 250–320 DPI equivalent.
2. Run local OCR on full pages.
3. Store text, boxes, confidence, and page images.
4. Send only recovered text to the translation model.
5. Crop and visually inspect low-confidence or complex regions; do not send full pages to a vision model by default.

OCR text recognition does not guarantee correct reading order. Multi-column pages, marginalia, footnotes, tables, and decorative layouts require region/order checks. Exclude visual/table areas from prose OCR and process them separately.

Do not equate high mean confidence with completeness. Detect suspicious gaps between otherwise regular body-text lines and visually sample pages even when every recognized line has a high score.

Mark a region `BLOCKED` instead of guessing when a name, number, formula, citation, or table cell is unreadable.
