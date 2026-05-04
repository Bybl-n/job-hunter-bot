import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEARCH_QUERIES = [
    "аналитик данных стажировка",
    "data analyst intern",
    "продуктовый аналитик стажировка"
]

CITY = "Москва"
CITY_ID = "1"

MIN_SCORE = 6
SEND_TIME = "22:55"
TEST_MODE = False
MAX_VACANCIES_TO_EVALUATE = 15
