# Issue verification

**Branch reviewed:** `dev`
**Compared with:** `main`  
**Review date:** 2026-11-10

| Issue | Status | Implementation status | Evidence and conclusion |
| --- | --- | --- | --- |
| [#18](https://github.com/cthit/SummIT/issues/18) Control who can upload what from admin GUI | Open | Partial | Admins can configure division-document requirements in the meeting administration UI, and the upload UI restricts personal uploads. The UI still allows a group to select non-required division types, so the complete “depending on group and requirements” behavior is not demonstrated. |
| [#22](https://github.com/cthit/SummIT/issues/22) Auto select latest meeting | Open | Not implemented | Document and upload pages require an explicit meeting selection; no automatic latest-meeting selection or “change meeting” flow is present. |
| [#21](https://github.com/cthit/SummIT/issues/21) Meeting announcement should go to all committees | Open | Partial | The announcement route sends only to groups returned by `get_document_requires(meeting_id)`, so whitelisted groups without requirements are still excluded. |
| [#20](https://github.com/cthit/SummIT/issues/20) Motion handling | Open | Partial | Motion is supported as an upload subtype and the database has motion document support, but the requested review workflow, visibility rules, mail notification, and deadline lock are not implemented. |
| [#19](https://github.com/cthit/SummIT/issues/19) Limit upload amounts for certain documents | Open | Partial | Duplicate document content is rejected, but there is no complete per-year, per-committee, or per-meeting cardinality enforcement for the document types listed in the issue. |
| [#17](https://github.com/cthit/SummIT/issues/17) Weird error when uploading a file too large | Open | Partial | `MAX_CONTENT_LENGTH` is configured and `RequestEntityTooLarge` has a dedicated translated error handler, but the issue remains open because the complete behavior is not verified as resolved. |
| [#16](https://github.com/cthit/SummIT/issues/16) Overwrite duplicate files | Open | Not implemented | Duplicate content is detected and rejected with a user-facing message. No overwrite path is present. |
| [#15](https://github.com/cthit/SummIT/issues/15) Download only relevant liberation documents | Open | Not resolved | The admin download query selects liberation documents for all whitelisted groups, rather than filtering them by the configured yearly liberation requirements. |
| [#14](https://github.com/cthit/SummIT/issues/14) Edit mail configs from admin view | Open | Not implemented | Mail templates are loaded from `project/mail_config/`; no admin route or editor for changing them is present. |
| [#13](https://github.com/cthit/SummIT/issues/13) Limit file type for uploads | **Closed** | Implemented in code | Uploads require a `.pdf` extension and `%PDF-` signature in the server-side route; the form also advertises PDF-only input. |
| [#12](https://github.com/cthit/SummIT/issues/12) Add error handling | Open | Partial | Dedicated handlers cover 413, HTTP exceptions, and unexpected exceptions, with logging for unexpected failures, but the issue remains open because error handling is not completely resolved. |
| [#11](https://github.com/cthit/SummIT/issues/11) Better error messages for end users | Open | Partial | Upload failures use translated flash messages and a translated error template, but the issue remains open because the complete user-facing error behavior is not resolved. |
| [#10](https://github.com/cthit/SummIT/issues/10) Limit file size for uploads | Open | Partial | The application exposes a configurable `APP_MAX_CONTENT_LENGTH` limit and converts oversized requests to a 413 response, but the issue remains open because the complete behavior is not resolved. |
| [#9](https://github.com/cthit/SummIT/issues/9) Limit upload options by group and requirements | Open | Partial | Owner membership and personal-upload restrictions are enforced server-side, and requirements are displayed/annotated. Non-required group document types are warned about rather than blocked. |
| [#8](https://github.com/cthit/SummIT/issues/8) Mail meeting admins after deadline | **Closed** | Implemented in code | The scheduled mail command sends a deadline-reached message after the configured deadline and records it in `SentMails`. |
| [#7](https://github.com/cthit/SummIT/issues/7) Infer LP from date | **Closed** | Implemented in code | `infer_study_period_from_date` maps dates to LP values and is exposed through the admin preview endpoint. |
| [#6](https://github.com/cthit/SummIT/issues/6) Infer year from date | **Closed** | Implemented in code | The same date inference returns the study year, including the January-to-previous-year LP2 boundary. |
| [#5](https://github.com/cthit/SummIT/issues/5) Send duty liberation mail | **Closed** | Implemented in code | Admins can trigger liberation mail for groups with missing required documents; sends are deduplicated by year. |
| [#4](https://github.com/cthit/SummIT/issues/4) Send mail when deadline approaches | **Closed** | Implemented in code | The scheduled mail command sends per-group reminders within the configured number of days before a deadline. |
| [#3](https://github.com/cthit/SummIT/issues/3) Add deadline to meeting creation | **Closed** | Implemented in code | Meeting creation and editing expose a deadline, store it, and normalize it to 23:59 on the selected date. |
| [#2](https://github.com/cthit/SummIT/issues/2) Make prettier | Open | Not started | An attempt has been made, it was not pretty |
