"""Настройки бота: токен, услуги, рабочее время.

Чтобы адаптировать бота под нового клиента, обычно достаточно поменять этот файл.
"""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
_admin = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(_admin) if _admin.isdigit() else None

SALON_NAME = "Beauty Studio"
SALON_INFO = (
    "💇 <b>Beauty Studio</b>\n"
    "📍 ул. Примерная, 10\n"
    "🕙 Пн–Сб, 10:00–19:00\n"
    "📞 +380 00 000 00 00"
)

# Услуги: (название, цена)
SERVICES = [
    ("Женская стрижка", "500 грн"),
    ("Мужская стрижка", "300 грн"),
    ("Маникюр", "450 грн"),
    ("Окрашивание", "от 1200 грн"),
]

# Рабочие часы: слоты по 1 часу с WORK_START до WORK_END (не включительно)
WORK_START = 10
WORK_END = 19
DAYS_AHEAD = 7          # на сколько дней вперёд можно записаться
DAYS_OFF = {6}          # выходные: 0=Пн ... 6=Вс
REMIND_HOURS_BEFORE = 24  # за сколько часов напоминать клиенту о записи
