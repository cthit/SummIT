from project.database import get_db
import datetime
from enum import IntEnum, StrEnum
from dataclasses import dataclass
from pathlib import Path
import os
import hashlib

UPLOAD_BASE: Path = Path("/") / "data" / "uploads"


class LP(IntEnum):
    LP1 = 1
    LP2 = 2
    LP3 = 3
    LP4 = 4
    SUMMER = 5


class DocumentType(StrEnum):
    MEETING = "meeting"
    DIVISION = "division"


class MeetingDocumentTypes(StrEnum):
    MOTION = "motion"
    PROPOSITION = "proposition"
    DAGORDNING = "dagordning"
    INTERPELLATION = "interpellation"
    NOMINERINGAR = "nomineringar"
    OTHER = "other"


class DivisionDocumentTypes(StrEnum):
    VERKSAMHETSRAPPORT = "verksamhetsrapport"
    VERKSAMETSBERATTELSE = "veksamhetsberattelse"
    EKONOMISKRAPPORT = "ekonomiskrapport"
    EKONOMISKBERATTELSE = "ekonomiskberattelse"
    BUDGET = "budget"


@dataclass(frozen=True, slots=True)
class StudyPeriod:
    id: int
    year: int
    lp: LP


@dataclass(frozen=True, slots=True)
class Meeting:
    id: int
    date: datetime.date
    study_period: StudyPeriod


@dataclass(frozen=True, slots=True)
class DocumentOwner:
    _id: str


@dataclass(frozen=True, slots=True)
class Document:
    _id: int
    name: str
    owner: DocumentOwner
    file_path: Path
    uploaded: datetime.datetime


def create_meeting(
    meeting_date: datetime.date, study_period: StudyPeriod
) -> Meeting | None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Meetings (meeting_date, study_period_id)
                VALUES (%s, %s)
                RETURNING meeting_id, meeting_date, study_period_id;
                """,
                (meeting_date, study_period.id),
            )
            meeting_data = cur.fetchone()
        conn.commit()
        if not meeting_data:
            return None
        return Meeting(
            id=meeting_data[0],
            date=meeting_data[1],
            study_period=study_period,
        )
    except Exception as e:
        print(e)
        conn.rollback()
        return None


def fetch_meetings() -> list[Meeting]:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT meeting_id, meeting_date, StudyPeriods.study_period_id, study_year, study_period
            FROM Meetings JOIN StudyPeriods ON Meetings.study_period_id=StudyPeriods.study_period_id
            ORDER BY meeting_date DESC;
            """
        )
        meeting_data = cur.fetchall()
    return list(map(lambda x: Meeting(*x[:2], StudyPeriod(*x[2:])), meeting_data))


def lookup_study_period(year: int, lp: LP) -> StudyPeriod | None:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT study_period_id, study_year, study_period
            FROM StudyPeriods
            WHERE study_year = %s AND study_period = %s;
            """,
            (year, int(lp)),
        )
        row = cur.fetchone()
        if not row:
            return None
        return StudyPeriod(id=row[0], year=row[1], lp=LP(row[2]))


def create_study_period(year: int, lp: LP) -> StudyPeriod | None:
    conn = get_db()
    try:
        # Try to insert; on conflict return existing row
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO StudyPeriods (study_year, study_period)
                VALUES (%s, %s)
                ON CONFLICT (study_year, study_period) DO NOTHING
                RETURNING study_period_id, study_year, study_period;
                """,
                (year, int(lp)),
            )
            row = cur.fetchone()
        conn.commit()

        if row:
            return StudyPeriod(id=row[0], year=row[1], lp=LP(row[2]))

        # If INSERT did nothing due to conflict, fetch existing
        return lookup_study_period(year, lp)
    except Exception as e:
        print(e)
        conn.rollback()
        return None


