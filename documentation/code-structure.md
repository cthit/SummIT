# SummIT code structure

This page describes the application structure on the `dev` branch. It is
intended to be a maintenance and review guide, not an exhaustive API
reference.

## Repository layout

```text
.
├── project/
│   ├── __init__.py              Flask application factory and configuration
│   ├── auth.py                  OAuth login, session setup, and access guards
│   ├── main.py                  Main pages, document routes, and admin routes
│   ├── mail.py                  Admin-triggered mail routes
│   ├── mail_handler.py          Gotify client and mail-template rendering
│   ├── tasks.py                 Scheduled deadline and reminder mail command
│   ├── data_handler.py          Database models, queries, and document storage
│   ├── database.py              PostgreSQL connection-pool integration
│   ├── error.py                 HTTP, upload-size, and unexpected-error handlers
│   ├── i18n.py                  English/Swedish translations
│   ├── gamma/                   Gamma API client and response types
│   ├── mail_config/             Jinja mail templates and static mail variables
│   ├── templates/               Flask/Jinja HTML templates
│   └── static/                  Browser stylesheets
├── summit_database/
│   ├── seed.sql                 PostgreSQL schema and seed data
│   └── Dockerfile               Database image definition
├── documentation/
│   ├── code-structure.md        This document
│   ├── issue-status.md          Issue verification on the dev branch
│   └── er.puml                  PlantUML database relationship diagram
├── tests/                       Automated tests
├── wsgi.py                      WSGI entry point
├── Dockerfile                   Web application image
└── docker-compose.yml            Web, mailer, database, and Gotify services
```

## Application startup

`wsgi.py` exposes the Flask application. The application factory in
`project/__init__.py` loads environment variables, configures logging and the
upload-size limit, initializes the database and OAuth client, registers the
blueprints, installs error handlers, and registers the `send-due-mails` CLI
command.

The application has three blueprints:

| Blueprint | Responsibility | Main surfaces |
| --- | --- | --- |
| `auth` | Login, logout, and user/session setup | OAuth callbacks and access decorators |
| `main` | User documents, uploads, meetings, and meeting administration | `/documents`, `/admin`, `/admin/liberation` |
| `mail` | Admin-triggered announcements and liberation mail | `/admin/mail/...` |

## Request and data flow

1. A request enters through the WSGI application and the registered
   `before_request` hook restores the authenticated user from the session.
2. Authentication decorators in `auth.py` protect user and admin routes.
3. Route handlers in `main.py` or `mail.py` validate request input and
   permissions, then call functions in `data_handler.py`.
4. `data_handler.py` performs PostgreSQL queries through `database.py` and
   stores uploaded files under `/data/uploads`.
5. Routes render a template, redirect with a translated flash message, or
   return a file/JSON response.
6. Unexpected HTTP and application errors are rendered by `error.py`.

The upload path applies both browser-side controls in `templates/upload.html`
and server-side checks in `main.py`. Server-side checks include owner
membership, document type/subtype, PDF signature, duplicate content, meeting
existence, and deadline rules.

## Persistence model

The database schema is defined in `summit_database/seed.sql`; the corresponding
relationships are sketched in [`er.puml`](./er.puml). The central `Documents`
record stores common metadata and a filesystem path. A document is classified
through one of `MeetingDocuments`, `DivisionDocuments`, or
`LiberationDocuments`, with a type table for each classification.

Meetings refer to a `StudyPeriods` row and may have a deadline. Requirement
tables connect meetings or liberation group instances to required document
types. `SentMails` makes scheduled mail operations idempotent.

## Background mail processing

The `summit_mailer` service runs the Flask `send-due-mails` command
periodically. `tasks.py` finds meetings with deadlines, sends reminder and
deadline-reached messages, and records successful sends in `SentMails`.
`mail_handler.py` renders templates from `project/mail_config/` with strict
variable checking before sending through Gotify.

## Deployment components

`docker-compose.yml` runs:

- `summit_web`: the Gunicorn-hosted Flask application;
- `summit_mailer`: the periodic mail command;
- `summit_db`: PostgreSQL with persistent database storage; and
- `gotify`: the mail delivery service.

Environment-specific credentials, OAuth settings, database settings, and
upload limits are supplied through `.env`; `.env-example` documents the
expected variables.

## Verification scope

This page documents the structure observed on `dev`. It does not claim that
all backlog issues are closed. See [`issue-status.md`](./issue-status.md) for
the issue-by-issue evidence review and the limitations of that verification.
