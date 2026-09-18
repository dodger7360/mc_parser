from playwright.sync_api import sync_playwright
from datetime import datetime
import sys


from cities import CITIES


from history import (
    save_snapshot,
    prepare_snapshot,
    load_latest_snapshot_before,
    compare_snapshots,
    calculate_dynamics
)


TARGETS = {
    "A500C": [
        ("6", "6000", "А500С", "6 6м"),
        ("6", "мотки", "А500С", "6 бухта"),

        ("8", "11700", "А500С", "8 11,7м"),
        ("8", "6000", "А500С", "8 6м"),
        ("8", "мотки", "А500С", "8 бухта"),

        ("10", "11700", "А500С", "10"),
        ("10", "мотки", "А500С", "10 бухта"),

        ("12", "11700", "А500С", "12"),
        ("12", "мотки", "А500С", "12 бухта"),

        ("14", "11700", "А500С", "14"),
        ("16", "11700", "А500С", "16"),
        ("18", "11700", "А500С", "18"),
        ("20", "11700", "А500С", "20"),
        ("22", "11700", "А500С", "22"),
        ("25", "11700", "А500С", "25"),
        ("28", "11700", "А500С", "28"),
        ("32", "11700", "А500С", "32"),
        ("36", "11700", "А500С", "36"),
        ("40", "11700", "А500С", "40"),
    ],

    "A1": [
        ("6", "6000", "Ст3", "6"),
        ("6", "мотки", "А240", "6 бухта"),
        ("10", "11700", "А240С", "10 11,7м"),
        ("10", "мотки", "А240С", "10 бухта"),
        ("14", "11700", "А240", "14 11,7м"),
    ],

    "At800": [
        ("14", "7600", "", "14"),
    ],

    "Лист": [
        ("3", "", "Ст3", "3мм Ст3"),
        ("4", "", "Ст3", "4мм Ст3"),
    ],

    "Уголок": [
        ("40х4", "6000", "Ст3", "40х4 6000"),
        ("40х4", "12000", "Ст3", "40х4 12000"),
        ("45х5", "6000", "Ст3", "45х5"),
        ("50х5", "6000", "Ст3", "50х5 6000"),
        ("50х5", "12000", "Ст3", "50х5 12000"),
        ("63х5", "6000", "Ст3", "63х5"),
        ("75х5", "6000", "Ст3", "75х5"),
    ],

    "Швеллер": [
        ("10", "6000", "Ст3", "10 У"),
        ("12", "12000", "Ст3", "12 П"),
        ("12", "6000", "Ст3", "12 У"),
        ("14", "12000", "Ст3", "14 П"),
        ("14", "6000", "Ст3", "14 У"),
        ("16", "12000", "Ст3", "16 У"),
        ("18", "12000", "Ст3", "18 У"),
        ("22", "12000", "Ст3", "22 П"),
        ("30", "12000", "Ст3", "30 У"),
    ],

    "Полоса": [
        ("40х4", "6000", "Ст3", "40х4"),
        ("50х4", "6000", "Ст3", "50х4"),
        ("50х5", "6000", "Ст3", "50х5"),
        ("100х10", "6000", "Ст3", "100х10"),
    ],

    "Проволока": [
        ("1.2", "", "отожженная", "1,2 отожженная"),
    ],

    "ВР-1": [
        ("4", "", "", "4"),
        ("5", "", "", "5"),
    ],
}


SECTION_NAMES = {
    "A500C": "Арматура А500С:",
    "A1": "Арматура А1:",
    "At800": "Арматура At800:",
    "Лист": "Лист горячекатаный:",
    "Уголок": "Уголок Ст3:",
    "Швеллер": "Швеллер Ст3:",
    "Полоса": "Полоса Ст3:",
    "Проволока": "Проволока торговая:",
    "ВР-1": "Проволока ВР-1:",
}


def clean(text):
    text = text.replace("\xa0", " ")
    return " ".join(text.split()).strip()


def normalize_size(value):
    value = clean(value)
    value = value.replace(",", ".")
    return value


def normalize_price(value):
    value = clean(value)

    if value.lower() in ("заказ", ""):
        return None

    value = value.replace("₽", "")
    value = value.replace(" ", "")

    if not value.isdigit():
        return None

    return int(value)


def format_price(price):
    if price is None:
        return "нет"

    return f"{price:,}".replace(",", " ")


def get_page_rows(page, url):
    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(2500)

    try:
        page.wait_for_selector(
            "#grid_tab",
            timeout=15000
        )
    except:
        pass

    if "check-human" in page.url:
        raise RuntimeError(
            "Metalservice отправил страницу на check-human"
        )

    trs = page.locator("#grid_tab tr").all()

    result = []

    for tr in trs:
        cells = tr.locator("td").all()

        if not cells:
            continue

        row = []

        for cell in cells:
            row.append(
                clean(cell.inner_text())
            )

        result.append(row)

    return result


