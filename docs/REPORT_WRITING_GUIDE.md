# ClaimSafe report writing guide

## Purpose and source of the writing preferences

The content organisation and explanatory approach follow the three supplied security
coursework samples: Mattew Loh, Ong Yu Chin and Lau En Sin. Learn how they introduce the
system, discuss security issues, explain implementations with figures/code and evaluate
the results. Use original ClaimSafe content and verified evidence, not their wording,
project details, findings, reference lists or older assignment requirements. The current
2026 coursework brief and marking criteria govern the required coverage.

The user's FYP report is a visual formatting reference only: font, paragraph justification,
spacing and neat arrangement. It does not determine the security report's content,
research structure or preliminary sections. The user explicitly requested no abstract.
The report starts with its cover, contents and caption lists, followed by the numbered
security report sections. Do not add an abstract through the source or document builder.

Write in plain, naturally connected paragraphs, preserving qualifications and developing
the explanation where useful. Avoid stock introductions, repeated feature inventories,
unnecessary lists and brochure/workbook language. This guide records writing preferences;
it does not establish test results or replace the coursework rubric.

## Words, sentences and paragraphs

The user's later presentation reference is their own FYP report supplied on 26 October 2026.
The ClaimSafe report should be a formal assignment in editable Word and matching PDF:
A4 portrait, one-inch margins, Times New Roman 12 pt, 1.5 body spacing, justified paragraphs,
numbered sections and subsections, contents, caption lists and centred page numbers.
Use Roman preliminary numbering and Arabic body numbering. The user's 29 October clarification
asks for ordinary report writing and formatting learned from the supplied security samples.
Use numbered sections such as `1.0 Introduction and System Overview`, `2.0 Security Analysis
and Design`, `3.0 Security Implementation`, `4.0 Discussion` and `5.0 Conclusion`, followed by
references and an appendix. Give subsections short names for their actual subject. Do not
invent branded headings, slogans, workbook prompts, checklist pages, decorative banners or
brochure sections. Follow the security coursework's content rather than copying the FYP's
seven chapters or its subject matter. Plain tables
may summarise genuine comparisons and evidence; do not turn narrative into a workbook.
Keep development instructions, submission reminders and advice addressed to the student in
separate project documentation. Retain a factual AI acknowledgement in the report itself.

Use direct, familiar academic language. Choose a precise technical term when the term is
needed, explain it on first use, and connect it to what actually happens in ClaimSafe. Prefer
“uses”, “checks” and “prevents this request” to inflated wording such as “leverages”, “robust
ecosystem” or “ensures complete protection”. Avoid promotional descriptions of the app.

Develop one main point in each paragraph. Introduce the security concern, explain the design
or implementation decision, and connect the evidence to its significance. Paragraphs should
read naturally; do not force every one into an identical template or repeat the same opening.
Vary sentence length when it improves the flow. Join related ideas where the relationship
is clear, but do not turn several independent points into one long sentence.
Do not remove an important qualification just to make the prose sound smoother, and avoid
repeated sentences that merely list four or five feature names without explaining them.

The main report should use connected prose. Use a table for a real comparison, permission
matrix, risk assessment or set of test outcomes. Use lists for genuine steps or parallel
items. Avoid presenting every explanation as numbered points. Use headings to organise the
assessment, without adding a heading above every short paragraph. Avoid unnecessary hyphens
and invented labels; retain punctuation required for clarity and exact technical identifiers.

Use a consistent academic voice. Unless the module guidance requires first person, describe
the system and decisions directly: “ClaimSafe checks the claimant's identity” or “The design
limits public item details”. Do not write “our group” or “the team” for work done individually.
Use past tense for completed implementation and observed testing; present tense may describe
current system behaviour. Use future or conditional wording for planned improvements.

## Explanation should follow the actual project

The report's central problem is controlled disclosure and authorised collection. A public
listing must help an owner recognise an item without revealing all the details an impostor
could repeat. Staff need private evidence, while students should be able to see only their
own claims. An approved collection must happen once, with an accountable handover.

Use that problem to explain why the controls exist. A paragraph on permissions should show
why a role check alone is insufficient for a student's private claim. A paragraph on collection
should explain the relationship between approval, the code's validity and the final state
change. Explain framework protections as configured and used by this project; do not imply
the student invented Django's authentication, CSRF protection or cryptographic primitives.

Choose code extracts and figures that let a reviewer check the explanation. Introduce each
figure, give it a meaningful caption, and discuss the relevant observation afterwards. A
screenshot of an interface illustrates that screen; a successful test needs an action and
observed outcome. Do not use screenshots as substitutes for technical reasoning.

## Sources and evidence

Use primary documentation and credible security literature for external claims. Read the
source before citing it. Explain why it supports a project decision rather than adding a
citation to a generic definition. Never copy the sample reports' reference lists, wording,
diagrams or risk scores. Confirm the lecturer's required referencing style; the 2026 brief
does not establish every formatting rule found in older samples.

Describe local test results as local test results. The initial implementation has a recorded
run of 45 passing automated tests and a fictional browser handover. That is not evidence of
45 penetration tests, a full OWASP assessment, real campus use or legal compliance. The test
count and outcomes must be refreshed against the version used for the final report.

Do not invent survey responses, participants, screenshots, scan findings, timing measurements,
deployment results or an insecure earlier application. A new application can be designed
securely from the beginning. Explain its identified risks, controls and verification without
fabricating a before-and-after story.

State material limits where they belong in the reasoning. The current server uses local
HTTP; production security switches are not evidence of a working certificate or TLS setup.
Private records are encrypted, but the application and host operator can decrypt them. Audit
records are restricted through application routes but are not tamper-proof against a database
administrator. Staff still make ownership decisions. Describe implemented MFA only if it is
actually added and tested.

## Illustrative paragraph style

The following passage illustrates the proposed voice using the current implementation. It
is not a replacement for the final report's references, figures or measured evidence.

> Approval alone is not sufficient to complete a collection because an approved request
> could be submitted more than once. ClaimSafe therefore issues a collection code for a
> particular approved claim and gives it a limited lifetime. When an officer confirms the
> handover, the server checks the code and records its use within the same database
> transaction that updates the claim and item. If a required update fails, the transaction
> is rolled back so the code is not consumed without a completed handover.
>
> The concurrent collection test sent two requests for the same approved claim using the
> same code. One request completed the handover and the other was rejected, while the audit
> table contained one completed collection event. This supports the intended collection
> rule under the tested local SQLite configuration. A change to the database engine or
> transaction settings would require the behaviour to be tested again.

## Review before drafting is considered finished

Read each section for a clear relationship between the risk, decision, implementation and
evidence. Remove repetition, vague praise, unnecessary definitions and claims stronger than
the observations support. Check terminology, source accuracy, figure references and the
actual app version. Keep the user's voice while correcting factual and grammatical errors.
Use the assignment's required AI acknowledgement and declaration honestly.
Preserve the existing report's formatting during later revisions unless the user requests
a formatting change. Distinguish published findings from the student's design decisions,
and distinguish mocked tests, fictional records, browser observations and independent user
testing rather than treating those as interchangeable forms of evidence.
