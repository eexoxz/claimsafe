# Report production notes

The report is a formal coursework document. Its presentation follows the user's supplied
FYP report: A4, one-inch margins, Times New Roman 12 pt, 1.5 body spacing and numbered
sections. The original FYP and distinction samples remain external references, not repository
content. No tourism text, sample-student text or old FYP figures are included.

`REPORT_DRAFT.md` is the editable text source. `report-assets/report-template.docx` is a
sanitised formatting template derived from a working copy of the user's reference. Its old
body, media, headers, comments and private content relationships were removed; only formatting
and empty note separators remain. Microsoft Word requires the note separator parts referenced
by the retained settings. Removing those parts causes an opening error.

`scripts/build_report.py` builds the DOCX through `scripts/build_report_docx.py`. The PDF is
exported from that DOCX by `scripts/export_report.ps1`, using native Microsoft Word. This
keeps editable and printable versions on one layout engine. Word refreshes SEQ captions,
the contents, figure/table lists and page numbers before export. Never replace this with an
independently typeset PDF while claiming that it validates the Word document.

Install `requirements-report.txt` in the chosen Python environment, then run:

```powershell
python scripts/build_report.py --export-pdf
```

Without Word, omit `--export-pdf`, open the generated DOCX in an editor, update its fields
and export it there. Default output is `.local/report/`; `--output-dir` chooses another
folder. Refresh the reviewed copies under `docs/report/` after the final rendering checks.

The 26 October revision contains approximately 3,890 main-report words before references,
abstract and appendices. This is an approximate source count, not a module ruling on which
elements count. The retained structure has five main security coursework sections. Body text is
primarily connected prose; tables compare permissions, risks and selected test outcomes.

The original 25 October test summary remains in `report-assets/test-summary.txt`. The
26 October rerun completed 45 tests in 20.056 seconds, with no failed assertions and no system
check issues. This duration is a test-run observation, not a performance measurement.
The code baseline remains d1086b5; report-only commits do not change the assessed app code.
Browser captures come from the earlier fictional walkthrough, not the rerun or a user study.

The current report still records incomplete HTTPS deployment, host protection and broader
manual/automated vulnerability assessment. Update its implementation, findings and conclusion
when that work is complete. The required Turnitin screenshot and official Generative AI
Declaration Form must be supplied for submission; the report acknowledgement does not
replace the form. Cover identity was carried from the user's own supplied report.

The 29 October style revision follows the supplied security samples' ordinary numbered
section convention (`1.0`, `1.1`, etc.), with a plain title page, shorter subject headings
and direct explanatory prose. It does not copy their wording, project content or old brief.
The report's technical findings still concern baseline d1086b5 and its recorded 45-test run.
Later HTTPS/MFA/backup evidence has not been incorporated in this presentation-only pass.
The revised main text contains approximately 3,852 words using the builder's source counter.
All 21 pages were inspected after Word export. Contents, caption lists and page numbering
were refreshed. The exporter now invokes Word through late-bound automation to avoid a
cached Office type-library error on this machine; it still exports from the saved DOCX.
