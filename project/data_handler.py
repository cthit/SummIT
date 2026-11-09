from project.database import get_db
import datetime
import logging
import psycopg2
from enum import IntEnum, StrEnum
from dataclasses import dataclass
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

UPLOAD_BASE: Path = Path("/") / "data" / "uploads"


class DuplicateDocumentError(ValueError):
    """Raised when the exact same file (name + content) is uploaded again."""


class LP(IntEnum):
    LP1 = 1
    LP2 = 2
    LP3 = 3
    LP4 = 4
    SUMMER = 5


def infer_study_period_from_date(meeting_date: datetime.date) -> tuple[int, "LP"]:
    """Map a date to (study_year, lp).

    study_year is the calendar year in which the study period STARTS, so
    early-January dates belong to the previous year's LP2. This keeps a
    December and a January meeting on the same StudyPeriod row, which
    division documents hang off.

    Boundaries are approximations of the Chalmers academic calendar
    (real dates shift a few days per year):
    LP1 Sep-Oct, LP2 Nov-Jan 15, LP3 Jan 16-Mar, LP4 Apr-Jun 15,
    SUMMER Jun 16-Aug.
    """
    m, d = meeting_date.month, meeting_date.day
    if m in (9, 10):
        return meeting_date.year, LP.LP1
    if m in (11, 12):
        return meeting_date.year, LP.LP2
    if m == 1:
        if d <= 15:
            return meeting_date.year - 1, LP.LP2
        return meeting_date.year, LP.LP3
    if m in (2, 3):
        return meeting_date.year, LP.LP3
    if m in (4, 5) or (m == 6 and d <= 15):
        return meeting_date.year, LP.LP4
    return meeting_date.year, LP.SUMMER


class DocumentType(StrEnum):
    MEETING = "meeting"
    DIVISION = "division"
    LIBERATION = "liberation"


class MeetingDocumentTypes(StrEnum):
    MOTION = "motion"
    PROPOSITION = "proposition"
    DAGORDNING = "dagordning"
    INTERPELLATION = "interpellation"
    NOMINERINGAR = "nomineringar"
    OTHER = "other"


class DivisionDocumentTypes(StrEnum):
    KVARTAL_VERKSAMHETSRAPPORT = "kvartal verksamhetsrapport"
    KVARTAL_EKONOMISKRAPPORT = "kvartal ekonomiskrapport"
    BUDGET = "budget"
    VERKSAMHETSPLAN = "verksamhetsplan"


class LiberationDocumentTypes(StrEnum):
    VERKSAMETSBERATTELSE = "verksamhetsberattelse"
    EKONOMISKBERATTELSE = "ekonomiskberattelse"


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
    deadline: datetime.datetime | None = None


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
    meeting_date: datetime.date,
    study_period: StudyPeriod,
    deadline: datetime.datetime | None = None,
) -> Meeting | None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Meetings (meeting_date, study_period_id, deadline)
                VALUES (%s, %s, %s)
                RETURNING meeting_id, meeting_date, deadline;
                """,
                (meeting_date, study_period.id, deadline),
            )
            meeting_data = cur.fetchone()
        conn.commit()
        if not meeting_data:
            return None
        return Meeting(
            id=meeting_data[0],
            date=meeting_data[1],
            deadline=meeting_data[2],
            study_period=study_period,
        )
    except psycopg2.errors.UniqueViolation:
        # meeting_date is UNIQUE - the one expected failure
        conn.rollback()
        return None
    except Exception:
        logger.exception("create_meeting failed")
        conn.rollback()
        raise


def _meeting_from_row(row: tuple) -> Meeting:
    return Meeting(
        id=row[0],
        date=row[1],
        deadline=row[2],
        study_period=StudyPeriod(id=row[3], year=row[4], lp=LP(row[5])),
    )


def fetch_meetings() -> list[Meeting]:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT meeting_id, meeting_date, deadline, StudyPeriods.study_period_id, study_year, study_period
            FROM Meetings JOIN StudyPeriods ON Meetings.study_period_id=StudyPeriods.study_period_id
            ORDER BY meeting_date DESC;
            """
        )
        meeting_data = cur.fetchall()
    return [_meeting_from_row(row) for row in meeting_data]


