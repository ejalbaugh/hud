import json
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


WEEKDAY_INDEX = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


def normalize_item(item: dict) -> dict | None:
    item_date = parse_date(item.get("date"))
    if not item_date:
        return None
    payload = {
        "title": str(item.get("title", "(untitled)")),
        "date": item_date.isoformat(),
    }
    if item.get("time"):
        payload["time"] = str(item["time"])
    if item.get("notes"):
        payload["notes"] = str(item["notes"])
    if item.get("tag"):
        payload["tag"] = str(item["tag"])
    return payload


def add_days_until(items: list[dict]) -> list[dict]:
    today = date.today()
    enriched = []
    for item in items:
        item_date = parse_date(item["date"])
        if not item_date:
            continue
        entry = dict(item)
        entry["days_until"] = (item_date - today).days
        enriched.append(entry)
    return enriched


def split_left_items(items: list[dict]) -> dict:
    now: list[dict] = []
    soon: list[dict] = []
    landmarks: list[dict] = []

    for item in add_days_until(items):
        if item["days_until"] < 0:
            continue
        if item["days_until"] <= 7:
            now.append(item)
        elif item["days_until"] <= 30:
            soon.append(item)
        else:
            landmarks.append(item)

    now.sort(key=lambda i: i["date"])
    soon.sort(key=lambda i: i["date"])
    landmarks.sort(key=lambda i: i["date"])

    return {"now": now, "soon": soon, "landmarks": landmarks}


def normalize_right_item(item: dict) -> dict | None:
    title = item.get("title")
    if not title:
        return None
    payload = {"title": str(title)}
    if item.get("time"):
        payload["time"] = str(item["time"])
    if item.get("notes"):
        payload["notes"] = str(item["notes"])
    if item.get("tag"):
        payload["tag"] = str(item["tag"])

    recurrence = item.get("recurrence")
    if isinstance(recurrence, dict):
        days = recurrence.get("days")
        if isinstance(days, list) and days:
            payload["recurrence"] = {
                "freq": "weekly",
                "days": [str(day) for day in days],
            }
            if recurrence.get("time"):
                payload["recurrence"]["time"] = str(recurrence["time"])
            return payload

    date_value = item.get("date") or item.get("next_occurrence")
    parsed = parse_date(date_value)
    if parsed:
        if item.get("date"):
            payload["date"] = parsed.isoformat()
        else:
            payload["next_occurrence"] = parsed.isoformat()
        payload["days_until"] = (parsed - date.today()).days

    return payload


def normalize_weekdays(days: list[str]) -> list[int]:
    normalized = []
    for day in days:
        key = str(day).strip().lower()
        if key in WEEKDAY_INDEX:
            normalized.append(WEEKDAY_INDEX[key])
    return sorted(set(normalized))


def next_weekday_occurrence(start: date, weekdays: list[int]) -> date | None:
    for offset in range(0, 28):
        candidate = start + timedelta(days=offset)
        if candidate.weekday() in weekdays:
            return candidate
    return None


def build_recurring_occurrences(items: list[dict], start: date, days: int = 28) -> list[dict]:
    occurrences: list[dict] = []
    for item in items:
        recurrence = item.get("recurrence") or {}
        weekdays = normalize_weekdays(recurrence.get("days", []))
        if not weekdays:
            continue
        for offset in range(days):
            current = start + timedelta(days=offset)
            if current.weekday() in weekdays:
                entry = {
                    "title": item["title"],
                    "date": current.isoformat(),
                    "source": "recurring",
                }
                time_value = recurrence.get("time") or item.get("time")
                if time_value:
                    entry["time"] = str(time_value)
                occurrences.append(entry)
    return occurrences


def build_today_list(
    today: date,
    left_items: list[dict],
    appointments: list[dict],
    recurring_occurrences: list[dict],
) -> list[dict]:
    today_iso = today.isoformat()
    items: list[dict] = []

    for item in left_items:
        if item["date"] == today_iso:
            items.append(
                {
                    "title": item["title"],
                    "date": item["date"],
                    "time": item.get("time"),
                    "source": "left",
                }
            )

    for item in appointments:
        date_value = item.get("date") or item.get("next_occurrence")
        if date_value == today_iso:
            items.append(
                {
                    "title": item["title"],
                    "date": date_value,
                    "time": item.get("time"),
                    "source": "appointment",
                }
            )

    for item in recurring_occurrences:
        if item["date"] == today_iso:
            items.append(
                {
                    "title": item["title"],
                    "date": item["date"],
                    "time": item.get("time"),
                    "source": "recurring",
                }
            )

    def sort_key(entry: dict) -> tuple:
        time_value = entry.get("time") or "99:99"
        return (time_value, entry["title"])

    return sorted(items, key=sort_key)


def sort_right(items: list[dict]) -> list[dict]:
    def key(item: dict) -> str:
        return item.get("date") or item.get("next_occurrence") or "9999-12-31"

    return sorted(items, key=key)


def main() -> None:
    today = date.today()
    left_items = []
    for path in [DATA_DIR / "left_column.json", DATA_DIR / "big_events.json"]:
        for raw in load_json(path):
            normalized = normalize_item(raw)
            if normalized:
                left_items.append(normalized)

    right_items = []
    for raw in load_json(DATA_DIR / "right_column.json"):
        normalized = normalize_right_item(raw)
        if normalized:
            right_items.append(normalized)

    recurring_items = [item for item in right_items if "recurrence" in item]
    appointment_items = [item for item in right_items if "recurrence" not in item]
    recurring_occurrences = build_recurring_occurrences(recurring_items, today, 28)

    for item in recurring_items:
        weekdays = normalize_weekdays(item["recurrence"].get("days", []))
        next_date = next_weekday_occurrence(today, weekdays)
        if next_date:
            item["next_occurrence"] = next_date.isoformat()
            item["days_until"] = (next_date - today).days

    calendar_items = [
        {"title": item["title"], "date": item["date"], "source": "left"}
        for item in left_items
        if 0 <= (parse_date(item["date"]) - today).days <= 27
    ] + [
        {"title": item["title"], "date": item["date"], "source": "recurring"}
        for item in recurring_occurrences
    ]

    def calendar_sort(entry: dict) -> tuple:
        return (entry["date"], entry["title"])

    calendar_items = sorted(calendar_items, key=calendar_sort)

    output = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "left": {
            "today": build_today_list(today, left_items, appointment_items, recurring_occurrences),
            **split_left_items(left_items),
        },
        "right": {
            "appointments": sort_right(appointment_items),
            "recurring": sort_right(recurring_items),
        },
        "calendar": calendar_items,
    }

    (OUTPUT_DIR / "dashboard.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
