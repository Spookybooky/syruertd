import os
import asyncio
import logging
import json
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

# ============ КОНФИГ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "8878696401:AAGWYU0a0xAbK1-BjDof9Y86_O4kDH5g-5s")

REQUIRED_CHANNELS = [
    {"id": "@spookyscripts", "link": "https://t.me/spookyscripts", "name": "Spooky Scripts"},
    {"id": -1003788328996, "link": "https://t.me/+GMHDq5Fij2M5MmFh", "name": "Spooky mod"},
    {"id": -1004356916182, "link": "https://t.me/+GIrw6Qj8tkZiMzhh", "name": "OUTLOW SCRIPTS"},
    # Рекламная редирект-ссылка — проверка подписки невозможна
    {"id": None, "link": "https://telegram.me/linknibot/app?startapp=x_432rp", "name": "подписка на канал 4", "no_check": True}
]

ADMIN_IDS = [6621617827, 7326365411]

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

COMMANDS_FILE = "hidden_commands.json"
USERS_FILE = "users_stats.json"
SETTINGS_FILE = "settings.json"
TICKETS_FILE = "tickets.json"

bot_stats = {
    "start_time": time.time(),
    "messages_processed": 0,
    "commands_used": 0,
    "errors": 0
}

users_page = {}
commands_page = {}
subscribed_cache = {}

POST_BUTTON_PRESETS = ["🔗Получить скрипт", "🔗 Получить чит"]


# ============ ЗАГРУЗКА/СОХРАНЕНИЕ ============
def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default


def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


hidden_commands = load_json(COMMANDS_FILE, {})
users_stats = load_json(USERS_FILE, {})
bot_settings = load_json(SETTINGS_FILE, {"notify_clicks": True, "menu1_photo": None, "menu2_photo": None, "menu3_photo": None})
tickets = load_json(TICKETS_FILE, {})


# --- Состояния FSM ---
class AddCommandStates(StatesGroup):
    waiting_for_command_name = State()
    waiting_for_media = State()
    waiting_for_file = State()
    waiting_for_title = State()


class MailingStates(StatesGroup):
    waiting_for_mailing_text = State()
    waiting_for_mailing_media = State()
    waiting_for_mailing_confirm = State()


class SupportStates(StatesGroup):
    waiting_for_support = State()


class ReplyStates(StatesGroup):
    waiting_for_reply = State()


class PostStates(StatesGroup):
    waiting_for_post = State()
    waiting_for_button_text = State()


class MenuPhotoStates(StatesGroup):
    waiting_for_menu1 = State()
    waiting_for_menu2 = State()
    waiting_for_menu3 = State()


# ==================== СТАТИСТИКА ====================
def update_user_stats(user_id: int, username: str = None, first_name: str = None):
    now = time.time()
    today = datetime.now().strftime('%Y-%m-%d')
    user_id_str = str(user_id)
    if user_id_str not in users_stats:
        users_stats[user_id_str] = {
            "first_seen": now, "last_seen": now, "first_name": first_name or "",
            "username": username or "", "total_visits": 0, "daily_visits": {}, "total_commands": 0,
            "new_sub_shown": False
        }
    user = users_stats[user_id_str]
    user["last_seen"] = now
    user["total_visits"] += 1
    if first_name:
        user["first_name"] = first_name
    if username:
        user["username"] = username
    if today not in user["daily_visits"]:
        user["daily_visits"][today] = 0
    user["daily_visits"][today] += 1
    if "new_sub_shown" not in user:
        user["new_sub_shown"] = False
    save_json(USERS_FILE, users_stats)


