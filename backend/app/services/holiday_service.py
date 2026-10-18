from __future__ import annotations
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Holiday

# Authoritative dataset of all 24 supplied 2026 Tamil Nadu Government Public Holidays
# Officially verified against:
# Government of Tamil Nadu, Public (Miscellaneous) Department
# G.O.(Ms.) No. 708, dated November 11, 2025 (under Negotiable Instruments Act, 1881)
SUPPLIED_2026_HOLIDAYS = [
    {
        "s_no": 1,
        "holiday_name": "New Year's Day",
        "holiday_date": date(2026, 1, 1),
        "supplied_day": "Thursday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 2,
        "holiday_name": "Pongal",
        "holiday_date": date(2026, 1, 15),
        "supplied_day": "Thursday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 3,
        "holiday_name": "Thiruvalluvar Day",
        "holiday_date": date(2026, 1, 16),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 4,
        "holiday_name": "Uzhavar Thirunal",
        "holiday_date": date(2026, 1, 17),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 5,
        "holiday_name": "Republic Day",
        "holiday_date": date(2026, 1, 26),
        "supplied_day": "Monday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 6,
        "holiday_name": "Thai Poosam",
        "holiday_date": date(2026, 2, 1),
        "supplied_day": "Sunday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 7,
        "holiday_name": "Telugu New Year's Day",
        "holiday_date": date(2026, 3, 19),
        "supplied_day": "Thursday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 8,
        "holiday_name": "Ramzan (Idu'l Fitr)",
        "holiday_date": date(2026, 3, 21),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 9,
        "holiday_name": "Mahaveer Jayanthi",
        "holiday_date": date(2026, 3, 31),
        "supplied_day": "Tuesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 10,
        "holiday_name": "Annual closing of Accounts for Commercial Banks & Co-operative Banks",
        "holiday_date": date(2026, 4, 1),
        "supplied_day": "Wednesday",
        "holiday_type": "Bank Holiday",
        "applicability": "bank_only",  # Specifically restricted to commercial & co-op banks under G.O. Ms. No. 708
    },
    {
        "s_no": 11,
        "holiday_name": "Good Friday",
        "holiday_date": date(2026, 4, 3),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 12,
        "holiday_name": "Tamil New Year's Day / Dr. B.R. Ambedkar's Birthday",
        "holiday_date": date(2026, 4, 14),
        "supplied_day": "Tuesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 13,
        "holiday_name": "May Day",
        "holiday_date": date(2026, 5, 1),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 14,
        "holiday_name": "Bakrid (Idul Azha)",
        "holiday_date": date(2026, 5, 28),
        "supplied_day": "Thursday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 15,
        "holiday_name": "Muharram (Yaom-EShahadath)",
        "holiday_date": date(2026, 6, 26),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 16,
        "holiday_name": "Independence Day",
        "holiday_date": date(2026, 8, 15),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 17,
        "holiday_name": "Milad-un-Nabi (Prophet's Birthday)",
        "holiday_date": date(2026, 8, 26),
        "supplied_day": "Wednesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 18,
        "holiday_name": "Krishna Jayanthi",
        "holiday_date": date(2026, 9, 4),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 19,
        "holiday_name": "Vinayakar Chathurthi",
        "holiday_date": date(2026, 9, 14),
        "supplied_day": "Monday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 20,
        "holiday_name": "Gandhi Jayanthi",
        "holiday_date": date(2026, 10, 2),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 21,
        "holiday_name": "Ayutha Pooja",
        "holiday_date": date(2026, 10, 19),
        "supplied_day": "Monday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 22,
        "holiday_name": "Vijaya Dasami",
        "holiday_date": date(2026, 10, 20),
        "supplied_day": "Tuesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 23,
        "holiday_name": "Deepavali",
        "holiday_date": date(2026, 11, 8),
        "supplied_day": "Sunday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 24,
        "holiday_name": "Christmas",
        "holiday_date": date(2026, 12, 25),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
]

SOURCE_NAME = "Tamil Nadu Government Gazette Public Holidays 2026"
SOURCE_REF = "G.O.(Ms.) No. 708, Public (Miscellaneous) Department, dated 11.11.2025"

# Authoritative dataset of supplied 2027 Tamil Nadu Holidays (Part 4)
# Note: Marked as source_verified=0 pending official Government Order publication in late 2026
SUPPLIED_2027_HOLIDAYS = [
    {
        "s_no": 1,
        "holiday_name": "New Year's Day",
        "holiday_date": date(2027, 1, 1),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 2,
        "holiday_name": "Thai Pongal",
        "holiday_date": date(2027, 1, 15),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 3,
        "holiday_name": "Mattu Pongal / Thiruvalluvar Day",
        "holiday_date": date(2027, 1, 16),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 4,
        "holiday_name": "Farmers' Day / Kaanum Pongal",
        "holiday_date": date(2027, 1, 17),
        "supplied_day": "Sunday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
        "overlaps_sunday": True,
    },
    {
        "s_no": 5,
        "holiday_name": "Thaipusam",
        "holiday_date": date(2027, 1, 22),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 6,
        "holiday_name": "Republic Day",
        "holiday_date": date(2027, 1, 26),
        "supplied_day": "Tuesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 7,
        "holiday_name": "Ramzan Khutba",
        "holiday_date": date(2027, 3, 10),
        "supplied_day": "Wednesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 8,
        "holiday_name": "Good Friday",
        "holiday_date": date(2027, 3, 26),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 9,
        "holiday_name": "Bank Annual Closing of Accounts — banks only",
        "holiday_date": date(2027, 4, 1),
        "supplied_day": "Thursday",
        "holiday_type": "Bank Holiday",
        "applicability": "bank_only",
    },
    {
        "s_no": 10,
        "holiday_name": "Telugu New Year / Ugadi",
        "holiday_date": date(2027, 4, 7),
        "supplied_day": "Wednesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 11,
        "holiday_name": "Tamil New Year",
        "holiday_date": date(2027, 4, 14),
        "supplied_day": "Wednesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 12,
        "holiday_name": "Mahavir Jayanti",
        "holiday_date": date(2027, 4, 19),
        "supplied_day": "Monday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 13,
        "holiday_name": "May Day",
        "holiday_date": date(2027, 5, 1),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 14,
        "holiday_name": "Bakrid",
        "holiday_date": date(2027, 5, 17),
        "supplied_day": "Monday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 15,
        "holiday_name": "Muharram",
        "holiday_date": date(2027, 6, 16),
        "supplied_day": "Wednesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 16,
        "holiday_name": "Independence Day / Milad-un-Nabi",
        "holiday_date": date(2027, 8, 15),
        "supplied_day": "Sunday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
        "overlaps_sunday": True,
    },
    {
        "s_no": 17,
        "holiday_name": "Gokulashtami",
        "holiday_date": date(2027, 8, 24),
        "supplied_day": "Tuesday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 18,
        "holiday_name": "Vinayagar Chaturthi",
        "holiday_date": date(2027, 9, 4),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 19,
        "holiday_name": "Gandhi Jayanti",
        "holiday_date": date(2027, 10, 2),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 20,
        "holiday_name": "Saraswati Pooja / Ayutha Pooja",
        "holiday_date": date(2027, 10, 8),
        "supplied_day": "Friday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 21,
        "holiday_name": "Vijaya Dasami",
        "holiday_date": date(2027, 10, 9),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 22,
        "holiday_name": "Deepavali",
        "holiday_date": date(2027, 10, 28),
        "supplied_day": "Thursday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
    {
        "s_no": 23,
        "holiday_name": "Christmas",
        "holiday_date": date(2027, 12, 25),
        "supplied_day": "Saturday",
        "holiday_type": "Public Holiday",
        "applicability": "all",
    },
]

SOURCE_2027_NAME = "Supplied Tamil Nadu Holiday Calendar 2027"
SOURCE_2027_REF = "Supplied by Project Owner (Pending official Tamil Nadu Government Order release late 2026)"


def generate_sundays_calendar(
    start_date: date | None = None,
    end_date: date | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    """
    Programmatically generates all Sundays within the specified range (defaults 2026-01-01 to 2027-12-31).
    Validates that every generated date has weekday() == 6 (Sunday).
    First Sunday: 2026-01-04. Last Sunday: 2027-12-26. Total: 104 Sundays.
    Works recurringly for any year range beyond 2027.
    """
    if start_year:
        s_date = date(start_year, 1, 1)
    elif start_date:
        s_date = start_date
    else:
        s_date = date(2026, 1, 1)

    if end_year:
        e_date = date(end_year, 12, 31)
    elif end_date:
        e_date = end_date
    else:
        e_date = date(2027, 12, 31)

    current = s_date
    while current.weekday() != 6:
        current += timedelta(days=1)

    sundays = []
    while current <= e_date:
        sundays.append({
            "date": current.isoformat(),
            "year": current.year,
            "month": current.month,
            "day": current.day,
            "weekday_name": "Sunday",
            "weekday_idx": 6,
            "is_valid_sunday": (current.weekday() == 6),
        })
        current += timedelta(days=7)

    return {
        "ok": True,
        "total_sundays": len(sundays),
        "start_sunday": sundays[0]["date"] if sundays else None,
        "end_sunday": sundays[-1]["date"] if sundays else None,
        "first_sunday": sundays[0]["date"] if sundays else None,
        "last_sunday": sundays[-1]["date"] if sundays else None,
        "all_validated": all(s["is_valid_sunday"] for s in sundays),
        "sundays": sundays,
    }


def seed_2026_holidays(db: Session) -> dict:
    """
    Idempotently seeds all 24 supplied 2026 Tamil Nadu Government public holidays into PostgreSQL.
    Guarantees no duplicate records and preserves existing records.
    """
    inserted_count = 0
    existing_count = 0

    for item in SUPPLIED_2026_HOLIDAYS:
        h_date = item["holiday_date"]
        h_name = item["holiday_name"]

        existing = (
            db.query(Holiday)
            .filter(
                Holiday.holiday_date == h_date,
                Holiday.holiday_name == h_name,
            )
            .first()
        )

        if not existing:
            new_h = Holiday(
                holiday_date=h_date,
                holiday_name=h_name,
                holiday_type=item["holiday_type"],
                calendar_year=2026,
                source_name=SOURCE_NAME,
                source_reference=SOURCE_REF,
                source_verified=1,
                applicability=item["applicability"],
                is_active=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_h)
            inserted_count += 1
        else:
            existing_count += 1

    if inserted_count > 0:
        db.commit()

    total_2026 = db.query(Holiday).filter(Holiday.calendar_year == 2026).count()

    return {
        "ok": True,
        "inserted": inserted_count,
        "already_existing": existing_count,
        "total_2026_holidays": total_2026,
        "source_name": SOURCE_NAME,
        "source_reference": SOURCE_REF,
        "verified": True,
    }


def seed_2027_holidays(db: Session, force_active: bool = True) -> dict:
    """
    Idempotently imports all 23 supplied 2027 Tamil Nadu holidays into PostgreSQL (Part 4 & 5).
    - Preserves existing records.
    - Sets source_verified=0 (pending official Government Order release in late 2026).
    - Sets applicability='bank_only' for April 1 Annual closing of accounts.
    - Accurately tracks Sunday overlaps (Farmers' Day 2027-01-17 and Independence Day 2027-08-15).
    """
    inserted_count = 0
    existing_count = 0
    sunday_overlaps = []

    for item in SUPPLIED_2027_HOLIDAYS:
        h_date = item["holiday_date"]
        h_name = item["holiday_name"]

        if h_date.weekday() == 6:
            sunday_overlaps.append({"date": h_date.isoformat(), "name": h_name})

        existing = (
            db.query(Holiday)
            .filter(
                Holiday.holiday_date == h_date,
                Holiday.holiday_name == h_name,
            )
            .first()
        )

        if not existing:
            new_h = Holiday(
                holiday_date=h_date,
                holiday_name=h_name,
                holiday_type=item["holiday_type"],
                calendar_year=2027,
                source_name=SOURCE_2027_NAME,
                source_reference=SOURCE_2027_REF,
                source_verified=0,  # Explicitly marked as pending review / unverified official truth
                applicability=item["applicability"],
                is_active=1 if force_active else 0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_h)
            inserted_count += 1
        else:
            existing_count += 1

    if inserted_count > 0:
        db.commit()

    total_2027 = db.query(Holiday).filter(Holiday.calendar_year == 2027).count()

    return {
        "ok": True,
        "inserted": inserted_count,
        "already_existing": existing_count,
        "total_2027_holidays": total_2027,
        "source_name": SOURCE_2027_NAME,
        "source_reference": SOURCE_2027_REF,
        "verified": False,
        "sunday_overlaps": sunday_overlaps,
        "bank_only_count": sum(1 for h in SUPPLIED_2027_HOLIDAYS if h["applicability"] == "bank_only"),
    }


def seed_all_holidays(db: Session) -> dict:
    """Seeds both 2026 and 2027 holiday lists idempotently."""
    res_2026 = seed_2026_holidays(db)
    res_2027 = seed_2027_holidays(db)
    return {
        "ok": True,
        "2026": res_2026,
        "2027": res_2027,
    }


def get_all_holidays(db: Session, year: int | None = None) -> list[Holiday]:
    query = db.query(Holiday).filter(Holiday.is_active == 1)
    if year:
        query = query.filter(Holiday.calendar_year == year)
    return query.order_by(Holiday.holiday_date.asc()).all()


def is_holiday(db: Session, target_date: date, calendar_type: str = "company") -> tuple[bool, Holiday | None]:
    """
    Checks if target_date is an active holiday for the given calendar_type.
    For standard company employees, bank_only holidays (e.g. April 1 bank closing) do NOT apply.
    """
    query = db.query(Holiday).filter(
        Holiday.holiday_date == target_date,
        Holiday.is_active == 1,
    )
    if calendar_type == "company":
        query = query.filter(Holiday.applicability.in_(["all", "company"]))

    h = query.first()
    if h:
        return True, h
    return False, None


def is_weekly_off(target_date: date, off_days: tuple[int, ...] = (6,)) -> bool:
    """
    Weekly off check.
    In Mindful Metrics standard policy:
    Sunday (weekday() == 6) is the official recurring Weekly Off.
    Supports additional days (e.g. Saturday 5) if configured.
    """
    return target_date.weekday() in off_days
