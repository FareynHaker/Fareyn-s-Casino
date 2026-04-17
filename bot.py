import asyncio
import random
import time
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite

TOKEN = "ВСТАВЬ_ТОКЕН_ОТ_BOTFATHER"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB = "casino.db"

bets = {}
game_start_time = None

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🎮 Игры", callback_data="games"),
         InlineKeyboardButton(text="🎰 Рулетка", callback_data="roulette")],
        [InlineKeyboardButton(text="📜 Лог", callback_data="log"),
         InlineKeyboardButton(text="💸 Перевод", callback_data="transfer")]
    ])

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            subscribed INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER,
            color TEXT
        )""")
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance, subscribed FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row:
            await db.execute("INSERT INTO users VALUES (?,0,0)", (user_id,))
            await db.commit()
            return 0, 0
        return row

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def set_sub(user_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET subscribed=1 WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET balance=balance+5000", (user_id,))
        await db.commit()

async def save_log(n, c):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO logs(number,color) VALUES(?,?)", (n,c))
        await db.commit()

async def get_logs():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT number,color FROM logs ORDER BY id DESC LIMIT 10")
        return await cur.fetchall()

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("🎰 Fareyn’s Casino", reply_markup=menu())

@dp.callback_query()
async def cb(call: types.CallbackQuery):
    uid = call.from_user.id
    balance, _ = await get_user(uid)

    if call.data == "profile":
        await call.message.answer(f"👤 ID: {uid}\n💰 Баланс: {balance} FRN", reply_markup=menu())

    if call.data == "balance":
        await call.message.answer(f"💰 Баланс: {balance} FRN", reply_markup=menu())

    if call.data == "log":
        logs = await get_logs()
        text = "📜 Последние числа:\n"
        for n,c in logs:
            text += f"{n} ({c})\n"
        await call.message.answer(text, reply_markup=menu())

@dp.message()
async def handler(msg: types.Message):
    global bets, game_start_time

    text = msg.text.lower()
    uid = msg.from_user.id

    balance, _ = await get_user(uid)

    if text == "b":
        await msg.answer(str(balance))
        return

    if re.match(r"^\d", text):
        if not game_start_time:
            game_start_time = time.time()

        parts = text.split()
        amount = int(parts[0])
        bet = " ".join(parts[1:])

        bets.setdefault(uid, []).append((amount, bet))
        await msg.answer(f"Ставка {amount} FRN на {bet}")
        return

    if text == "го":
        if not bets:
            await msg.answer("Нет ставок")
            return

        if time.time() - game_start_time < 15:
            await msg.answer("Подожди 15 секунд")
            return

        number = random.randint(0,36)
        color = "green" if number==0 else ("black" if number%2==0 else "red")

        await save_log(number,color)

        result = f"🎰 Выпало: {number} ({color})\n"

        for uid,user_bets in bets.items():
            win=0
            for amount,bet in user_bets:
                if bet==str(number): win+=amount*10
                if bet==color: win+=amount*2
                if bet=="к" and number==0: win+=amount*14

            if win:
                await update_balance(uid,win)

            result+=f"{uid}: +{win} FRN\n"

        bets={}
        game_start_time=None

        await msg.answer(result)

async def main():
    await init_db()
    await dp.start_polling(bot)

asyncio.run(main())
