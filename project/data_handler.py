from project.database import get_db
import datetime
from enum import IntEnum
from dataclasses import dataclass
from pathlib import Path
import os
import hashlib

UPLOAD_BASE: Path = Path("/")/"data"/"uploads"

class LP(IntEnum):
    LP1 = 1
    LP2 = 2
    LP3 = 3
    LP4 = 4
    SUMMER = 5

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


def create_meeting(meeting_date: datetime.date, study_period: StudyPeriod) -> Meeting | None:
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

def upload_document(the_file: bytes, file_name: str, document_owner: DocumentOwner) -> Document:
    conn = get_db()
    file_hash = hashlib.md5(the_file)
    file_path = UPLOAD_BASE/(f"{file_hash.hexdigest()}_{file_name}")

    create_document_owner(document_owner)

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
        
        document = Document(
            _id = document_id,
            name = file_name,
            owner = document_owner,
            file_path = file_path,
            uploaded = timestamp,
        )
        if file_path.is_file():
            raise Exception("File already exists...?")
        with file_path.open("wb") as f: f.write(the_file)
        conn.commit()
    except:
        conn.rollback()
        raise
    return document

def create_document_owner(document_owner: DocumentOwner):
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
    except:
        conn.rollback()
        raise   