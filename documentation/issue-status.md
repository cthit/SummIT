# Issue verification

**Branch reviewed:** `dev`  
**Compared with:** `main`  
**Review date:** 2026-11-09

| Issue | Status | Implementation status | Evidence and conclusion |
| --- | --- | --- | --- |
| [#18](https://github.com/cthit/SummIT/issues/18) Control who can upload what from admin GUI | Open | Partial | Admins can configure division-document requirements in the meeting administration UI, and the upload UI restricts personal uploads. The UI still allows a group to select non-required division types, so the complete “depending on group and requirements” behavior is not demonstrated. |
| [#17](https://github.com/cthit/SummIT/issues/17) Weird error when uploading a file too large | **Closed** | Implemented in code | `MAX_CONTENT_LENGTH` is configured and `RequestEntityTooLarge` has a dedicated translated error handler. The repository test suite passes through `uv run pytest -q`. |
| [#16](https://github.com/cthit/SummIT/issues/16) Overwrite duplicate files | Open | Not implemented | Duplicate content is detected and rejected with a user-facing message. No overwrite path is present. |
| [#15](https://github.com/cthit/SummIT/issues/15) Download only relevant liberation documents | Open | Not resolved | The admin download query selects liberation documents for all whitelisted groups, rather than filtering them by the configured yearly liberation requirements. |
| [#14](https://github.com/cthit/SummIT/issues/14) Edit mail configs from admin view | Open | Not implemented | Mail templates are loaded from `project/mail_config/`; no admin route or editor for changing them is present. |
| [#13](https://github.com/cthit/SummIT/issues/13) Limit file type for uploads | **Closed** | Implemented in code | Uploads require a `.pdf` extension and `%PDF-` signature in the server-side route; the form also advertises PDF-only input. |
| [#12](https://github.com/cthit/SummIT/issues/12) Add error handling | **Closed** | Implemented in code | Dedicated handlers cover 413, HTTP exceptions, and unexpected exceptions, with logging for unexpected failures. |
| [#11](https://github.com/cthit/SummIT/issues/11) Better error messages for end users | **Closed** | Implemented in code | Upload failures use translated flash messages and a translated error template. |
| [#10](https://github.com/cthit/SummIT/issues/10) Limit file size for uploads | **Closed** | Implemented in code | The application exposes a configurable `APP_MAX_CONTENT_LENGTH` limit and converts oversized requests to a 413 response. |
| [#9](https://github.com/cthit/SummIT/issues/9) Limit upload options by group and requirements | Open | Partial | Owner membership and personal-upload restrictions are enforced server-side, and requirements are displayed/annotated. Non-required group document types are warned about rather than blocked. |
| [#8](https://github.com/cthit/SummIT/issues/8) Mail meeting admins after deadline | **Closed** | Implemented in code | The scheduled mail command sends a deadline-reached message after the configured deadline and records it in `SentMails`. |
| [#7](https://github.com/cthit/SummIT/issues/7) Infer LP from date | **Closed** | Implemented in code | `infer_study_period_from_date` maps dates to LP values and is exposed through the admin preview endpoint. |
| [#6](https://github.com/cthit/SummIT/issues/6) Infer year from date | **Closed** | Implemented in code | The same date inference returns the study year, including the January-to-previous-year LP2 boundary. |
| [#5](https://github.com/cthit/SummIT/issues/5) Send duty liberation mail | **Closed** | Implemented in code | Admins can trigger liberation mail for groups with missing required documents; sends are deduplicated by year. |
| [#4](https://github.com/cthit/SummIT/issues/4) Send mail when deadline approaches | **Closed** | Implemented in code | The scheduled mail command sends per-group reminders within the configured number of days before a deadline. |
| [#3](https://github.com/cthit/SummIT/issues/3) Add deadline to meeting creation | **Closed** | Implemented in code | Meeting creation and editing expose a deadline, store it, and normalize it to 23:59 on the selected date. |
| [#2](https://github.com/cthit/SummIT/issues/2) Make prettier | Open | Subjective / not formally verifiable | The branch contains shared CSS and template formatting work, but there is no objective acceptance criterion or visual review record in the repository. |