def upload_document(
    the_file: bytes,
    file_name: str,
    document_owner: DocumentOwner,
    meeting_id: int,
    document_type: DocumentType,
    document_subtype: str,
    is_group: bool = False,
) -> Document:
    conn = get_db()
    file_hash = hashlib.md5(the_file)
    file_path = UPLOAD_BASE / (f"{file_hash.hexdigest()}_{file_name}")

    create_document_owner(document_owner, is_group)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Documents (document_name, gamma_owner_id, file_path)
                VALUES (%s, %s, %s)
                RETURNING document_id, uploaded;
                """,
                (file_name, document_owner._id, str(file_path)),
            )
            document_id, timestamp = cur.fetchone()

            if document_type == DocumentType.MEETING:
                # Use provided subtype
                cur.execute(
                    """
                    INSERT INTO MeetingDocumentTypes (type_name) VALUES (%s)
                    ON CONFLICT (type_name) DO NOTHING;
                    """,
                    (document_subtype,),
                )
                cur.execute(
                    "SELECT type_id FROM MeetingDocumentTypes WHERE type_name = %s;",
                    (document_subtype,),
                )
                type_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO MeetingDocuments (document_id, type_id, meeting_id)
                    VALUES (%s, %s, %s);
                    """,
                    (document_id, type_id, meeting_id),
                )
            else:  # DocumentType.DIVISION
                # Get study_period_id from meeting
                cur.execute(
                    "SELECT study_period_id FROM Meetings WHERE meeting_id = %s;",
                    (meeting_id,),
                )
                study_period_id = cur.fetchone()[0]
                # Use provided subtype
                cur.execute(
                    """
                    INSERT INTO DivisionDocumentTypes (type_name) VALUES (%s)
                    ON CONFLICT (type_name) DO NOTHING;
                    """,
                    (document_subtype,),
                )
                cur.execute(
                    "SELECT type_id FROM DivisionDocumentTypes WHERE type_name = %s;",
                    (document_subtype,),
                )
                type_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO DivisionDocuments (document_id, type_id, study_period_id)
                    VALUES (%s, %s, %s);
                    """,
                    (document_id, type_id, study_period_id),
                )

        document = Document(
            _id=document_id,
            name=file_name,
            owner=document_owner,
            file_path=file_path,
            uploaded=timestamp,
        )
        if file_path.is_file():
            raise Exception("File already exists...?")
        with file_path.open("wb") as f:
            f.write(the_file)
        conn.commit()
    except:
        conn.rollback()
        raise
    return document


def create_document_owner(document_owner: DocumentOwner, is_group: bool = False):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO DocumentOwners (gamma_owner_id)
                VALUES (%s)
                ON CONFLICT (gamma_owner_id) DO NOTHING;
                """,
                (document_owner._id,),
            )
            if is_group:
                cur.execute(
                    """
                    INSERT INTO Committees (gamma_group_id)
                    VALUES (%s)
                    ON CONFLICT (gamma_group_id) DO NOTHING;
                    """,
                    (document_owner._id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO Members (gamma_user_id)
                    VALUES (%s)
                    ON CONFLICT (gamma_user_id) DO NOTHING;
                    """,
                    (document_owner._id,),
                )
    except:
        conn.rollback()
        raise


def fetch_documents_for_meeting(
    meeting_id: int, user_id: str, group_ids: list[str]
) -> dict:
    conn = get_db()
    all_owner_ids = [user_id] + group_ids

    with conn.cursor() as cur:
        # Fetch meeting documents
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.gamma_owner_id, mdt.type_name
            FROM Documents d
            JOIN MeetingDocuments md ON d.document_id = md.document_id
            JOIN MeetingDocumentTypes mdt ON md.type_id = mdt.type_id
            WHERE md.meeting_id = %s AND d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (meeting_id, all_owner_ids),
        )
        meeting_docs = cur.fetchall()

        # Fetch division documents for the meeting's study period
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.gamma_owner_id, ddt.type_name
            FROM Documents d
            JOIN DivisionDocuments dd ON d.document_id = dd.document_id
            JOIN DivisionDocumentTypes ddt ON dd.type_id = ddt.type_id
            JOIN Meetings m ON dd.study_period_id = m.study_period_id
            WHERE m.meeting_id = %s AND d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (meeting_id, all_owner_ids),
        )
        division_docs = cur.fetchall()

    # Group documents by owner
    documents_by_owner = {}
    for doc in meeting_docs + division_docs:
        doc_id, doc_name, owner_id, doc_type = doc
        if owner_id not in documents_by_owner:
            documents_by_owner[owner_id] = []
        documents_by_owner[owner_id].append(
            {"id": doc_id, "name": doc_name, "type": doc_type}
        )

    return documents_by_owner


def fetch_document_by_id(document_id: int, allowed_owner_ids: list[str]) -> dict | None:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT document_id, document_name, file_path, gamma_owner_id
            FROM Documents
            WHERE document_id = %s AND gamma_owner_id = ANY(%s);
            """,
            (document_id, allowed_owner_ids),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {"id": row[0], "name": row[1], "file_path": row[2], "owner_id": row[3]}


def delete_document(document_id: int, allowed_owner_ids: list[str]) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Get file path first
            cur.execute(
                "SELECT file_path FROM Documents WHERE document_id = %s AND gamma_owner_id = ANY(%s);",
                (document_id, allowed_owner_ids),
            )
            row = cur.fetchone()
            if not row:
                return False

            file_path = Path(row[0])

            # Delete from MeetingDocuments or DivisionDocuments first (foreign key constraint)
            cur.execute(
                "DELETE FROM MeetingDocuments WHERE document_id = %s;", (document_id,)
            )
            cur.execute(
                "DELETE FROM DivisionDocuments WHERE document_id = %s;", (document_id,)
            )

            # Now delete from Documents
            cur.execute(
                "DELETE FROM Documents WHERE document_id = %s AND gamma_owner_id = ANY(%s);",
                (document_id, allowed_owner_ids),
            )

            # Delete physical file
            if file_path.is_file():
                file_path.unlink()

        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
        return False


def delete_meeting_and_documents(meeting_id: int) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Get all meeting documents
            cur.execute(
                "SELECT d.document_id, d.file_path FROM Documents d JOIN MeetingDocuments md ON d.document_id = md.document_id WHERE md.meeting_id = %s;",
                (meeting_id,),
            )
            meeting_doc_rows = cur.fetchall()

            # Get all division documents (via study_period_id)
            cur.execute(
                "SELECT d.document_id, d.file_path FROM Documents d JOIN DivisionDocuments dd ON d.document_id = dd.document_id JOIN Meetings m ON dd.study_period_id = m.study_period_id WHERE m.meeting_id = %s;",
                (meeting_id,),
            )
            division_doc_rows = cur.fetchall()

            # Delete meeting documents
            for doc_id, file_path in meeting_doc_rows:
                cur.execute(
                    "DELETE FROM MeetingDocuments WHERE document_id = %s;", (doc_id,)
                )
                cur.execute("DELETE FROM Documents WHERE document_id = %s;", (doc_id,))
                if file_path and Path(file_path).is_file():
                    Path(file_path).unlink()

            # Delete division documents
            for doc_id, file_path in division_doc_rows:
                cur.execute(
                    "DELETE FROM DivisionDocuments WHERE document_id = %s;", (doc_id,)
                )
                cur.execute("DELETE FROM Documents WHERE document_id = %s;", (doc_id,))
                if file_path and Path(file_path).is_file():
                    Path(file_path).unlink()

            # Delete document requires
            cur.execute(
                "DELETE FROM DocumentRequire WHERE meeting_id = %s;", (meeting_id,)
            )

            # Delete meeting
            cur.execute("DELETE FROM Meetings WHERE meeting_id = %s;", (meeting_id,))

        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
        return False


def get_document_requires(meeting_id: int) -> dict:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dt.type_name, dr.gamma_owner_id
            FROM DocumentRequire dr
            JOIN DivisionDocumentTypes dt ON dr.document_type_id = dt.type_id
            WHERE dr.meeting_id = %s;
            """,
            (meeting_id,),
        )
        rows = cur.fetchall()

    # Return dict: {group_id: [doc_type1, doc_type2, ...]}
    result = {}
    for doc_type, group_id in rows:
        if group_id not in result:
            result[group_id] = []
        result[group_id].append(doc_type)
    return result


def set_document_require(meeting_id: int, group_id: str, doc_type_name: str) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Ensure document owner exists
            cur.execute(
                "INSERT INTO DocumentOwners (gamma_owner_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                (group_id,),
            )
            cur.execute(
                "INSERT INTO Committees (gamma_group_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                (group_id,),
            )

            # Get type_id
            cur.execute(
                "SELECT type_id FROM DivisionDocumentTypes WHERE type_name = %s;",
                (doc_type_name,),
            )
            row = cur.fetchone()
            if not row:
                # Create the type if it doesn't exist
                cur.execute(
                    "INSERT INTO DivisionDocumentTypes (type_name) VALUES (%s) RETURNING type_id;",
                    (doc_type_name,),
                )
                row = cur.fetchone()

            type_id = row[0]

            # Insert requirement
            cur.execute(
                "INSERT INTO DocumentRequire (document_type_id, meeting_id, gamma_owner_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
                (type_id, meeting_id, group_id),
            )
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
        return False


def remove_document_require(meeting_id: int, group_id: str, doc_type_name: str) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Get type_id
            cur.execute(
                "SELECT type_id FROM DivisionDocumentTypes WHERE type_name = %s;",
                (doc_type_name,),
            )
            row = cur.fetchone()
            if not row:
                return False

            type_id = row[0]

            # Delete requirement
            cur.execute(
                "DELETE FROM DocumentRequire WHERE document_type_id = %s AND meeting_id = %s AND gamma_owner_id = %s;",
                (type_id, meeting_id, group_id),
            )
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
        return False
