import asyncio
import schedule
import time
import threading
from scraper import fetch_all_vacancies
from claude_agent import filter_vacancies
from telegram_bot import send_digest, run_bot, send_menu
from config import SEND_TIME


async def run_job_async(chat_id=None):
    print("Запускаю поиск вакансий...")
   

    print("Шаг 1: Собираю вакансии с hh.ru...")
    vacancies = fetch_all_vacancies()

    if not vacancies:
        print("Новых вакансий не найдено.")
        await send_digest([], chat_id)
        return

    print(f"\nШаг 2: Оцениваю {len(vacancies)} вакансий...")
    suitable = filter_vacancies(vacancies)

    print(f"\nШаг 3: Отправляю дайджест в Telegram...")
    await send_digest(suitable, chat_id)

    print("\nГотово! Дайджест отправлен.")


def schedule_loop(loop):
    def run():
        asyncio.run_coroutine_threadsafe(run_job_async(), loop)

    schedule.every().day.at(SEND_TIME).do(run)
    while True:
        schedule.run_pending()
        time.sleep(60)


async def main():
    print(f"Job Hunter Bot запущен. Автодайджест каждый день в {SEND_TIME}")
    print("Напиши /start боту в Telegram чтобы начать\n")

    loop = asyncio.get_event_loop()
    thread = threading.Thread(target=schedule_loop, args=(loop,), daemon=True)
    thread.start()

    await send_menu()
    await run_bot()


if __name__ == "__main__":
    asyncio.run(main())