def fetch_meeting(meeting_id) -> Meeting | None:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT meeting_id, meeting_date, deadline, StudyPeriods.study_period_id, study_year, study_period
            FROM Meetings JOIN StudyPeriods ON Meetings.study_period_id=StudyPeriods.study_period_id
            WHERE meeting_id = %s;
            """,
            (meeting_id,),
        )
        meeting_data = cur.fetchone()
    if meeting_data is None:
        return None
    return _meeting_from_row(meeting_data)


def update_meeting_deadline(
    meeting_id: int, deadline: datetime.datetime | None
) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE Meetings SET deadline = %s WHERE meeting_id = %s;",
                (deadline, meeting_id),
            )
        conn.commit()
        return True
    except Exception:
        logger.exception("update_meeting_deadline(%s) failed", meeting_id)
        conn.rollback()
        raise


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
    except Exception:
        logger.exception("create_study_period failed")
        conn.rollback()
        raise


def upload_document(
    the_file: bytes,
    file_name: str,
    document_owner: DocumentOwner,
    meeting_id: int | None,
    document_type: DocumentType,
    document_subtype: str,
    is_group: bool = False,
) -> Document:
    conn = get_db()
    file_hash = hashlib.md5(the_file)
    file_path = UPLOAD_BASE / (f"{file_hash.hexdigest()}_{file_name}")

    # Check before touching the database: Documents.file_path is UNIQUE, so
    # a second row for the same file would fail anyway - but failing here
    # gives the route a clean, user-explainable error instead of a rollback.
    if file_path.is_file():
        raise DuplicateDocumentError(
            "This exact file has already been uploaded."
        )

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
            elif document_type == DocumentType.DIVISION:
                # Get study_period_id from meeting
                cur.execute(
                    "SELECT study_period_id FROM Meetings WHERE meeting_id = %s;",
                    (meeting_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("Meeting does not exist.")
                study_period_id = row[0]
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
            elif document_type == DocumentType.LIBERATION:
                # Liberation documents are not bound to any meeting or study period
                cur.execute(
                    """
                    INSERT INTO LiberationDocumentTypes (type_name) VALUES (%s)
                    ON CONFLICT (type_name) DO NOTHING;
                    """,
                    (document_subtype,),
                )
                cur.execute(
                    "SELECT type_id FROM LiberationDocumentTypes WHERE type_name = %s;",
                    (document_subtype,),
                )
                type_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO LiberationDocuments (document_id, type_id)
                    VALUES (%s, %s);
                    """,
                    (document_id, type_id),
                )

        document = Document(
            _id=document_id,
            name=file_name,
            owner=document_owner,
            file_path=file_path,
            uploaded=timestamp,
        )
        with file_path.open("wb") as f:
            f.write(the_file)
        conn.commit()
    except Exception:
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
    except Exception:
        conn.rollback()
        raise


def fetch_liberation_documents(user_id: str, group_ids: list[str]) -> dict:
    """Fetch all liberation documents accessible to the user and their groups."""
    conn = get_db()
    all_owner_ids = [user_id] + group_ids

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.gamma_owner_id, ldt.type_name
            FROM Documents d
            JOIN LiberationDocuments ld ON d.document_id = ld.document_id
            JOIN LiberationDocumentTypes ldt ON ld.type_id = ldt.type_id
            WHERE d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (all_owner_ids,),
        )
        liberation_docs = cur.fetchall()

    # Group documents by owner
    documents_by_owner = {}
    for doc in liberation_docs:
        doc_id, doc_name, owner_id, doc_type = doc
        if owner_id not in documents_by_owner:
            documents_by_owner[owner_id] = []
        documents_by_owner[owner_id].append(
            {"id": doc_id, "name": doc_name, "type": doc_type}
        )

    return documents_by_owner


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

        # Fetch liberation documents (not tied to any meeting or study period)
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.gamma_owner_id, ldt.type_name
            FROM Documents d
            JOIN LiberationDocuments ld ON d.document_id = ld.document_id
            JOIN LiberationDocumentTypes ldt ON ld.type_id = ldt.type_id
            WHERE d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (all_owner_ids,),
        )
        liberation_docs = cur.fetchall()

    # Group documents by owner
    documents_by_owner = {}
    for doc in meeting_docs + division_docs + liberation_docs:
        doc_id, doc_name, owner_id, doc_type = doc
        if owner_id not in documents_by_owner:
            documents_by_owner[owner_id] = []
        documents_by_owner[owner_id].append(
            {"id": doc_id, "name": doc_name, "type": doc_type}
        )

    return documents_by_owner


