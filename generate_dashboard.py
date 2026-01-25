import json
from datetime import date, datetime
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


def normalize_item(item: dict) -> dict | None:
    item_date = parse_date(item.get("date"))
    if not item_date:
        return None
    payload = {
        "title": str(item.get("title", "(untitled)")),
        "date": item_date.isoformat(),
    }
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
    if item.get("notes"):
        payload["notes"] = str(item["notes"])
    if item.get("tag"):
        payload["tag"] = str(item["tag"])

    date_value = item.get("date") or item.get("next_occurrence")
    parsed = parse_date(date_value)
    if parsed:
        if item.get("date"):
            payload["date"] = parsed.isoformat()
        else:
            payload["next_occurrence"] = parsed.isoformat()
        payload["days_until"] = (parsed - date.today()).days

    return payload


def sort_right(items: list[dict]) -> list[dict]:
    def key(item: dict) -> str:
        return item.get("date") or item.get("next_occurrence") or "9999-12-31"

    return sorted(items, key=key)


def main() -> None:
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

    output = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "left": split_left_items(left_items),
        "right": sort_right(right_items),
    }

    (OUTPUT_DIR / "dashboard.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
