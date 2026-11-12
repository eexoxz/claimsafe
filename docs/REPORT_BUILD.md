# Report production notes

The report is a formal coursework document. Its font, justification and neat layout follow
the user's supplied FYP report: A4, one-inch margins, Times New Roman 12 pt and 1.5 body spacing.
Content organisation and explanatory style follow the three security samples (Mattew Loh,
Ong Yu Chin and Lau En Sin), subject to the current rubric. The report has no abstract.
The original FYP and distinction samples remain external references, not repository
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

The reviewed export has 20 pages. Word counted 3,770 words across Sections 1–5 and
4,384 across the whole document. Recheck the counts after adding any submission material.
The exporter writes those statistics to a companion `.layout.json` file.

The report covers application baseline `aaf4b89`. It uses the retained 30 October
83-test regression run, 19 HTTPS account checks and dependency audit, and distinguishes
those from the earlier web and TLS scans. The two interface captures are from the
25 October fictional walkthrough. See the [user manual](USER_MANUAL.md) for the current
demo steps.