def get_user_stats(user_id: int) -> dict:
    user_id_str = str(user_id)
    if user_id_str not in users_stats:
        return None
    user = users_stats[user_id_str]
    now = time.time()
    first_seen = datetime.fromtimestamp(user["first_seen"])
    last_seen = datetime.fromtimestamp(user["last_seen"])
    total_seconds = now - user["first_seen"]
    days, hours, minutes = int(total_seconds // 86400), int((total_seconds % 86400) // 3600), int((total_seconds % 3600) // 60)
    today = datetime.now().strftime('%Y-%m-%d')
    today_visits = user["daily_visits"].get(today, 0)

    week_visits, month_visits, year_visits = 0, 0, 0
    now_date = datetime.now()
    for date, count in user["daily_visits"].items():
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            days_diff = (now_date - date_obj).days
            if days_diff <= 7:
                week_visits += count
            if days_diff <= 30:
                month_visits += count
            if days_diff <= 365:
                year_visits += count
        except:
            pass

    return {
        "user_id": user_id, "first_name": user.get("first_name", "Неизвестно"), "username": user.get("username"),
        "first_seen": first_seen.strftime('%d.%m.%Y %H:%M'), "last_seen": last_seen.strftime('%d.%m.%Y %H:%M'),
        "first_seen_timestamp": user["first_seen"], "total_seconds": total_seconds,
        "days": days, "hours": hours, "minutes": minutes, "total_visits": user["total_visits"],
        "today_visits": today_visits, "week_visits": week_visits, "month_visits": month_visits,
        "year_visits": year_visits, "total_commands": user.get("total_commands", 0), "daily_visits": user["daily_visits"]
    }


def get_all_users_stats() -> list:
    result = []
    for user_id_str in users_stats.keys():
        try:
            stats = get_user_stats(int(user_id_str))
            if stats:
                result.append(stats)
        except:
            continue
    result.sort(key=lambda x: x['first_seen_timestamp'], reverse=True)
    return result


# ==================== ПРОВЕРКА ПОДПИСКИ ====================
async def is_user_subscribed(user_id: int, force_check: bool = False) -> bool:
    now = time.time()
    if not force_check and user_id in subscribed_cache:
        if now - subscribed_cache[user_id] < 900:
            return True

    for channel in REQUIRED_CHANNELS:
        if channel.get("no_check") or channel.get("id") is None:
            continue
        try:
            member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status in ['left', 'kicked']:
                subscribed_cache.pop(user_id, None)
                return False
        except:
            return False

    subscribed_cache[user_id] = now
    return True


def get_subscription_keyboard(include_new_sub: bool = False):
    """include_new_sub=True — добавляет рекламную кнопку (канал 4)"""
    keyboard = []
    for channel in REQUIRED_CHANNELS:
        if channel.get("no_check"):
            if not include_new_sub:
                continue
            icon = "🚀"
        else:
            icon = "📢"
        keyboard.append([InlineKeyboardButton(text=f"{icon} {channel['name']}", url=channel["link"])])
    keyboard.append([InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ==================== СКОРОСТЬ ====================
async def check_bot_speed() -> dict:
    uptime_seconds = time.time() - bot_stats["start_time"]
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    uptime_seconds_formatted = uptime_seconds % 60

    ping_times = []
    for _ in range(3):
        try:
            start_ping = time.time()
            await bot.get_me()
            ping_times.append(round((time.time() - start_ping) * 1000))
        except:
            ping_times.append(None)

    valid_pings = [p for p in ping_times if p is not None]
    return {
        "uptime": f"{int(uptime_hours)}ч {int(uptime_minutes)}м {int(uptime_seconds_formatted)}с",
        "avg_ping": round(sum(valid_pings) / len(valid_pings)) if valid_pings else "❌ Ошибка",
        "min_ping": min(valid_pings) if valid_pings else "❌", "max_ping": max(valid_pings) if valid_pings else "❌",
        "messages": bot_stats["messages_processed"], "commands": bot_stats["commands_used"],
        "errors": bot_stats["errors"], "hidden_commands": len(hidden_commands),
        "last_check": datetime.now().strftime('%H:%M:%S')
    }


# ==================== ОТПРАВКА КОМАНД ====================
async def send_command_response(message: types.Message, command_data: dict):
    text = command_data.get('text', '')
    media_type = command_data.get('media_type')
    media_file_id = command_data.get('media_file_id')
    file_id = command_data.get('file_id')

    try:
        if media_type == 'photo' and media_file_id:
            await message.answer_photo(photo=media_file_id, caption=text)
        elif media_type == 'video' and media_file_id:
            await message.answer_video(video=media_file_id, caption=text)
        else:
            await message.answer(text)
    except:
        await message.answer(text)

    if file_id:
        try:
            await message.answer_document(document=file_id)
        except:
            pass


# ==================== КАРТИНКИ МЕНЮ ====================
@dp.message(Command("menu1"))
async def set_menu1_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📸 Отправь мне картинку для главного меню. Жду фото...\n\n❌ Отмена: /cancel")
    await state.set_state(MenuPhotoStates.waiting_for_menu1)


@dp.message(StateFilter(MenuPhotoStates.waiting_for_menu1), F.photo)
async def save_menu1_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    bot_settings["menu1_photo"] = message.photo[-1].file_id
    save_json(SETTINGS_FILE, bot_settings)
    await message.answer("✅ Картинка для главного меню сохранена!")
    await state.clear()


@dp.message(Command("menu2"))
async def set_menu2_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📸 Отправь мне картинку для поддержки. Жду фото...\n\n❌ Отмена: /cancel")
    await state.set_state(MenuPhotoStates.waiting_for_menu2)


@dp.message(StateFilter(MenuPhotoStates.waiting_for_menu2), F.photo)
async def save_menu2_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    bot_settings["menu2_photo"] = message.photo[-1].file_id
    save_json(SETTINGS_FILE, bot_settings)
    await message.answer("✅ Картинка для поддержки сохранена!")
    await state.clear()


@dp.message(Command("menu3"))
async def set_menu3_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📸 Отправь мне картинку для профиля. Жду фото...\n\n❌ Отмена: /cancel")
    await state.set_state(MenuPhotoStates.waiting_for_menu3)


@dp.message(StateFilter(MenuPhotoStates.waiting_for_menu3), F.photo)
async def save_menu3_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    bot_settings["menu3_photo"] = message.photo[-1].file_id
    save_json(SETTINGS_FILE, bot_settings)
    await message.answer("✅ Картинка для профиля сохранена!")
    await state.clear()


# ==================== START ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bot_stats["messages_processed"] += 1
    update_user_stats(user_id, message.from_user.username, message.from_user.first_name)

    args = message.text.split()
    if len(args) >= 2:
        command_name = args[1]

        if command_name == "back":
            await state.clear()
        elif command_name.startswith("postcmd_"):
            real_cmd = command_name.replace("postcmd_", "")
            if is_admin(user_id) and real_cmd in hidden_commands:
                await state.update_data(post_command=real_cmd, post_text=None, post_media_type=None, post_media_file_id=None, button_text=None)
                await state.set_state(PostStates.waiting_for_post)
                await message.answer(f"📝 Создание поста: {real_cmd}\n\nШаг 1/2: Отправь <b>текст поста</b> (можно с медиа).\n\n❌ Отмена: /cancel", parse_mode="HTML")
            return
        elif command_name in hidden_commands:
            if not await is_user_subscribed(user_id, force_check=True):
                await message.answer("⚠️ Для активации скрипта подпишитесь на каналы:", reply_markup=get_subscription_keyboard(include_new_sub=False))
                return

            bot_stats["commands_used"] += 1
            if str(user_id) in users_stats:
                users_stats[str(user_id)]["total_commands"] += 1
                save_json(USERS_FILE, users_stats)

            if bot_settings.get("notify_clicks"):
                username = f"@{message.from_user.username}" if message.from_user.username else "нет"
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, f"🔗 **Переход!**\n📁 `{command_name}`\n👤 {message.from_user.first_name} ({username})", parse_mode="Markdown")
                    except:
                        pass

            await send_command_response(message, hidden_commands[command_name])
            return

    # === Показ новой рекламной подписки ВСЕМ, но только 1 раз ===
    user_data = users_stats.get(str(user_id), {})
    if not user_data.get("new_sub_shown", False):
        await message.answer(
            "🚀 <b>Новая подписка!</b>\n\nПодпишитесь на наш новый канал:",
            reply_markup=get_subscription_keyboard(include_new_sub=True),
            parse_mode="HTML"
        )
        users_stats[str(user_id)]["new_sub_shown"] = True
        save_json(USERS_FILE, users_stats)
        return

    if not await is_user_subscribed(user_id):
        await message.answer("⚠️ Подпишитесь на каналы:", reply_markup=get_subscription_keyboard(include_new_sub=False))
        return

    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="user_support")]
    ])
    if is_admin(user_id):
        user_kb.inline_keyboard.insert(0, [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])

    channels_text = "".join([f"• <a href='{ch['link']}'>{ch['name']}</a>\n" for ch in REQUIRED_CHANNELS if not ch.get("no_check")])
    welcome_text = f"🎮 <b>С возвращением!</b>\n\n📢 Активация скриптов через:\n{channels_text}\n⚡ Бот работает 24/7\n\n💡 Предложения в <b>Поддержку</b>!"

    try:
        photo_id = bot_settings.get("menu1_photo")
        if photo_id:
            await message.answer_photo(photo=photo_id, caption=welcome_text, reply_markup=user_kb, parse_mode="HTML")
        else:
            await message.answer(welcome_text, reply_markup=user_kb, parse_mode="HTML")
    except:
        await message.answer(welcome_text, reply_markup=user_kb, parse_mode="HTML")