def fetch_downloadable_documents_for_meeting(
    meeting_id: int, whitelist_group_ids: list[str]
) -> list[tuple]:
    """
    Fetch all documents for a meeting: the meeting documents themselves
    (any owner - motions come from individual members), plus division and
    liberation documents from whitelisted groups.
    Returns list of tuples:
    (document_id, document_name, file_path, owner_id, doc_type, doc_subtype)
    """
    conn = get_db()
    documents = []

    with conn.cursor() as cur:
        # Fetch the meeting's own documents (motions, agenda, ...)
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.file_path, d.gamma_owner_id, 'meeting'::text, mdt.type_name
            FROM Documents d
            JOIN MeetingDocuments md ON d.document_id = md.document_id
            JOIN MeetingDocumentTypes mdt ON md.type_id = mdt.type_id
            WHERE md.meeting_id = %s
            ORDER BY d.uploaded DESC;
            """,
            (meeting_id,),
        )
        documents.extend(cur.fetchall())

        # Fetch division documents for the meeting's study period
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.file_path, d.gamma_owner_id, 'division'::text, ddt.type_name
            FROM Documents d
            JOIN DivisionDocuments dd ON d.document_id = dd.document_id
            JOIN DivisionDocumentTypes ddt ON dd.type_id = ddt.type_id
            JOIN Meetings m ON dd.study_period_id = m.study_period_id
            WHERE m.meeting_id = %s AND d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (meeting_id, whitelist_group_ids),
        )
        documents.extend(cur.fetchall())

        # Fetch liberation documents
        cur.execute(
            """
            SELECT d.document_id, d.document_name, d.file_path, d.gamma_owner_id, 'liberation'::text, ldt.type_name
            FROM Documents d
            JOIN LiberationDocuments ld ON d.document_id = ld.document_id
            JOIN LiberationDocumentTypes ldt ON ld.type_id = ldt.type_id
            WHERE d.gamma_owner_id = ANY(%s)
            ORDER BY d.uploaded DESC;
            """,
            (whitelist_group_ids,),
        )
        documents.extend(cur.fetchall())

    return documents


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

            # Delete from related document tables first (foreign key constraints)
            cur.execute(
                "DELETE FROM MeetingDocuments WHERE document_id = %s;", (document_id,)
            )
            cur.execute(
                "DELETE FROM DivisionDocuments WHERE document_id = %s;", (document_id,)
            )
            cur.execute(
                "DELETE FROM LiberationDocuments WHERE document_id = %s;",
                (document_id,),
            )

            # Now delete from Documents
            cur.execute(
                "DELETE FROM Documents WHERE document_id = %s AND gamma_owner_id = ANY(%s);",
                (document_id, allowed_owner_ids),
            )

        conn.commit()
    except Exception:
        logger.exception("delete_document(%s) failed", document_id)
        conn.rollback()
        raise

    # Remove the file only after the delete is committed - a failed commit
    # must not leave a Documents row pointing at a deleted file.
    if file_path.is_file():
        file_path.unlink()
    return True


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
            for doc_id, _ in meeting_doc_rows:
                cur.execute(
                    "DELETE FROM MeetingDocuments WHERE document_id = %s;", (doc_id,)
                )
                cur.execute("DELETE FROM Documents WHERE document_id = %s;", (doc_id,))

            # Delete division documents
            for doc_id, _ in division_doc_rows:
                cur.execute(
                    "DELETE FROM DivisionDocuments WHERE document_id = %s;", (doc_id,)
                )
                cur.execute("DELETE FROM Documents WHERE document_id = %s;", (doc_id,))

            # Delete document requires
            cur.execute(
                "DELETE FROM DocumentRequire WHERE meeting_id = %s;", (meeting_id,)
            )

            # Delete sent-mail records (the FK also cascades; explicit for
            # symmetry with the rest of this function)
            cur.execute(
                "DELETE FROM SentMails WHERE meeting_id = %s;", (meeting_id,)
            )

            # Delete meeting
            cur.execute("DELETE FROM Meetings WHERE meeting_id = %s;", (meeting_id,))

        conn.commit()
    except Exception:
        logger.exception("delete_meeting_and_documents(%s) failed", meeting_id)
        conn.rollback()
        raise

    # Remove files only after the DB state is committed - a failed commit
    # must not orphan rows pointing at deleted files.
    for _, file_path in meeting_doc_rows + division_doc_rows:
        if file_path and Path(file_path).is_file():
            Path(file_path).unlink()
    return True


def fetch_upcoming_meetings_with_deadline() -> list[Meeting]:
    """Meetings that have a deadline and have not happened yet - the set the
    mail scheduler cares about."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT meeting_id, meeting_date, deadline, StudyPeriods.study_period_id, study_year, study_period
            FROM Meetings JOIN StudyPeriods ON Meetings.study_period_id=StudyPeriods.study_period_id
            WHERE deadline IS NOT NULL AND meeting_date >= CURRENT_DATE
            ORDER BY meeting_date;
            """
        )
        rows = cur.fetchall()
    return [_meeting_from_row(row) for row in rows]


def get_missing_document_requires(meeting_id: int) -> dict[str, list[str]]:
    """Required division documents each group has NOT yet uploaded for the
    meeting's study period. Same shape as get_document_requires."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dr.gamma_owner_id, dt.type_name
            FROM DocumentRequire dr
            JOIN DivisionDocumentTypes dt ON dr.document_type_id = dt.type_id
            JOIN Meetings m ON dr.meeting_id = m.meeting_id
            WHERE dr.meeting_id = %s
              AND NOT EXISTS (
                SELECT 1
                FROM DivisionDocuments dd
                JOIN Documents d ON d.document_id = dd.document_id
                WHERE dd.type_id = dr.document_type_id
                  AND dd.study_period_id = m.study_period_id
                  AND d.gamma_owner_id = dr.gamma_owner_id
              );
            """,
            (meeting_id,),
        )
        rows = cur.fetchall()

    result: dict[str, list[str]] = {}
    for group_id, doc_type in rows:
        result.setdefault(group_id, []).append(doc_type)
    return result


def get_liberation_requires() -> list[dict]:
    """Liberation requirements, one entry per required yearly group:
    [{super_group_id, group_name, group_pretty_name, doc_types}].

    group_name identifies the responsible sitting group (digit25);
    super_group_id is the owner id its uploads are stored under.
    """
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT lr.gamma_owner_id, lr.group_name,
                   lr.group_pretty_name, lt.type_name
            FROM LiberationRequire lr
            JOIN LiberationDocumentTypes lt ON lr.document_type_id = lt.type_id
            ORDER BY lr.group_name;
            """
        )
        rows = cur.fetchall()

    by_group: dict[str, dict] = {}
    for super_id, group_name, pretty_name, doc_type in rows:
        entry = by_group.setdefault(
            group_name,
            {
                "super_group_id": super_id,
                "group_name": group_name,
                "group_pretty_name": pretty_name,
                "doc_types": [],
            },
        )
        entry["doc_types"].append(doc_type)
    return list(by_group.values())


