# 0015 — Export the full plan as CSV (every group, every file)

- **Priority**: Medium
- **Batch**: report
- **Depends**: —
- **Files**: `src/media_dedup/report/writer.py`, `src/media_dedup/report/` (new `csv_export.py`), `src/media_dedup/services/reporting.py`, `README.md`, `README_FR.md`

## Context

The HTML report caps the groups it lists. Users who want to check everything, or to compare
with another tool (0013), need the whole plan in a format they can open in Excel, filter and
sort.

## Proposal

- `plan.csv` next to `report.html` in each report folder: one row per file, with group number,
  SHA-256, size, action (`keep` / `delete` / `protected` / `broken`), host path, folder,
  modification date, and keep reason (0012).
- Excel-friendly: UTF-8 with BOM, and a `;` separator when the locale is French (Excel's list
  separator follows the regional settings). Document the choice.
- Link to it from the report and from `index.html`.

## Acceptance

- [ ] Every file of the plan appears exactly once, even beyond the HTML cap.
- [ ] Opens correctly in Excel (FR and EN), accents included.
- [ ] README + README_FR mention it; tests on a demo tree.
