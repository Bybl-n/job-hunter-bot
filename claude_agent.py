import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import requests
import json as json_lib
from config import MIN_SCORE, DEEPSEEK_API_KEY, TEST_MODE

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"


RELEVANT_KEYWORDS = [
    "аналитик", "analyst", "data", "данные", "python", "sql",
    "bi", "статистик", "researcher", "science", "ml",
    "machine learning", "стажёр", "intern", "стажировка"
]


SENIORITY_STOP_WORDS = [
    "senior", "lead", "middle", "director", "руководитель",
    "главный", "ведущий", "старший", "head", "chief", "директор"
]


def is_relevant_by_title(title):
    title_lower = title.lower()

    if any(kw in title_lower for kw in SENIORITY_STOP_WORDS):
        return False

    if not any(kw in title_lower for kw in RELEVANT_KEYWORDS):
        return False

    return True


def evaluate_vacancy(vacancy):
    if TEST_MODE:
        return {
            "score": 7,
            "comment": "Тестовый режим",
            "is_suitable": True,
            "red_flags": ""
        }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    title = str(vacancy.get("title", "")).strip()
    company = str(vacancy.get("company", "")).strip()
    salary = str(vacancy.get("salary", "")).strip()
    snippet = str(vacancy.get("snippet", ""))[:1500].strip()

    system_prompt = (
        "Ты HR-ассистент. Отвечаешь ТОЛЬКО валидным JSON без markdown и пояснений. "
        "Схема ответа: "
        "{\"score\": число_1_10, \"comment\": \"строка\", \"is_suitable\": true/false, \"red_flags\": \"строка\"}"
    )

    user_prompt = (
        f"Вакансия:\n"
        f"Название: {title}\n"
        f"Компания: {company}\n"
        f"Зарплата: {salary}\n"
        f"Описание: {snippet}\n\n"
        "Профиль соискателя:\n"
        "- Без опыта, ищет стажировку или Junior позицию в Москве\n"
        "- Стек: Python, SQL, Pandas, NumPy, Scikit-learn, BI, A/B тесты, статистика\n\n"
        "Правила оценки:\n"
        "1. Если вакансия не про аналитику данных, DS, BI или ML -> score: 1, is_suitable: false\n"
        "2. Если требуется опыт от 2 лет, или Middle/Senior/Lead -> score: 2, is_suitable: false\n"
        "3. Совпадение стека (Python, SQL, Pandas, A/B) -> +3 балла\n"
        "4. Топ-компания (Яндекс, Сбер, Тинькофф, Авито, Ozon, МТС, ВТБ, Kaspersky) -> +2 балла\n"
        "5. Обучение или менторство -> +1 балл\n"
        "6. Указана зарплата -> +1 балл\n"
        "7. Удалёнка или гибрид -> +1 балл\n"
        "8. Реальная аналитическая работа (метрики, дашборды, A/B тесты) -> +2 балла\n\n"
        "Верни JSON."
    )

    data = {
        "model": MODEL_NAME,
        "max_tokens": 300,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result_json = response.json()
        text = result_json["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json_lib.loads(text)

    except Exception as e:
        print(f"Ошибка DeepSeek API: {e}")
        return {"score": 0, "comment": "Ошибка LLM", "is_suitable": False, "red_flags": "Ошибка запроса"}


def filter_vacancies(vacancies):
    from config import MAX_VACANCIES_TO_EVALUATE

    pre_filtered = [v for v in vacancies if is_relevant_by_title(v["title"])]
    skipped = len(vacancies) - len(pre_filtered)
    if skipped > 0:
        print(f"Отсеяно по названию: {skipped}")

    pre_filtered = pre_filtered[:MAX_VACANCIES_TO_EVALUATE]
    print(f"Отправляю в LLM: {len(pre_filtered)}")

    suitable = []
    for i, vacancy in enumerate(pre_filtered):
        print(f"Оцениваю {i+1}/{len(pre_filtered)}: {vacancy['title']}")
        evaluation = evaluate_vacancy(vacancy)

        score = evaluation.get("score", 0)
        is_suitable = evaluation.get("is_suitable", False)
        comment = evaluation.get("comment", "")
        red_flags = evaluation.get("red_flags", "")

        if score >= MIN_SCORE and is_suitable:
            vacancy["score"] = score
            vacancy["comment"] = comment
            vacancy["red_flags"] = red_flags
            suitable.append(vacancy)
            print(f"  подходит: {score}/10")
        else:
            print(f"  не подходит: {score}/10 — {comment}")

    suitable.sort(key=lambda x: x["score"], reverse=True)
    print(f"Итого отобрано: {len(suitable)}/{len(pre_filtered)}")
    return suitable


if __name__ == "__main__":
    test = evaluate_vacancy({
        "title": "Junior Data Analyst",
        "company": "Яндекс",
        "salary": "от 80 000 руб.",
        "snippet": "Требуется SQL, Python, работа с метриками и A/B тестами. Менторство."
    })
    print(test)