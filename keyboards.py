"""Кнопки бота."""
from datetime import date, datetime, timedelta

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)

import config

BTN_BOOK = "📅 Записаться"
BTN_MY = "📋 Мои записи"
BTN_INFO = "ℹ️ О нас"

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BOOK)],
                  [KeyboardButton(text=BTN_MY), KeyboardButton(text=BTN_INFO)]],
        resize_keyboard=True,
    )


def services() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{name} — {price}", callback_data=f"svc:{i}")]
            for i, (name, price) in enumerate(config.SERVICES)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dates(closed: set[str] = frozenset()) -> InlineKeyboardMarkup:
    today = date.today()
    buttons = []
    for offset in range(config.DAYS_AHEAD + 1):
        d = today + timedelta(days=offset)
        if d.weekday() in config.DAYS_OFF or d.isoformat() in closed:
            continue
        label = f"{WEEKDAYS[d.weekday()]} {d.strftime('%d.%m')}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"date:{d.isoformat()}"))
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:services")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times(day: str, busy: set[str]) -> InlineKeyboardMarkup | None:
    """Свободные часы на день. None — если свободных нет."""
    now = datetime.now()
    buttons = []
    for hour in range(config.WORK_START, config.WORK_END):
        t = f"{hour:02d}:00"
        slot = datetime.fromisoformat(f"{day}T{t}")
        if t in busy or slot <= now:
            continue
        buttons.append(InlineKeyboardButton(text=t, callback_data=f"time:{t}"))
    if not buttons:
        return None
    rows = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:dates")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def share_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
    ]])


def cancel_booking(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отменить запись", callback_data=f"cancel:{booking_id}")
    ]])
