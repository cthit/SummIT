from project.database import get_db
import datetime
from enum import IntEnum
from dataclasses import dataclass

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


def fetch_meetings() -> list[tuple[int, datetime.date, int]]:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT meeting_id, meeting_date, study_period_id
            FROM Meetings
            ORDER BY meeting_date DESC;
            """
        )
        return cur.fetchall()
    
def lookup_study_period(year: int, lp: LP) -> StudyPeriod | None:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT study_period_id, study_year, study_period
            FROM StudyPeriod
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
                INSERT INTO StudyPeriod (study_year, study_period)
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