# ==================== АДМИН ПАНЕЛЬ ====================
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    total_users = len(users_stats)
    total_commands_all = sum(u.get('total_commands', 0) for u in users_stats.values())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📊 Статистика всех пользователей", callback_data="all_users_stats")],
        [InlineKeyboardButton(text="⚡ Проверить скорость", callback_data="check_speed")],
        [InlineKeyboardButton(text="➕ Добавить команду", callback_data="add_command")],
        [InlineKeyboardButton(text="📋 Список команд", callback_data="list_commands")],
        [InlineKeyboardButton(text="❌ Удалить команду", callback_data="delete_command")],
        [InlineKeyboardButton(text="📨 Сделать рассылку", callback_data="start_mailing")],
        [InlineKeyboardButton(text="🔄 Обновить данные юзеров", callback_data="update_users_data")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])
    await message.answer(f"⚙️ АДМИН-ПАНЕЛЬ\n\n👥 Всего пользователей: {total_users}\n🎯 Всего команд активировано: {total_commands_all}\n📁 Скрытых команд: {len(hidden_commands)}", reply_markup=kb)


@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Доступ запрещен!", show_alert=True)
    total_users = len(users_stats)
    total_commands_all = sum(u.get('total_commands', 0) for u in users_stats.values())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📊 Статистика всех пользователей", callback_data="all_users_stats")],
        [InlineKeyboardButton(text="⚡ Проверить скорость", callback_data="check_speed")],
        [InlineKeyboardButton(text="➕ Добавить команду", callback_data="add_command")],
        [InlineKeyboardButton(text="📋 Список команд", callback_data="list_commands")],
        [InlineKeyboardButton(text="❌ Удалить команду", callback_data="delete_command")],
        [InlineKeyboardButton(text="📨 Сделать рассылку", callback_data="start_mailing")],
        [InlineKeyboardButton(text="🔄 Обновить данные юзеров", callback_data="update_users_data")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])
    text = f"⚙️ АДМИН-ПАНЕЛЬ\n\n👥 Всего: {total_users}\n🎯 Команд: {total_commands_all}\n📁 Скрытых: {len(hidden_commands)}"
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


