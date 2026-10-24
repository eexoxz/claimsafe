# Development log

## 2026-10-25 - Scope and foundation

- Selected an original campus lost-property claim and collection workflow.
- Planned public/private item data separation and a staff-reviewed ownership process.
- Chose Django 5.2 LTS for a small, explainable server-rendered application with framework
  authentication, CSRF protection, ORM queries and template escaping.
- Chose SQLite for the initial local prototype. Collection authorisation must use conditional
  writes inside a transaction, rather than relying on SQLite row-lock functionality.
- Prepared a dedicated local repository and excluded runtime data and secrets.

Implementation, test results, limitations and further decisions will be recorded as they are verified.