def set_liberation_require(
    super_group_id: str,
    group_name: str,
    group_pretty_name: str,
    doc_type_name: str,
) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # The super-group owns the uploads; make sure it exists as an
            # owner so the FK holds
            cur.execute(
                "INSERT INTO DocumentOwners (gamma_owner_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                (super_group_id,),
            )
            cur.execute(
                "INSERT INTO Committees (gamma_group_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                (super_group_id,),
            )

            # Get or create the type row (rows are otherwise created lazily
            # on first upload)
            cur.execute(
                "SELECT type_id FROM LiberationDocumentTypes WHERE type_name = %s;",
                (doc_type_name,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO LiberationDocumentTypes (type_name) VALUES (%s) RETURNING type_id;",
                    (doc_type_name,),
                )
                row = cur.fetchone()

            cur.execute(
                """
                INSERT INTO LiberationRequire
                    (gamma_owner_id, group_name, group_pretty_name, document_type_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (group_name, document_type_id) DO NOTHING;
                """,
                (super_group_id, group_name, group_pretty_name, row[0]),
            )
        conn.commit()
        return True
    except Exception:
        logger.exception("set_liberation_require failed")
        conn.rollback()
        raise


def remove_liberation_require(group_name: str) -> bool:
    """Remove all liberation requirements for one yearly group."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM LiberationRequire WHERE group_name = %s;",
                (group_name,),
            )
            removed = cur.rowcount > 0
        conn.commit()
        return removed
    except Exception:
        logger.exception("remove_liberation_require failed")
        conn.rollback()
        raise


def get_missing_liberation_documents() -> list[dict]:
    """Requirements with what is still missing, one entry per yearly group:
    [{super_group_id, group_name, group_pretty_name, missing}].

    Uploads are matched by the super-group owner id, since that is how
    documents are stored.
    """
    requires = get_liberation_requires()
    if not requires:
        return []

    super_ids = list({r["super_group_id"] for r in requires})
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.gamma_owner_id, lt.type_name
            FROM Documents d
            JOIN LiberationDocuments ld ON d.document_id = ld.document_id
            JOIN LiberationDocumentTypes lt ON ld.type_id = lt.type_id
            WHERE d.gamma_owner_id = ANY(%s);
            """,
            (super_ids,),
        )
        uploaded = cur.fetchall()

    uploaded_by_owner: dict[str, set[str]] = {}
    for owner_id, type_name in uploaded:
        uploaded_by_owner.setdefault(owner_id, set()).add(type_name)

    result = []
    for req in requires:
        uploaded_types = uploaded_by_owner.get(req["super_group_id"], set())
        missing = [t for t in req["doc_types"] if t not in uploaded_types]
        if missing:
            result.append({**req, "missing": missing})
    return result