# ==================== ПРОФИЛЬ ====================
@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    if not await is_user_subscribed(callback.from_user.id, force_check=True):
        await callback.message.answer("⚠️ Вы отписались от каналов! Подпишитесь снова:", reply_markup=get_subscription_keyboard(include_new_sub=False))
        return await callback.answer()

    user_id = callback.from_user.id
    stats = get_user_stats(user_id)
    if not stats:
        return await callback.answer("❌ Профиль не найден!", show_alert=True)

    username_display = f"@{stats.get('username')}" if stats.get('username') else "❌ нету"
    time_str = f"{stats['days']}д {stats['hours']}ч {stats['minutes']}м"

    text = (
        f"👤 <b>Твой Профиль</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n📛 Имя: {stats['first_name']}\n🔗 Username: {username_display}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n📊 <b>Статистика:</b>\n👁 Визитов: {stats['total_visits']}\n"
        f"📅 Впервые: {stats['first_seen']}\n🕐 Последний раз: {stats['last_seen']}\n⏱ В боте: {time_str}\n"
        f"🎯 Скриптов: {stats['total_commands']}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="my_profile")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])

    photo_id = bot_settings.get("menu3_photo")
    if photo_id:
        await callback.message.answer_photo(photo=photo_id, caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ==================== ПРОВЕРКА ПОДПИСКИ ====================
@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
    if await is_user_subscribed(callback.from_user.id, force_check=True):
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        if str(callback.from_user.id) in users_stats:
            users_stats[str(callback.from_user.id)]["new_sub_shown"] = True
            save_json(USERS_FILE, users_stats)
        await cmd_start(callback.message, state)
    else:
        await callback.message.answer("❌ Вы ещё не подписались на все каналы!", reply_markup=get_subscription_keyboard(include_new_sub=False))


@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message, state)
    await callback.answer()


# ==================== СТАТИСТИКА ====================
@dp.callback_query(F.data == "all_users_stats")
async def all_users_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users_page[callback.from_user.id] = 0
    await show_users_page(callback.message, callback.from_user.id, 0)
    await callback.answer()


@dp.callback_query(F.data.startswith("users_page_"))
async def users_page_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        page = int(callback.data.split("_")[2])
        users_page[callback.from_user.id] = page
        await show_users_page(callback.message, callback.from_user.id, page)
    except:
        pass
    await callback.answer()


async def show_users_page(message: types.Message, user_id: int, page: int):
    all_stats = get_all_users_stats()
    if not all_stats:
        return await message.answer("📭 Нет пользователей")
    per_page = 5
    total_pages = (len(all_stats) + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    start_idx = page * per_page
    page_stats = all_stats[start_idx:start_idx + per_page]

    text = f"📊 СТАТИСТИКА\n👥 Всего: {len(all_stats)} | 📄 Стр. {page + 1}/{total_pages}\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, stats in enumerate(page_stats, start_idx + 1):
        time_str = f"{stats['days']}д {stats['hours']}ч {stats['minutes']}м"
        text += f"{i}. {stats['first_name']}\n   🆔 {stats['user_id']}\n   👁 {stats['total_visits']} | ⏱ {time_str}\n\n"

    kb = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"users_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"users_page_{page + 1}"))
    if nav_row:
        kb.append(nav_row)
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"users_page_{page}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    stats = get_user_stats(callback.from_user.id)
    if not stats:
        return await callback.answer("❌ Статистика не найдена!", show_alert=True)
    time_str = f"{stats['days']}д {stats['hours']}ч {stats['minutes']}м"
    text = f"👤 МОЯ СТАТИСТИКА\n\n📛 {stats['first_name']}\n🆔 {stats['user_id']}\n⏱ В боте: {time_str}\n👁 Визитов: {stats['total_visits']}"
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]]))
    await callback.answer()


