import json
from pathlib import Path
from datetime import date, timedelta


HISTORY_DIR = Path(__file__).parent / "history"


def save_snapshot(data, city, snapshot_date=None):
    if snapshot_date is None:
        snapshot_date = date.today()

    city_dir = HISTORY_DIR / city.lower()
    city_dir.mkdir(parents=True, exist_ok=True)

    file_path = city_dir / f"{snapshot_date.isoformat()}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return file_path


def load_snapshot(city, snapshot_date):
    file_path = (
        HISTORY_DIR
        / city.lower()
        / f"{snapshot_date.isoformat()}.json"
    )

    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def previous_working_day(snapshot_date=None):
    if snapshot_date is None:
        snapshot_date = date.today()

    current = snapshot_date - timedelta(days=1)

    while current.weekday() >= 5:
        current -= timedelta(days=1)

    return current


def load_previous_working_day(city, snapshot_date=None):
    if snapshot_date is None:
        snapshot_date = date.today()

    current = previous_working_day(snapshot_date)

    while True:
        snapshot = load_snapshot(city, current)

        if snapshot is not None:
            return current, snapshot

        current -= timedelta(days=1)


def compare_snapshots(current, previous):
    result = {}

    for group, positions in current.items():
        result[group] = []

        previous_positions = previous.get(group, [])

        previous_by_name = {
            item["name"]: item["price"]
            for item in previous_positions
        }

        for item in positions:
            name = item["name"]
            current_price = item["price"]
            previous_price = previous_by_name.get(name)

            result[group].append({
                "name": name,
                "current": current_price,
                "previous": previous_price
            })

    return result


def prepare_snapshot(all_data, targets, find_price_func, **kwargs):
    snapshot = {}

    for group, group_targets in targets.items():
        snapshot[group] = []

        rows = all_data.get(group, [])

        for size, length, grade, output_name in group_targets:
            price = find_price_func(
                rows,
                size,
                length,
                grade,
                **kwargs
            )

            snapshot[group].append({
                "name": output_name,
                "price": price
            })

    return snapshot


def calculate_dynamics(comparison):
    result = {}

    for group, positions in comparison.items():
        result[group] = []

        for item in positions:
            current = item["current"]
            previous = item["previous"]

            if current is None and previous is None:
                dynamics = "нет"

            elif current is None:
                dynamics = f"было: {previous}"

            elif previous is None:
                dynamics = "было: нет"

            else:
                difference = current - previous

                if difference > 0:
                    dynamics = f"+{difference}"
                elif difference < 0:
                    dynamics = str(difference)
                else:
                    dynamics = "0"

            result[group].append({
                "name": item["name"],
                "current": current,
                "previous": previous,
                "dynamics": dynamics
            })

    return result


def load_latest_snapshot_before(city, snapshot_date=None):
    if snapshot_date is None:
        snapshot_date = date.today()

    current = snapshot_date - timedelta(days=1)

    while current >= date(2020, 1, 1):
        snapshot = load_snapshot(city, current)

        if snapshot is not None:
            return current, snapshot

        current -= timedelta(days=1)

    return None, None