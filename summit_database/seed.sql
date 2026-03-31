CREATE TABLE IF NOT EXISTS StudyPeriods (
    study_period_id SERIAL PRIMARY KEY,
    study_year INTEGER,
    study_period INTEGER,
    CONSTRAINT study_period_primary_key UNIQUE (study_year, study_period)
);

CREATE TABLE IF NOT EXISTS Meetings (
    meeting_id SERIAL PRIMARY KEY,
    meeting_date DATE UNIQUE,
    study_period_id INTEGER REFERENCES StudyPeriods(study_period_id)
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
