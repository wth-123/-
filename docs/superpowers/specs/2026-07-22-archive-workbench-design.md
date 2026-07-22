# Archive Workbench UI Design

## Goal

Reshape the local document-review page into a compact archive workbench for
internal reviewers. The page must keep the existing upload, processing,
review, retry, and export API contracts unchanged.

## Visual System

- Paper gray `#F2F3EF`: page canvas.
- Ink green `#183B3A`: titles, navigation, and primary actions.
- Archive white `#FFFFFF`: operational surfaces and editable fields.
- Vermilion `#C55438`: failure and reprocess emphasis.
- Use a serif display role for the page title, a sans-serif body role, and a
  monospaced utility role for filenames, counts, and status details.

## Layout

- A compact top bar contains the product label, batch metadata, and the export
  action.
- A second operational strip groups upload and processing controls with live
  counts for processed, pending, and failed items.
- The review surface is a full-width, dense table on desktop. Each row starts
  with a narrow vertical archive tag whose color represents review state.
- The source cell carries the filename, type, and processing status. Editable
  classification, summary, review state, notes, and save action remain in the
  row.
- At narrow widths, table rows become stacked archive records so controls stay
  readable and no horizontal scrolling is required.

## Interaction

- Upload and process actions retain their existing endpoints and show concise
  progress text in the operational strip.
- Saving a row preserves the existing PATCH contract and gives a short inline
  confirmation without moving the table.
- Selecting `reprocess` visually marks a row with the vermilion archive tag;
  processing keeps the same retry behavior.
- Empty state directs the reviewer to upload a supported document type.

## Accessibility and Boundaries

- Visible keyboard focus, semantic buttons and labels, and reduced-motion
  support are required.
- API responses must continue to omit raw and redacted source text.
- This work changes only the `GET /` presentation. Parsing, masking, model
  adapters, storage, and export behavior remain unchanged.

## Verification

- Preserve the existing API test suite.
- Add a lightweight response test for archive-workbench landmarks and action
  labels.
- Check the rendered page at desktop and mobile widths before completion.