@dp.callback_query(F.data == "check_speed")
async def check_speed(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    stats = await check_bot_speed()
    text = f"⚡ СКОРОСТЬ\n\n📡 Пинг: {stats['avg_ping']} мс\n⏱ Аптайм: {stats['uptime']}\n📨 Сообщений: {stats['messages']}\n🎯 Команд: {stats['commands']}"
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="check_speed")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]))
    await callback.answer()


@dp.callback_query(F.data == "update_users_data")
async def update_users_data(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("⏳ Обновляю...")
    updated = 0
    failed = 0
    for user_id_str in list(users_stats.keys()):
        try:
            chat = await bot.get_chat(int(user_id_str))
            new_name, new_username = chat.first_name or "", chat.username or ""
            if new_name != users_stats[user_id_str].get("first_name", "") or new_username != users_stats[user_id_str].get("username", ""):
                users_stats[user_id_str]["first_name"] = new_name
                users_stats[user_id_str]["username"] = new_username
                updated += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    save_json(USERS_FILE, users_stats)
    await callback.message.answer(f"✅ Обновлено: {updated}\n❌ Ошибок: {failed}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]]))
    await callback.answer()


@dp.callback_query(F.data == "admin_settings")
async def admin_settings(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    status = "✅ ВКЛ" if bot_settings.get("notify_clicks") else "❌ ВЫКЛ"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Уведомления: {status}", callback_data="toggle_clicks")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])
    await callback.message.answer("⚙️ НАСТРОЙКИ", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "toggle_clicks")
async def toggle_clicks(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    bot_settings["notify_clicks"] = not bot_settings.get("notify_clicks", True)
    save_json(SETTINGS_FILE, bot_settings)
    await admin_settings(callback)
    await callback.answer("Изменено!")


# ==================== ДОБАВЛЕНИЕ КОМАНД ====================
@dp.callback_query(F.data == "add_command")
async def add_command_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📝 Шаг 1/4: Введите название команды (латиницей, без пробелов):")
    await state.set_state(AddCommandStates.waiting_for_command_name)
    await callback.answer()


@dp.message(StateFilter(AddCommandStates.waiting_for_command_name))
async def add_command_get_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    command_name = message.text.strip().replace(" ", "_")
    if command_name in hidden_commands:
        return await message.answer("❌ Имя занято! Введите другое:")
    await state.update_data(command_name=command_name)
    await state.set_state(AddCommandStates.waiting_for_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_add_media")]
    ])
    await message.answer(
        "📷 Шаг 2/4: Отправьте медиа (фото или видео) для команды.\n"
        "Если медиа нет — нажмите «⏭️ Пропустить».\n\n❌ Отмена: /cancel",
        reply_markup=kb
    )


@dp.message(StateFilter(AddCommandStates.waiting_for_media), F.photo)
async def add_command_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(media_type="photo", media_file_id=message.photo[-1].file_id)
    await state.set_state(AddCommandStates.waiting_for_file)
    await message.answer("📎 Шаг 3/4: Теперь перешлите/отправьте <b>файл</b>, который бот запомнит и будет выдавать по команде.", parse_mode="HTML")


@dp.message(StateFilter(AddCommandStates.waiting_for_media), F.video)
async def add_command_video(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(media_type="video", media_file_id=message.video.file_id)
    await state.set_state(AddCommandStates.waiting_for_file)
    await message.answer("📎 Шаг 3/4: Теперь перешлите/отправьте <b>файл</b>, который бот запомнит и будет выдавать по команде.", parse_mode="HTML")


@dp.callback_query(F.data == "skip_add_media", StateFilter(AddCommandStates.waiting_for_media))
async def skip_add_media(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.update_data(media_type=None, media_file_id=None)
    await state.set_state(AddCommandStates.waiting_for_file)
    await callback.message.edit_text(
        "📎 Шаг 3/4: Теперь перешлите/отправьте <b>файл</b>, который бот запомнит и будет выдавать по команде.",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StateFilter(AddCommandStates.waiting_for_media))
async def add_command_media_invalid(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚠️ На этом шаге нужно отправить <b>фото или видео</b>, либо нажать «⏭️ Пропустить».", parse_mode="HTML")


@dp.message(StateFilter(AddCommandStates.waiting_for_file), F.document)
async def add_command_file(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(AddCommandStates.waiting_for_title)
    await message.answer("✍️ Шаг 4/4: Напишите <b>название</b> — текст, который будет в сообщении при выдаче команды.", parse_mode="HTML")


@dp.message(StateFilter(AddCommandStates.waiting_for_file))
async def add_command_file_invalid(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚠️ На этом шаге нужно отправить <b>файл</b> (документ).", parse_mode="HTML")


@dp.message(StateFilter(AddCommandStates.waiting_for_title), F.text)
async def add_command_title(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    hidden_commands[data['command_name']] = {
        "text": message.text,
        "media_type": data.get('media_type'),
        "media_file_id": data.get('media_file_id'),
        "file_id": data.get('file_id')
    }
    save_json(COMMANDS_FILE, hidden_commands)
    await show_command_created(message, data['command_name'], message.text, hidden_commands[data['command_name']])
    await state.clear()


@dp.message(StateFilter(AddCommandStates.waiting_for_title))
async def add_command_title_invalid(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚠️ На этом шаге нужно отправить <b>текст</b> (название).", parse_mode="HTML")


async def show_command_created(message: types.Message, command_name: str, text: str, command_data: dict):
    bot_link = f"https://t.me/{(await bot.get_me()).username}?start={command_name}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Ссылка-кнопка", url=bot_link)],
        [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_panel")]
    ])
    has_file = "✅ есть" if command_data.get("file_id") else "❌ нет"
    has_media = "✅ есть" if command_data.get("media_type") else "❌ нет"
    result_text = (
        f"✅ Команда создана!\n\n"
        f"📌 Имя: {command_name}\n"
        f"📝 Название: {text[:100]}\n"
        f"🖼 Медиа: {has_media}\n"
        f"📎 Файл: {has_file}\n"
        f"🔗 Ссылка:\n{bot_link}"
    )
    media_type = command_data.get('media_type')
    media_file_id = command_data.get('media_file_id')
    if media_type == 'photo' and media_file_id:
        await message.answer_photo(photo=media_file_id, caption=result_text, reply_markup=keyboard)
    elif media_type == 'video' and media_file_id:
        await message.answer_video(video=media_file_id, caption=result_text, reply_markup=keyboard)
    else:
        await message.answer(result_text, reply_markup=keyboard)


@dp.callback_query(F.data == "list_commands")
async def list_commands(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    commands_page[callback.from_user.id] = 0
    await show_commands_page(callback.message, callback.from_user.id, 0)
    await callback.answer()


@dp.callback_query(F.data.startswith("cmdpage_"))
async def commands_page_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        page = int(callback.data.split("_")[1])
        commands_page[callback.from_user.id] = page
        await show_commands_page(callback.message, callback.from_user.id, page)
    except:
        pass
    await callback.answer()


async def show_commands_page(message: types.Message, user_id: int, page: int):
    if not hidden_commands:
        return await message.answer("📭 Список пуст!")
    bot_username = (await bot.get_me()).username
    items = list(hidden_commands.items())
    per_page = 10
    total_pages = (len(items) + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    page_items = items[page * per_page:(page + 1) * per_page]

    text = f"📋 КОМАНДЫ\n📄 Стр. {page + 1}/{total_pages}\n━━━━━━━━━━━━━━━━━━\n\n"
    for idx, (name, data) in enumerate(page_items, page * per_page + 1):
        display_name = data.get('text', '').strip() or name
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        link = f"https://t.me/{bot_username}?start={name}"
        post_link = f"https://t.me/{bot_username}?start=postcmd_{name}"
        text += f"{idx}. {display_name}\n🔗 <a href='{link}'>Ссылка</a> | 📝 <a href='{post_link}'>Пост</a>\n\n"

    kb = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cmdpage_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"cmdpage_{page + 1}"))
    if nav_row:
        kb.append(nav_row)
    kb.append([InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_panel")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), disable_web_page_preview=True, parse_mode="HTML")


@dp.callback_query(F.data == "delete_command")
async def delete_command_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id) or not hidden_commands:
        return
    kb = []
    for name in hidden_commands.keys():
        kb.append([InlineKeyboardButton(text=f"❌ {name}", callback_data=f"del_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await callback.message.answer("🗑 Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("del_"))
async def delete_command_confirm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    name = callback.data.replace("del_", "")
    if name in hidden_commands:
        del hidden_commands[name]
        save_json(COMMANDS_FILE, hidden_commands)
        await callback.answer(f"✅ {name} удалена!", show_alert=True)
        await admin_panel(callback)


# ==================== ПОСТЫ ====================
@dp.message(StateFilter(PostStates.waiting_for_post), F.photo)
async def post_get_photo(message: types.Message, state: FSMContext):
    await state.update_data(post_text=message.caption or "", post_media_type="photo", post_media_file_id=message.photo[-1].file_id)
    await ask_button_text(message, state)


@dp.message(StateFilter(PostStates.waiting_for_post), F.video)
async def post_get_video(message: types.Message, state: FSMContext):
    await state.update_data(post_text=message.caption or "", post_media_type="video", post_media_file_id=message.video.file_id)
    await ask_button_text(message, state)


@dp.message(StateFilter(PostStates.waiting_for_post), F.text)
async def post_get_text(message: types.Message, state: FSMContext):
    await state.update_data(post_text=message.text, post_media_type=None, post_media_file_id=None)
    await ask_button_text(message, state)


async def ask_button_text(message: types.Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_button_text)
    # Инлайн-кнопки с копированием текста
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=preset, copy_text=CopyTextButton(text=preset))] for preset in POST_BUTTON_PRESETS
    ])
    await message.answer(
        "Шаг 2/2: Отправь <b>текст кнопки</b> или нажми на вариант ниже, чтобы скопировать:\n\n"
        "❌ Отмена: /cancel",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.message(StateFilter(PostStates.waiting_for_button_text), F.text)
async def post_get_button_text(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text.strip())
    data = await state.get_data()

    command_name = data.get('post_command')
    post_text = data.get('post_text', '')
    media_type = data.get('post_media_type')
    media_file_id = data.get('post_media_file_id')
    link_text = data.get('button_text')

    link = f"https://t.me/{(await bot.get_me()).username}?start={command_name}"
    post_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=link_text, url=link)]])
    preview_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_menu_{command_name}")],
        [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_panel")]
    ])

    await message.answer("👀 Превью:")
    if media_type == "photo":
        await message.answer_photo(photo=media_file_id, caption=post_text, reply_markup=post_keyboard, parse_mode="HTML")
    elif media_type == "video":
        await message.answer_video(video=media_file_id, caption=post_text, reply_markup=post_keyboard, parse_mode="HTML")
    else:
        await message.answer(post_text, reply_markup=post_keyboard, parse_mode="HTML", disable_web_page_preview=True)

    await message.answer("Выбери действие:", reply_markup=preview_kb)
    # ❗ state НЕ очищаем — данные нужны для publish_post


@dp.callback_query(F.data.startswith("publish_menu_"))
async def publish_menu(callback: types.CallbackQuery):
    command_name = callback.data.replace("publish_menu_", "", 1)
    kb = []
    for idx, ch in enumerate(REQUIRED_CHANNELS):
        if ch.get("no_check"):
            continue  # ❗ канал 4 не показываем в публикации
        kb.append([InlineKeyboardButton(text=f"📢 {ch['name']}", callback_data=f"publish_{idx}_{command_name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    await callback.message.answer(f"📢 Куда опубликовать <code>{command_name}</code>?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("publish_"))
async def publish_post(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    idx, command_name = int(parts[1]), parts[2]
    channel = REQUIRED_CHANNELS[idx]

    data = await state.get_data()
    post_text = data.get('post_text', '')
    media_type = data.get('post_media_type')
    media_file_id = data.get('post_media_file_id')
    button_text = data.get('button_text', '🔗 Скрипт')

    if not post_text:
        post_text = hidden_commands[command_name].get('text', '')
        media_type = hidden_commands[command_name].get('media_type')
        media_file_id = hidden_commands[command_name].get('media_file_id')

    link = f"https://t.me/{(await bot.get_me()).username}?start={command_name}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button_text, url=link)]])

    try:
        if media_type == "photo":
            await bot.send_photo(chat_id=channel["id"], photo=media_file_id, caption=post_text, reply_markup=kb)
        elif media_type == "video":
            await bot.send_video(chat_id=channel["id"], video=media_file_id, caption=post_text, reply_markup=kb)
        else:
            await bot.send_message(chat_id=channel["id"], text=post_text, reply_markup=kb)
        await callback.message.answer(f"✅ Опубликовано в «{channel['name']}»!")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}")
    await state.clear()
    await callback.answer()


# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "user_support")
async def user_support_start(callback: types.CallbackQuery, state: FSMContext):
    bot_username = (await bot.get_me()).username
    text = f"Привет, <b>{callback.from_user.first_name}</b>! Это поддержка. Напиши тикет или нажми <a href='https://t.me/{bot_username}?start=back'>Выход</a>."
    photo_id = bot_settings.get("menu2_photo")
    if photo_id:
        await callback.message.answer_photo(photo=photo_id, caption=text, parse_mode="HTML")
    else:
        await callback.message.answer(text, parse_mode="HTML")
    await state.set_state(SupportStates.waiting_for_support)
    await callback.answer()


@dp.message(StateFilter(SupportStates.waiting_for_support), F.text | F.photo | F.video)
async def user_support_get(message: types.Message, state: FSMContext):
    t_id = str(int(time.time()))
    text = message.text if message.text else (message.caption or "")
    media_type = 'photo' if message.photo else ('video' if message.video else None)
    media_file_id = message.photo[-1].file_id if message.photo else (message.video.file_id if message.video else None)

    tickets[t_id] = {"user_id": message.from_user.id, "name": message.from_user.first_name, "text": text, "media_type": media_type, "media_file_id": media_file_id, "status": "open"}
    save_json(TICKETS_FILE, tickets)

    for admin_id in ADMIN_IDS:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👁 Посмотреть", callback_data=f"view_ticket_{t_id}")]])
            await bot.send_message(admin_id, f"🆘 Тикет #{t_id} от {message.from_user.first_name}!", reply_markup=kb)
        except:
            pass
    await message.answer("✅ Отправлено! Ожидайте.")
    await state.clear()


@dp.callback_query(F.data.startswith("view_ticket_"))
async def view_ticket(callback: types.CallbackQuery):
    t_id = callback.data.replace("view_ticket_", "")
    t = tickets.get(t_id)
    if not t:
        return await callback.answer("❌ Не найден", show_alert=True)
    text = f"🆘 ТИКЕТ #{t_id}\n👤 {t['name']}\n📝 {t.get('text', '')}"
    kb = [
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_ticket_{t_id}")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"ignore_ticket_{t_id}")]
    ]

    if t.get('media_type') == 'photo':
        await callback.message.answer_photo(photo=t['media_file_id'], caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    elif t.get('media_type') == 'video':
        await callback.message.answer_video(video=t['media_file_id'], caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()


@dp.callback_query(F.data.startswith("ignore_ticket_"))
async def ignore_ticket(callback: types.CallbackQuery):
    t_id = callback.data.replace("ignore_ticket_", "")
    if t_id in tickets:
        tickets[t_id]['status'] = 'closed'
        save_json(TICKETS_FILE, tickets)
        await callback.message.answer(f"✅ Тикет #{t_id} закрыт.")
    await callback.answer()


@dp.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket_start(callback: types.CallbackQuery, state: FSMContext):
    t_id = callback.data.replace("reply_ticket_", "")
    await state.update_data(ticket_id=t_id)
    await callback.message.answer(f"✍️ Ответ для #{t_id} (или /cancel):")
    await state.set_state(ReplyStates.waiting_for_reply)
    await callback.answer()


@dp.message(StateFilter(ReplyStates.waiting_for_reply), F.text)
async def reply_ticket_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_id = data.get('ticket_id')
    if t_id in tickets:
        try:
            await bot.send_message(tickets[t_id]['user_id'], f"💬 Ответ по тикету #{t_id}:\n\n{message.text}")
            tickets[t_id]['status'] = 'closed'
            save_json(TICKETS_FILE, tickets)
            await message.answer("✅ Ответ отправлен!")
        except:
            await message.answer("❌ Ошибка отправки.")
    await state.clear()


# ==================== РАССЫЛКА ====================
@dp.callback_query(F.data == "start_mailing")
async def start_mailing(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("📨 Отправьте текст для рассылки (или /cancel):")
    await state.set_state(MailingStates.waiting_for_mailing_text)
    await callback.answer()


@dp.message(StateFilter(MailingStates.waiting_for_mailing_text))
async def get_mailing_text(message: types.Message, state: FSMContext):
    await state.update_data(mailing_text=message.text)
    await state.set_state(MailingStates.waiting_for_mailing_media)
    await message.answer("✅ Текст сохранен!\n📎 Медиа или Пропустить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_media")]]))


@dp.callback_query(F.data == "skip_media")
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    await show_confirm_mailing(callback.message, state)
    await callback.answer()


@dp.message(StateFilter(MailingStates.waiting_for_mailing_media), F.photo)
async def get_mailing_photo(message: types.Message, state: FSMContext):
    await state.update_data(media_type='photo', media_file_id=message.photo[-1].file_id)
    await show_confirm_mailing(message, state)


@dp.message(StateFilter(MailingStates.waiting_for_mailing_media), F.video)
async def get_mailing_video(message: types.Message, state: FSMContext):
    await state.update_data(media_type='video', media_file_id=message.video.file_id)
    await show_confirm_mailing(message, state)


async def show_confirm_mailing(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get('mailing_text', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_mailing")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
    ])
    await message.answer(f"📨 ПОДТВЕРЖДЕНИЕ\n👥 Получателей: {len(users_stats)}\n📝 Текст:\n{text[:200]}", reply_markup=kb)
    await state.set_state(MailingStates.waiting_for_mailing_confirm)


@dp.callback_query(F.data == "confirm_mailing")
async def confirm_mailing(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text, media_type, media_file_id = data.get('mailing_text', ''), data.get('media_type'), data.get('media_file_id')
    await callback.message.answer(f"⏳ Отправка...")
    success, failed = 0, 0
    for user_id_str in users_stats.keys():
        try:
            user_id = int(user_id_str)
            if media_type == 'photo':
                await bot.send_photo(chat_id=user_id, photo=media_file_id, caption=text)
            elif media_type == 'video':
                await bot.send_video(chat_id=user_id, video=media_file_id, caption=text)
            else:
                await bot.send_message(chat_id=user_id, text=text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await callback.message.answer(f"✅ Успешно: {success}\n❌ Ошибок: {failed}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]]))
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "cancel_mailing")
async def cancel_mailing(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Отменено", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]]))
    await callback.answer()


@dp.message(Command("cancel"))
async def cancel_all(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.")


# ==================== ЗАПУСК ====================
async def main():
    me = await bot.get_me()
    print(f"🤖 Бот запущен! @{me.username}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