def has_sent_mail(
    mail_type: str, meeting_id: int | None, gamma_owner_id: str | None
) -> bool:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM SentMails
            WHERE mail_type = %s
              AND meeting_id IS NOT DISTINCT FROM %s
              AND gamma_owner_id IS NOT DISTINCT FROM %s;
            """,
            (mail_type, meeting_id, gamma_owner_id),
        )
        return cur.fetchone() is not None


def record_sent_mail(
    mail_type: str, meeting_id: int | None, gamma_owner_id: str | None
) -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            if gamma_owner_id is not None:
                # Satisfy the FK even for groups that never uploaded
                # anything and never had a requirement set.
                cur.execute(
                    "INSERT INTO DocumentOwners (gamma_owner_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                    (gamma_owner_id,),
                )
                cur.execute(
                    "INSERT INTO Committees (gamma_group_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                    (gamma_owner_id,),
                )
            cur.execute(
                """
                INSERT INTO SentMails (mail_type, meeting_id, gamma_owner_id)
                VALUES (%s, %s, %s)
                ON CONFLICT ON CONSTRAINT sent_mails_unique DO NOTHING;
                """,
                (mail_type, meeting_id, gamma_owner_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_document_requires(meeting_id: int) -> dict[str, list[str]]:
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
    except Exception:
        logger.exception("set_document_require failed")
        conn.rollback()
        raise


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
    except Exception:
        logger.exception("remove_document_require failed")
        conn.rollback()
        raise
