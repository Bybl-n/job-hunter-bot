import json
from datetime import datetime

APPLIED_FILE = "applied.json"
VACANCIES_CACHE_FILE = "vacancies_cache.json"


def load_applied():
    try:
        with open(APPLIED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_applied(applied):
    with open(APPLIED_FILE, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)


def add_application(vacancy_id, title, company, url):
    applied = load_applied()

    for item in applied:
        if item["vacancy_id"] == vacancy_id:
            return False

    applied.append({
        "vacancy_id": vacancy_id,
        "title": title,
        "company": company,
        "url": url,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "timestamp": datetime.now().isoformat(),
        "status": "waiting"
    })

    save_applied(applied)
    return True


def update_status(vacancy_id, new_status):
    applied = load_applied()
    for item in applied:
        if item["vacancy_id"] == vacancy_id:
            item["status"] = new_status
            save_applied(applied)
            return True
    return False


def get_by_status():
    applied = load_applied()

    groups = {
        "waiting": [],
        "interview": [],
        "offer": [],
        "rejected": []
    }

    for item in applied:
        status = item.get("status", "waiting")
        if status in groups:
            groups[status].append(item)

    return groups


def days_ago(timestamp):
    try:
        date = datetime.fromisoformat(timestamp)
        delta = datetime.now() - date
        days = delta.days
        if days == 0:
            return "сегодня"
        elif days == 1:
            return "1 день назад"
        elif days < 5:
            return f"{days} дня назад"
        else:
            return f"{days} дней назад"
    except Exception:
        return "недавно"


def save_vacancy_cache(vacancies):
    try:
        try:
            with open(VACANCIES_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except FileNotFoundError:
            cache = {}

        for v in vacancies:
            vid = str(v["id"])[:30]
            cache[vid] = {
                "title": v.get("title", ""),
                "company": v.get("company", ""),
                "url": v.get("url", ""),
            }

        with open(VACANCIES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ошибка сохранения кэша: {e}")


def get_vacancy_from_cache(vacancy_id):
    try:
        with open(VACANCIES_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        return cache.get(vacancy_id, {})
    except FileNotFoundError:
        return {}