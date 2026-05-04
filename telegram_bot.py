import asyncio
from dotenv import load_dotenv
load_dotenv()
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import applied as applied_module


bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_message_with_retry(chat_id, text, reply_markup=None, disable_web_page_preview=False, parse_mode=None):
    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            print(f"Попытка {attempt+1} не удалась: {e}")
            await asyncio.sleep(3)
    return False


def format_vacancy(vacancy):
    score = vacancy.get("score", 0)

    def escape(text):
        for char in ['_', '*', '[', ']', '`']:
            text = text.replace(char, f'\\{char}')
        return text

    title = escape(str(vacancy['title']))
    company = escape(str(vacancy['company']))
    salary = escape(str(vacancy['salary']))
    comment = escape(str(vacancy.get('comment', '')))

    text = (
        f"*{title}* — {company}\n"
        f"*Оценка:* {score}/10\n"
        f"*Зарплата:* {salary}\n"
        f"*DeepSeek:* {comment}\n"
    )

    if vacancy.get("red_flags"):
        red_flags = escape(str(vacancy['red_flags']))
        text += f"*Важно:* {red_flags}\n"

    vacancy_id = str(vacancy['id'])[:30]

    keyboard = [[
        InlineKeyboardButton("Открыть вакансию", url=vacancy['url']),
        InlineKeyboardButton("Откликнулся", callback_data=f"ap_{vacancy_id}")
    ]]

    return text, InlineKeyboardMarkup(keyboard)


async def send_digest(vacancies, chat_id=None):
    target = chat_id or TELEGRAM_CHAT_ID
    applied_module.save_vacancy_cache(vacancies)
    today = datetime.now().strftime("%d.%m.%Y")

    if not vacancies:
        await send_message_with_retry(
            target,
            f"Дайджест вакансий — {today}\n\nСегодня новых подходящих вакансий не найдено."
        )
        await send_menu(target)
        return

    header = (
        f"Дайджест вакансий — {today}\n"
        f"Найдено подходящих: {len(vacancies)}\n"
        f"{'─' * 30}"
    )
    await send_message_with_retry(target, header)

    for vacancy in vacancies:
        text, markup = format_vacancy(vacancy)
        await send_message_with_retry(
            target,
            text,
            reply_markup=markup,
            disable_web_page_preview=True,
            parse_mode="Markdown"
        )
        await asyncio.sleep(0.5)

    await send_menu(target)


async def send_menu(chat_id=None):
    target = chat_id or TELEGRAM_CHAT_ID
    keyboard = [[
        InlineKeyboardButton("Мои отклики", callback_data="show_applied"),
        InlineKeyboardButton("Запустить поиск", callback_data="run_digest")
    ]]
    await send_message_with_retry(
        target,
        "Выбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_applied_list(query):
    groups = applied_module.get_by_status()

    status_labels = {
        "waiting": "Жду ответа",
        "interview": "Интервью",
        "offer": "Оффер",
        "rejected": "Отказ"
    }

    text = "Мои отклики\n\n"
    has_any = False

    for status, label in status_labels.items():
        items = groups.get(status, [])
        text += f"{label} ({len(items)}):\n"
        if items:
            has_any = True
            for item in items:
                days = applied_module.days_ago(item["timestamp"])
                text += f"  — {item['title']}, {item['company']} • {days}\n"
        text += "\n"

    if not has_any:
        text += "Откликов пока нет.\nНажми кнопку под вакансией чтобы добавить!"

    keyboard = []
    all_applied = applied_module.load_applied()

    status_prefix = {
        "waiting": "[ждем]",
        "interview": "[интервью]",
        "offer": "[оффер]",
        "rejected": "[отказ]"
    }

    for item in all_applied:
        prefix = status_prefix.get(item["status"], "")
        keyboard.append([InlineKeyboardButton(
            f"{prefix} {item['title'][:25]} — сменить статус",
            callback_data=f"cs_{item['vacancy_id'][:20]}"
        )])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_menu")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_status_picker(query, vacancy_id):
    keyboard = [
        [InlineKeyboardButton("Жду ответа", callback_data=f"ss_{vacancy_id}_waiting")],
        [InlineKeyboardButton("Позвали на интервью", callback_data=f"ss_{vacancy_id}_interview")],
        [InlineKeyboardButton("Получил оффер", callback_data=f"ss_{vacancy_id}_offer")],
        [InlineKeyboardButton("Отказ", callback_data=f"ss_{vacancy_id}_rejected")],
        [InlineKeyboardButton("Назад", callback_data="show_applied")],
    ]
    await query.edit_message_text(
        text="Выбери новый статус:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    print(f"Нажата кнопка: {data}")

    if data.startswith("ap_"):
        vacancy_id = data[3:]
        vacancy_data = applied_module.get_vacancy_from_cache(vacancy_id)
        title = vacancy_data.get("title", "Вакансия")
        company = vacancy_data.get("company", "Компания")
        url = vacancy_data.get("url", "")

        added = applied_module.add_application(vacancy_id, title, company, url)
        if added:
            await query.answer("Отклик записан!", show_alert=True)
        else:
            await query.answer("Ты уже откликался!", show_alert=True)

    elif data == "show_applied":
        await show_applied_list(query)

    elif data.startswith("cs_"):
        vacancy_id = data[3:]
        await show_status_picker(query, vacancy_id)

    elif data.startswith("ss_"):
        parts = data.split("_")
        vacancy_id = parts[1]
        new_status = parts[2]
        applied_module.update_status(vacancy_id, new_status)
        status_names = {
            "waiting": "Жду ответа",
            "interview": "Интервью",
            "offer": "Оффер",
            "rejected": "Отказ"
        }
        await query.answer(f"Статус обновлен: {status_names.get(new_status)}", show_alert=True)
        await show_applied_list(query)

    elif data == "run_digest":
        await query.edit_message_text("Запускаю поиск... Результаты придут отдельным сообщением!")
        from main import run_job_async
        loop = asyncio.get_event_loop()
        loop.create_task(run_job_async(chat_id))

    elif data == "back_menu":
        keyboard = [[
            InlineKeyboardButton("Мои отклики", callback_data="show_applied"),
            InlineKeyboardButton("Запустить поиск", callback_data="run_digest")
        ]]
        await query.edit_message_text(
            text="Выбери действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Мои отклики", callback_data="show_applied"),
        InlineKeyboardButton("Запустить поиск", callback_data="run_digest")
    ]]
    await update.message.reply_text(
        "Job Hunter Bot\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Telegram бот запущен, жду команд...")
    await asyncio.Event().wait()