def find_price(
    rows,
    target_size,
    target_length,
    target_grade,
    region_filter,
    warehouse_filter
):
    target_size = normalize_size(target_size)
    target_length = normalize_size(target_length)
    target_grade = clean(target_grade)

    prices = []

    for row in rows:

        if len(row) < 8:
            continue

        name = clean(row[0])
        size = normalize_size(row[1])
        grade = clean(row[2])
        length = normalize_size(row[3])
        region = clean(row[4])

        if region_filter and region_filter not in region:
            continue

        if warehouse_filter and warehouse_filter not in region:
            continue

        if "х" in target_size.lower():
            if target_size.lower() not in name.lower():
                continue
        else:
            if size != target_size:
                continue

        if target_grade and grade != target_grade:
            continue

        if target_length and length != target_length:
            continue

        price = normalize_price(row[7])

        if price is not None:
            prices.append(price)

    if not prices:
        return None

    return min(prices)


def prepare_city_snapshot(all_data, city_config):
    snapshot = {}

    for group, group_targets in TARGETS.items():
        snapshot[group] = []

        rows = all_data.get(group, [])

        for size, length, grade, output_name in group_targets:

            price = find_price(
                rows,
                size,
                length,
                grade,
                city_config["region_filter"],
                city_config["warehouse_filter"]
            )

            snapshot[group].append({
                "name": output_name,
                "price": price
            })

    return snapshot


def build_report(city_config, snapshot):
    today = datetime.now().strftime("%d.%m.%Y")

    lines = []

    lines.append(
        f"МС {city_config['name']} {today}"
    )

    lines.append(
        city_config["discount_text"]
    )

    lines.append("")

    for group, targets in TARGETS.items():

        lines.append(SECTION_NAMES[group])
        lines.append("")

        positions = snapshot.get(group, [])

        for index, target in enumerate(targets):

            output_name = target[3]

            if index >= len(positions):
                continue

            price = positions[index]["price"]

            lines.append(
                f"{output_name} – {format_price(price)}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()


def build_report_with_dynamics(
    city_config,
    snapshot,
    dynamics,
    previous_date
):
    today = datetime.now().strftime("%d.%m.%Y")

    lines = []

    lines.append(
        f"МС {city_config['name']} {today}"
    )

    lines.append(
        city_config["discount_text"]
    )

    lines.append("")

    for group, targets in TARGETS.items():

        lines.append(SECTION_NAMES[group])
        lines.append("")

        group_dynamics = dynamics.get(group, [])

        for index, target in enumerate(targets):

            output_name = target[3]

            if index >= len(group_dynamics):
                continue

            item = group_dynamics[index]

            current = item["current"]
            dynamics_text = item["dynamics"]

            current_text = format_price(current)

            lines.append(
                f"{output_name} – {current_text} ({dynamics_text})"
            )

        lines.append("")

    lines.append(
        f"Сравнение с {previous_date.strftime('%d.%m.%Y')}"
    )

    return "\n".join(lines).rstrip()


def run_city(page, city_code, city_config):

    print()
    print(f"Загрузка цен Metalservice — {city_code}")
    print()

    all_data = {}

    for name, url in city_config["urls"].items():

        try:
            rows = get_page_rows(page, url)

            all_data[name] = rows

            print(
                f"{name}: OK ({len(rows)} строк)"
            )

        except Exception as e:

            print(
                f"{name}: ОШИБКА — {e}"
            )

            all_data[name] = []

    snapshot = prepare_city_snapshot(
        all_data,
        city_config
    )

    save_snapshot(
        snapshot,
        city_code
    )

    previous_date, previous = load_latest_snapshot_before(
        city_code
    )

    if previous:

        comparison = compare_snapshots(
            snapshot,
            previous
        )

        dynamics = calculate_dynamics(
            comparison
        )

        report = build_report_with_dynamics(
            city_config,
            snapshot,
            dynamics,
            previous_date
        )

    else:

        report = build_report(
            city_config,
            snapshot
        )

    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТ")
    print("=" * 60)
    print()
    print(report)
    print()
    print(f"История {city_code} сохранена.")

    return snapshot


def main():

    print("Выберите город:")
    print("1 — ЕКБ")
    print("2 — МСК")
    print("3 — оба")

    choice = input("Ваш выбор: ").strip()

    if choice == "1":
        cities = ["ЕКБ"]

    elif choice == "2":
        cities = ["МСК"]

    elif choice == "3":
        cities = ["ЕКБ", "МСК"]

    else:
        print("Неверный выбор.")
        return

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            locale="ru-RU",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            )
        )

        for city_code in cities:

            run_city(
                page,
                city_code,
                CITIES[city_code]
            )

        browser.close()


if __name__ == "__main__":
    main()