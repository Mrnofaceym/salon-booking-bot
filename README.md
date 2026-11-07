# Salon Booking Telegram Bot

A Telegram bot that lets clients book appointments at a beauty salon, barbershop or any
service business — in a few taps, 24/7, without calls or messages to the owner.

<p align="center">
  <img src="docs/demo.gif" alt="Booking flow demo: service, date, time, name, phone, confirmation and owner notification" width="300">
</p>

## Features

**For clients**
- Step-by-step booking: service → date → free time slot → name → phone → confirm
- Only free and future time slots are shown; double booking is impossible
- "My bookings" with one-tap cancellation
- Automatic reminder 24 hours before the appointment

**For the owner**
- Instant notification about every new booking and cancellation
- `/admin` — list of upcoming appointments
- `/close 25.12` / `/open 25.12` — close days for holidays or vacation
- `/closed` — list of closed days

**Easy to adapt for a new client:** services, prices, working hours and days off
are all in one file — [`config.py`](config.py).

## Tech stack

- Python 3.12+
- [aiogram 3](https://docs.aiogram.dev/) (async Telegram Bot API framework, FSM for the booking flow)
- SQLite (no separate database server needed)
- systemd service for 24/7 operation on a Linux server

## Project structure

| File | Purpose |
|---|---|
| `bot.py` | Handlers: booking flow, cancellations, admin commands, reminder loop |
| `config.py` | Business settings: services, prices, schedule |
| `db.py` | SQLite storage and queries |
| `keyboards.py` | Telegram keyboards (menus, calendar, time slots) |
| `deploy/salon-bot.service` | systemd unit for running on a server |

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then put your BOT_TOKEN and ADMIN_ID into .env
python bot.py
```

Get a token from [@BotFather](https://t.me/BotFather). Send `/myid` to the running bot
to find your Telegram ID for `ADMIN_ID`.

## Deploy on a Linux server (systemd)

```bash
# copy the project to ~/salon-bot, create .venv and install requirements, then:
mkdir -p ~/.config/systemd/user
cp deploy/salon-bot.service ~/.config/systemd/user/
loginctl enable-linger $USER          # keep running after logout / start on boot
systemctl --user daemon-reload
systemctl --user enable --now salon-bot

journalctl --user -u salon-bot -f     # logs
```

Set your time zone in `deploy/salon-bot.service` (`Environment=TZ=...`).

---

🇷🇺 Telegram-бот для записи клиентов в салон: выбор услуги, даты и времени, уведомления
владельцу, напоминания клиентам, закрытие дней. Python + aiogram 3 + SQLite.
