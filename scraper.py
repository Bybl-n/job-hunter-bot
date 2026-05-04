import json
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from config import SEARCH_QUERIES, CITY_ID

def create_driver():
    import shutil
    import platform
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Определяем окружение
    is_docker = os.path.exists("/.dockerenv")
    
    if is_docker:
        # В Docker пути фиксированные
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        # Локально — автопоиск или ChromeDriverManager
        chromium_path = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        chromedriver_path = shutil.which("chromedriver")
        
        if chromium_path:
            options.binary_location = chromium_path
        
        if chromedriver_path:
            service = Service(chromedriver_path)
        else:
            service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    return driver


def handle_vpn_check(driver):
    if "vpncheck" not in driver.current_url:
        return

    print("  Обнаружен vpncheck, пробую пройти...")
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="vpn-check__button"]'))
        )
        btn.click()
        time.sleep(3)
        print("  Прошел vpncheck")
    except Exception:
        try:
            btns = driver.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                if "не использую" in btn.text.lower() or "продолжить" in btn.text.lower():
                    btn.click()
                    time.sleep(3)
                    print("  Прошел vpncheck через текст кнопки")
                    return
        except Exception as e:
            print(f"  Не удалось пройти vpncheck: {e}")


def get_vacancies(query, driver):
    url = f"https://hh.ru/search/vacancy?text={query}&area={CITY_ID}&per_page=10"

    try:
        driver.get(url)
        time.sleep(random.uniform(2, 3))

        handle_vpn_check(driver)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select('[data-qa="vacancy-serp__vacancy"]')

        print(f"  Найдено карточек: {len(cards)}")

        vacancies = []
        for card in cards:
            try:
                title_elem = card.select_one('[data-qa="serp-item__title"]')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url_vacancy = title_elem.get("href", "").split("?")[0]
                vacancy_id = url_vacancy.split("/")[-1]

                company_elem = card.select_one('[data-qa="vacancy-serp__vacancy-employer-text"]')
                company = company_elem.get_text(strip=True) if company_elem else "Не указана"

                salary_elem = card.select_one('[data-qa="vacancy-serp__vacancy-compensation"]') or \
                              card.select_one('[data-qa="vacancy-serp__vacancy-salary"]')
                salary = salary_elem.get_text(strip=True) if salary_elem else "не указана"

                snippet_elem = card.select_one('[data-qa="vacancy-serp__vacancy-snippet-requirement"]')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                vacancies.append({
                    "id": vacancy_id,
                    "title": title,
                    "company": company,
                    "salary": salary,
                    "url": url_vacancy,
                    "snippet": snippet,
                })

            except Exception as e:
                print(f"  Ошибка парсинга карточки: {e}")
                continue

        return vacancies

    except Exception as e:
        print(f"  Ошибка при загрузке [{query}]: {e}")
        return []


def get_full_description(url, driver):
    if not url:
        return ""
    try:
        print(f"  Загружаю описание: {url.split('/')[-1]}")
        driver.get(url)
        time.sleep(random.uniform(1.5, 2.5))
        handle_vpn_check(driver)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        desc_elem = soup.select_one('[data-qa="vacancy-description"]')
        return desc_elem.get_text(strip=True)[:1500] if desc_elem else ""
    except Exception:
        return ""


def load_seen_jobs():
    try:
        with open("seen_jobs.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen_jobs(seen_ids):
    with open("seen_jobs.json", "w") as f:
        json.dump(list(seen_ids), f)


def is_relevant_title(title):
    stop_words = [
        "senior", "lead", "middle", "director", "руководитель",
        "главный", "ведущий", "старший", "head", "chief", "директор"
    ]
    return not any(word in title.lower() for word in stop_words)


def fetch_all_vacancies():
    seen_ids = load_seen_jobs()
    all_vacancies = []
    unique_ids = set()

    driver = create_driver()

    try:
        driver.get("https://hh.ru")
        time.sleep(random.uniform(2, 3))
        handle_vpn_check(driver)

        for i, query in enumerate(SEARCH_QUERIES):
            print(f"\nЗапрос: {query}")
            vacancies = get_vacancies(query, driver)

            for vacancy in vacancies:
                vid = vacancy["id"]
                if vid not in seen_ids and vid not in unique_ids:
                    if is_relevant_title(vacancy["title"]):
                        full_desc = get_full_description(vacancy["url"], driver)
                        if full_desc:
                            vacancy["snippet"] = full_desc
                        all_vacancies.append(vacancy)
                        unique_ids.add(vid)

            if i < len(SEARCH_QUERIES) - 1:
                time.sleep(random.uniform(3, 5))

    finally:
        driver.quit()

    save_seen_jobs(seen_ids | unique_ids)
    print(f"\nИтого новых вакансий: {len(all_vacancies)}")
    return all_vacancies


if __name__ == "__main__":
    vacancies = fetch_all_vacancies()
    for v in vacancies:
        print(f"{v['title']} — {v['company']}")
