CREATE TABLE IF NOT EXISTS StudyPeriods (
    study_period_id SERIAL PRIMARY KEY,
    study_year INTEGER,
    study_period INTEGER,
    CONSTRAINT study_period_primary_key UNIQUE (study_year, study_period)
);

CREATE TABLE IF NOT EXISTS Meetings (
    meeting_id SERIAL PRIMARY KEY,
    meeting_date DATE UNIQUE,
    study_period_id INTEGER REFERENCES StudyPeriods(study_period_id),
    -- Upload deadline for the meeting's documents (server-local time)
    deadline TIMESTAMP
);

CREATE TABLE IF NOT EXISTS DocumentOwners (
    gamma_owner_id TEXT PRIMARY KEY
);

-- Example usrId and grpId 8bd1329b-01e6-444e-852b-eed58659d717
CREATE TABLE IF NOT EXISTS Members (
    gamma_user_id TEXT PRIMARY KEY REFERENCES DocumentOwners(gamma_owner_id)
);

CREATE TABLE IF NOT EXISTS Committees (
    gamma_group_id TEXT PRIMARY KEY REFERENCES DocumentOwners(gamma_owner_id)
);

CREATE TABLE IF NOT EXISTS Documents (
    document_id SERIAL PRIMARY KEY,
    document_name TEXT NOT NULL,
    gamma_owner_id TEXT NOT NULL REFERENCES DocumentOwners(gamma_owner_id),
    file_path TEXT UNIQUE,
    uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS LiberationDocumentTypes (
    type_id SERIAL PRIMARY KEY,
    type_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS LiberationDocuments (
    document_id INTEGER PRIMARY KEY REFERENCES Documents(document_id),
    type_id INTEGER REFERENCES LiberationDocumentTypes(type_id)
);

CREATE TABLE IF NOT EXISTS MeetingDocumentTypes (
    type_id SERIAL PRIMARY KEY,
    type_name TEXT UNIQUE
);

-- motioner, prepositioner, dagordning
CREATE TABLE IF NOT EXISTS MeetingDocuments (
    document_id INTEGER PRIMARY KEY REFERENCES Documents(document_id),
    type_id INTEGER REFERENCES MeetingDocumentTypes(type_id),
    meeting_id INTEGER REFERENCES Meetings(meeting_id)
);

CREATE TABLE IF NOT EXISTS DivisionDocumentTypes (
    type_id SERIAL PRIMARY KEY,
    type_name TEXT UNIQUE
);

-- rapporter, budget, berättelse, planer eg. en gång per lp eller år 
CREATE TABLE IF NOT EXISTS DivisionDocuments (
    document_id INTEGER PRIMARY KEY REFERENCES Documents(document_id),
    type_id INTEGER REFERENCES DivisionDocumentTypes(type_id),
    study_period_id INTEGER REFERENCES StudyPeriods(study_period_id)
);

CREATE TABLE IF NOT EXISTS DocumentRequire (
    document_type_id INTEGER REFERENCES DivisionDocumentTypes(type_id),
    meeting_id INTEGER REFERENCES Meetings(meeting_id),
    gamma_owner_id TEXT REFERENCES DocumentOwners(gamma_owner_id),
    PRIMARY KEY (document_type_id, meeting_id, gamma_owner_id)
);

-- Which liberation document types each specific yearly group (digit25,
-- prit24, ...) must submit, set by liberation admins. gamma_owner_id is the
-- super-group that owns the uploaded documents; group_name identifies the
-- sitting group, built as committee name + year in the admin UI since
-- Gamma's instance data is unreliable. The reminder mail goes to
-- <group_name>@chalmers.it.
CREATE TABLE IF NOT EXISTS LiberationRequire (
    gamma_owner_id TEXT NOT NULL REFERENCES DocumentOwners(gamma_owner_id),
    group_name TEXT NOT NULL,
    group_pretty_name TEXT NOT NULL,
    document_type_id INTEGER REFERENCES LiberationDocumentTypes(type_id),
    PRIMARY KEY (group_name, document_type_id)
);

-- Records which notification mails have been sent, so scheduler restarts
-- and re-runs never double-send.
CREATE TABLE IF NOT EXISTS SentMails (
    sent_mail_id SERIAL PRIMARY KEY,
    -- e.g. 'deadline_reminder' | 'deadline_reached' | 'duty_retirement_<year>'
    mail_type TEXT NOT NULL,
    -- NULL for mails not tied to a meeting (duty liberation)
    meeting_id INTEGER REFERENCES Meetings(meeting_id) ON DELETE CASCADE,
    -- NULL for board-wide mails (deadline reached)
    gamma_owner_id TEXT REFERENCES DocumentOwners(gamma_owner_id),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sent_mails_unique
        UNIQUE NULLS NOT DISTINCT (mail_type, meeting_id, gamma_owner_id)
);
