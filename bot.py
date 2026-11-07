"""Telegram-бот для записи клиентов в салон.

Запуск:  python bot.py
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
import db
import keyboards as kb

dp = Dispatcher()


class Booking(StatesGroup):
    """Шаги записи: бот запоминает, на каком шаге находится клиент."""
    service = State()
    day = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{kb.WEEKDAYS[d.weekday()]} {d.strftime('%d.%m.%Y')}"


def closed_set() -> set[str]:
    return set(db.closed_days(date.today().isoformat()))


def parse_day(text: str) -> date | None:
    """'25.12' или '25.12.2026' -> дата. Без года — ближайшая будущая."""
    try:
        parts = [int(p) for p in text.strip().split(".")]
        if len(parts) == 3:
            return date(parts[2], parts[1], parts[0])
        if len(parts) == 2:
            d = date(date.today().year, parts[1], parts[0])
            return d if d >= date.today() else d.replace(year=d.year + 1)
    except ValueError:
        pass
    return None


# ---------- Общие команды ----------

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Здравствуйте! 👋 Это бот <b>{config.SALON_NAME}</b>.\n"
        "Здесь можно записаться на услугу за пару нажатий.",
        reply_markup=kb.main_menu(),
    )


@dp.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>")


@dp.message(F.text == kb.BTN_INFO)
async def info(message: Message):
    await message.answer(config.SALON_INFO)


# ---------- Запись: услуга -> дата -> время -> имя -> телефон -> подтверждение ----------

@dp.message(F.text == kb.BTN_BOOK)
async def book_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Booking.service)
    await message.answer("Выберите услугу:", reply_markup=kb.services())


@dp.callback_query(Booking.service, F.data.startswith("svc:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    name, _ = config.SERVICES[int(call.data.split(":")[1])]
    await state.update_data(service=name)
    await state.set_state(Booking.day)
    await call.message.edit_text(f"Услуга: <b>{name}</b>\nВыберите дату:",
                                 reply_markup=kb.dates(closed_set()))
    await call.answer()


@dp.callback_query(F.data == "back:services")
async def back_to_services(call: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.service)
    await call.message.edit_text("Выберите услугу:", reply_markup=kb.services())
    await call.answer()


@dp.callback_query(Booking.day, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    day = call.data.split(":", 1)[1]
    if day in closed_set():
        await call.answer("Этот день закрыт для записи", show_alert=True)
        return
    markup = kb.times(day, db.busy_times(day))
    if markup is None:
        await call.answer("На этот день свободного времени нет 😔", show_alert=True)
        return
    await state.update_data(day=day)
    await state.set_state(Booking.time)
    await call.message.edit_text(f"Дата: <b>{fmt_date(day)}</b>\nВыберите время:", reply_markup=markup)
    await call.answer()


@dp.callback_query(F.data == "back:dates")
async def back_to_dates(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(Booking.day)
    await call.message.edit_text(f"Услуга: <b>{data.get('service')}</b>\nВыберите дату:",
                                 reply_markup=kb.dates(closed_set()))
    await call.answer()


@dp.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    t = call.data.split(":", 1)[1]
    await state.update_data(time=t)
    await state.set_state(Booking.name)
    await call.message.edit_text(f"Время: <b>{t}</b>")
    await call.message.answer("Как к вам обращаться? Напишите имя:")
    await call.answer()


@dp.message(Booking.name, F.text)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:50])
    await state.set_state(Booking.phone)
    await message.answer("Оставьте номер телефона — нажмите кнопку или напишите его:",
                         reply_markup=kb.share_phone())


@dp.message(Booking.phone, F.contact | F.text)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text.strip()[:20]
    await state.update_data(phone=phone)
    await state.set_state(Booking.confirm)
    d = await state.get_data()
    await message.answer("Проверьте данные:", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        f"💇 {d['service']}\n📅 {fmt_date(d['day'])}, {d['time']}\n"
        f"👤 {d['name']}\n📞 {phone}",
        reply_markup=kb.confirm(),
    )


@dp.callback_query(Booking.confirm, F.data.startswith("confirm:"))
async def confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    d = await state.get_data()
    await state.clear()
    if call.data == "confirm:no":
        await call.message.edit_text("Запись отменена.")
        await call.message.answer("Главное меню:", reply_markup=kb.main_menu())
        await call.answer()
        return

    booking_id = db.add_booking(call.from_user.id, d["name"], d["phone"],
                                d["service"], d["day"], d["time"])
    if booking_id is None:
        await call.message.edit_text("😔 Это время только что заняли. Попробуйте выбрать другое.")
        await call.message.answer("Главное меню:", reply_markup=kb.main_menu())
        await call.answer()
        return

    await call.message.edit_text(
        f"✅ Вы записаны!\n💇 {d['service']}\n📅 {fmt_date(d['day'])}, {d['time']}\n\nЖдём вас!"
    )
    await call.message.answer("Главное меню:", reply_markup=kb.main_menu())
    await call.answer()

    if config.ADMIN_ID:
        await bot.send_message(
            config.ADMIN_ID,
            f"🆕 <b>Новая запись #{booking_id}</b>\n💇 {d['service']}\n"
            f"📅 {fmt_date(d['day'])}, {d['time']}\n👤 {d['name']}\n📞 {d['phone']}",
        )


# ---------- Мои записи и отмена ----------

@dp.message(F.text == kb.BTN_MY)
async def my_bookings(message: Message):
    rows = db.user_bookings(message.from_user.id, date.today().isoformat())
    if not rows:
        await message.answer("У вас пока нет записей.")
        return
    for r in rows:
        await message.answer(f"💇 {r['service']}\n📅 {fmt_date(r['date'])}, {r['time']}",
                             reply_markup=kb.cancel_booking(r["id"]))


@dp.callback_query(F.data.startswith("cancel:"))
async def cancel(call: CallbackQuery, bot: Bot):
    booking_id = int(call.data.split(":")[1])
    r = db.get_booking(booking_id)
    if r and db.delete_booking(booking_id, call.from_user.id):
        await call.message.edit_text(f"❌ Запись на {fmt_date(r['date'])}, {r['time']} отменена.")
        if config.ADMIN_ID:
            await bot.send_message(
                config.ADMIN_ID,
                f"❌ Отмена записи #{booking_id}: {r['service']}, "
                f"{fmt_date(r['date'])} {r['time']}, {r['name']} {r['phone']}",
            )
    else:
        await call.message.edit_text("Запись не найдена.")
    await call.answer()


# ---------- Для владельца ----------

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    rows = db.upcoming_bookings(date.today().isoformat())
    if not rows:
        await message.answer("Предстоящих записей нет.")
        return
    lines = [f"<b>{fmt_date(r['date'])} {r['time']}</b> — {r['service']}, {r['name']}, {r['phone']}"
             for r in rows]
    await message.answer("📋 Предстоящие записи:\n\n" + "\n".join(lines))


ADMIN_HELP = (
    "Команды владельца:\n"
    "/admin — предстоящие записи\n"
    "/close 25.12 — закрыть день для записи\n"
    "/open 25.12 — открыть день снова\n"
    "/closed — список закрытых дней"
)


@dp.message(Command("close", "open"))
async def close_open_day(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    cmd, _, arg = message.text.partition(" ")
    d = parse_day(arg)
    if d is None:
        await message.answer("Укажите дату, например: <code>/close 25.12</code>\n\n" + ADMIN_HELP)
        return
    day = d.isoformat()
    if cmd.startswith("/close"):
        db.close_day(day)
        text = f"🔒 {fmt_date(day)} закрыт для записи."
        existing = db.bookings_on(day)
        if existing:
            text += "\n\n⚠️ На этот день уже есть записи — свяжитесь с клиентами:\n" + "\n".join(
                f"{r['time']} — {r['name']}, {r['phone']}" for r in existing)
        await message.answer(text)
    else:
        ok = db.open_day(day)
        await message.answer(f"🔓 {fmt_date(day)} снова открыт." if ok
                             else f"{fmt_date(day)} и так не был закрыт.")


@dp.message(Command("closed"))
async def list_closed(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    days = db.closed_days(date.today().isoformat())
    await message.answer("🔒 Закрытые дни:\n" + "\n".join(fmt_date(d) for d in days)
                         if days else "Закрытых дней нет.")


# ---------- Напоминания ----------

async def reminder_loop(bot: Bot):
    """Раз в минуту ищет записи, до которых осталось меньше REMIND_HOURS_BEFORE часов."""
    while True:
        try:
            now = datetime.now()
            until = now + timedelta(hours=config.REMIND_HOURS_BEFORE)
            for r in db.due_reminders(now.strftime("%Y-%m-%d %H:%M"), until.strftime("%Y-%m-%d %H:%M")):
                try:
                    await bot.send_message(
                        r["user_id"],
                        f"🔔 Напоминаем о записи!\n💇 {r['service']}\n"
                        f"📅 {fmt_date(r['date'])}, {r['time']}\n\nЕсли не сможете прийти — отмените запись:",
                        reply_markup=kb.cancel_booking(r["id"]),
                    )
                except Exception as e:  # клиент мог заблокировать бота
                    logging.warning("Не удалось отправить напоминание #%s: %s", r["id"], e)
                db.mark_reminded(r["id"])
        except Exception:
            logging.exception("Ошибка в цикле напоминаний")
        await asyncio.sleep(60)


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("Не найден BOT_TOKEN. Создайте файл .env (см. .env.example).")
    logging.basicConfig(level=logging.INFO)
    db.init_db()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    asyncio.create_task(reminder_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
