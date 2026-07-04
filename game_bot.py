import telebot
import random
import time
import asyncio
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from database import *

bot = telebot.TeleBot(GAME_BOT_TOKEN)

# ===== РЕГИСТРАЦИЯ / СТАРТ =====
@bot.message_handler(commands=['exchange'])
def exchange_command(message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        bot.reply_to(message, "Сначала /start")
        return
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🪙 Золото → 💎 Кристаллы', callback_data='ex_gold_crystal'),
        InlineKeyboardButton('💎 Кристаллы → 🪙 Золото', callback_data='ex_crystal_gold'),
        InlineKeyboardButton('🪙 Золото → 🌑 Тени', callback_data='ex_gold_shadow'),
        InlineKeyboardButton('🌑 Тени → 🪙 Золото', callback_data='ex_shadow_gold'),
        InlineKeyboardButton('🪙 Золото → 🔥 Пламя', callback_data='ex_gold_flame'),
        InlineKeyboardButton('🔥 Пламя → 🪙 Золото', callback_data='ex_flame_gold')
    )
    bot.send_message(
        message.chat.id,
        "💱 *Обменник валют*\nВыбери направление обмена:",
        reply_markup=kb,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('ex_'))
def exchange_callback(call):
    user_id = call.from_user.id
    _, from_cur, to_cur = call.data.split('_')
    
    # Курсы обмена (1 к 1 для простоты)
    rates = {
        ('gold', 'crystal'): 1,
        ('crystal', 'gold'): 1,
        ('gold', 'shadow'): 2,
        ('shadow', 'gold'): 0.5,
        ('gold', 'flame'): 3,
        ('flame', 'gold'): 0.33,
    }
    
    rate = rates.get((from_cur, to_cur), 1)
    msg = bot.send_message(
        call.message.chat.id,
        f"Курс: 1 {from_cur} = {rate} {to_cur}\n"
        f"Сколько {from_cur} хочешь обменять?"
    )
    bot.register_next_step_handler(msg, process_exchange, user_id, from_cur, to_cur, rate)

def process_exchange(message, user_id, from_cur, to_cur, rate):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            bot.reply_to(message, "❌ Введи положительное число.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if not player:
        bot.reply_to(message, "❌ Ты не зарегистрирован.")
        return
    
    # Проверка наличия валюты
    balance = player[from_cur]
    if balance < amount:
        bot.reply_to(message, f"❌ Недостаточно {from_cur}. У тебя {balance}.")
        return
    
    # Обмен
    new_amount = int(amount * rate)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE players SET {from_cur} = {from_cur} - ?, {to_cur} = {to_cur} + ? WHERE user_id = ?", (amount, new_amount, user_id))
    conn.commit()
    conn.close()
    
    bot.reply_to(
        message,
        f"✅ Обмен завершён!\n"
        f"-{amount} {from_cur}\n"
        f"+{new_amount} {to_cur}\n"
        f"Новый баланс: {get_player(user_id)[to_cur]} {to_cur}",
        parse_mode='Markdown'
    )

# ===== /PLAY =====
@bot.message_handler(commands=['play'])
def play_command(message):
    show_games(message.chat.id)

def show_games(chat_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🔫 Русская рулетка', callback_data='game_roulette'),
        InlineKeyboardButton('🔴 Красное / Чёрное', callback_data='game_red_black'),
        InlineKeyboardButton('🎲 Кости', callback_data='game_dice')
    )
    bot.send_message(
        chat_id,
        "🎯 *Выбери игру:*",
        reply_markup=kb,
        parse_mode='Markdown'
    )

# ===== ОБРАБОТЧИК КНОПОК (основной) =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    if not player:
        bot.answer_callback_query(call.id, "Сначала зарегистрируйся через /start")
        return
    
    data = call.data
    
    # Главное меню
    if data == 'play':
        show_games(call.message.chat.id)
    elif data == 'stats':
        show_stats(call.message.chat.id, user_id)
    elif data == 'top':
        show_top_menu(call.message.chat.id)
    elif data == 'quests':
        show_quests(call.message.chat.id, user_id)
    
    # Игры
    elif data == 'game_roulette':
        ask_roulette_bet(call.message.chat.id, user_id)
    elif data == 'game_red_black':
        ask_red_black_bet(call.message.chat.id, user_id)
    elif data == 'game_dice':
        ask_dice_bet(call.message.chat.id, user_id)
    
    # Топ
    elif data == 'top_money':
        show_top_by(call.message.chat.id, 'money')
    elif data == 'top_level':
        show_top_by(call.message.chat.id, 'level')
    
    # Закрыть меню
    elif data == 'close':
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ===== СТАТИСТИКА =====
@bot.message_handler(commands=['stats'])
def stats_command(message):
    show_stats(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['stats_player'])
def stats_player_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Используй: /stats_player @username")
        return
    target_username = args[1].replace('@', '')
    # Ищем игрока по username (приблизительно)
    bot.reply_to(message, "🔍 Функция поиска игроков будет добавлена позже.")
    # Пока просто показываем свою статистику
    show_stats(message.chat.id, message.from_user.id)

def show_stats(chat_id, user_id):
    player = get_player(user_id)
    if not player:
        bot.send_message(chat_id, "❌ Ты не зарегистрирован. Напиши /start")
        return
    
    text = (
        f"📊 *Твоя статистика*\n\n"
        f"👤 Имя: {player['display_name']}\n"
        f"🏅 Уровень: {player['level']}\n"
        f"⭐ Опыт: {player['exp']}\n\n"
        f"{MAIN_CURRENCY}: {player['money']}\n"
        f"{CURRENCIES['crystal']}: {player['crystals']}\n"
        f"{CURRENCIES['shadow']}: {player['shadows']}\n"
        f"{CURRENCIES['flame']}: {player['flames']}\n\n"
        f"✅ Победы: {player['wins']}\n"
        f"❌ Поражения: {player['loses']}\n"
        f"🎮 Всего игр: {player['games_played']}"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='close'))
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode='Markdown')

# ===== ТОП =====
def show_top_menu(chat_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('💰 По деньгам', callback_data='top_money'),
        InlineKeyboardButton('🏅 По уровню', callback_data='top_level')
    )
    bot.send_message(
        chat_id,
        "🏆 *Выбери категорию топа:*",
        reply_markup=kb,
        parse_mode='Markdown'
    )

def show_top_by(chat_id, by):
    players = get_top_players(by)
    if not players:
        bot.send_message(chat_id, "❌ Нет игроков.")
        return
    
    text = f"🏆 *Топ-50 по {'деньгам' if by == 'money' else 'уровню'}*\n\n"
    for i, p in enumerate(players, 1):
        if by == 'money':
            text += f"{i}. {p['display_name']} — {p['money']} {MAIN_CURRENCY}\n"
        else:
            text += f"{i}. {p['display_name']} — Уровень {p['level']} (опыт: {p['exp']})\n"
        if i >= 50:
            break
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='close'))
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode='Markdown')

# ===== ИГРА: РУССКАЯ РУЛЕТКА =====
def ask_roulette_bet(chat_id, user_id):
    msg = bot.send_message(
        chat_id,
        f"🔫 *Русская рулетка*\n"
        f"Введите ставку (от {ROULETTE_MIN_BET} до {ROULETTE_MAX_BET} {MAIN_CURRENCY}):"
    )
    bot.register_next_step_handler(msg, process_roulette, user_id)

def process_roulette(message, user_id):
    try:
        bet = int(message.text.strip())
        if bet < ROULETTE_MIN_BET or bet > ROULETTE_MAX_BET:
            bot.reply_to(message, f"❌ Ставка от {ROULETTE_MIN_BET} до {ROULETTE_MAX_BET}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    # Логика рулетки
    chamber = random.randint(1, 6)
    bullet = random.randint(1, 6)
    
    if chamber == bullet:
        # Проигрыш
        admin_remove_money(user_id, bet)
        update_player_stats(user_id, loses=1, games=1)
        bot.reply_to(
            message,
            f"💥 *БАХ!* Ты проиграл {bet} {MAIN_CURRENCY}.\n"
            f"Баланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
            parse_mode='Markdown'
        )
    else:
        # Выигрыш (x5)
        win = bet * 5
        admin_add_money(user_id, win)
        update_player_stats(user_id, wins=1, games=1)
        bot.reply_to(
            message,
            f"🍀 *Клик!* Ты выжил! Выигрыш: {win} {MAIN_CURRENCY}.\n"
            f"Баланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
            parse_mode='Markdown'
        )

# ===== ИГРА: КРАСНОЕ / ЧЁРНОЕ =====
# Храним активные игры
red_black_games = {}

def ask_red_black_bet(chat_id, user_id):
    msg = bot.send_message(
        chat_id,
        f"🔴 *Красное / Чёрное*\n"
        f"Введите ставку (от {RED_BLACK_MIN_BET} до {RED_BLACK_MAX_BET} {MAIN_CURRENCY}):"
    )
    bot.register_next_step_handler(msg, process_red_black_bet, user_id)

def process_red_black_bet(message, user_id):
    try:
        bet = int(message.text.strip())
        if bet < RED_BLACK_MIN_BET or bet > RED_BLACK_MAX_BET:
            bot.reply_to(message, f"❌ Ставка от {RED_BLACK_MIN_BET} до {RED_BLACK_MAX_BET}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    # Выбор цвета
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🔴 Красное', callback_data=f'rb_red_{bet}_{user_id}'),
        InlineKeyboardButton('⚫ Чёрное', callback_data=f'rb_black_{bet}_{user_id}')
    )
    bot.send_message(
        message.chat.id,
        f"Выбери цвет (ставка {bet} {MAIN_CURRENCY}):",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('rb_'))
def red_black_result(call):
    _, color, bet, user_id = call.data.split('_')
    bet = int(bet)
    user_id = int(user_id)
    
    # Проверка, что вызывающий тот же игрок
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "❌ Это не твоя ставка.")
        return
    
    # Результат
    result = random.choice(['red', 'black'])
    win = bet * 2 if color == result else 0
    
    if win > 0:
        admin_add_money(user_id, win)
        update_player_stats(user_id, wins=1, games=1)
        text = f"🔴 Выпало *Красное*! Ты выиграл {win} {MAIN_CURRENCY}!"
    else:
        admin_remove_money(user_id, bet)
        update_player_stats(user_id, loses=1, games=1)
        text = f"⚫ Выпало *Чёрное*! Ты проиграл {bet} {MAIN_CURRENCY}."
    
    bot.edit_message_text(
        text + f"\nБаланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='Markdown'
    )

# ===== ИГРА: КОСТИ =====
def ask_dice_bet(chat_id, user_id):
    msg = bot.send_message(
        chat_id,
        f"🎲 *Кости*\n"
        f"Введите ставку (от {DICE_MIN_BET} до {DICE_MAX_BET} {MAIN_CURRENCY}):"
    )
    bot.register_next_step_handler(msg, process_dice, user_id)

def process_dice(message, user_id):
    try:
        bet = int(message.text.strip())
        if bet < DICE_MIN_BET or bet > DICE_MAX_BET:
            bot.reply_to(message, f"❌ Ставка от {DICE_MIN_BET} до {DICE_MAX_BET}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    # Бросок
    user_dice = random.randint(1, 6) + random.randint(1, 6)
    bot_dice = random.randint(1, 6) + random.randint(1, 6)
    
    if user_dice > bot_dice:
        win = bet * 2
        admin_add_money(user_id, win)
        update_player_stats(user_id, wins=1, games=1)
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n✅ Победа! +{win} {MAIN_CURRENCY}"
    elif user_dice < bot_dice:
        admin_remove_money(user_id, bet)
        update_player_stats(user_id, loses=1, games=1)
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n❌ Поражение! -{bet} {MAIN_CURRENCY}"
    else:
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n🤝 Ничья!"
    
    bot.reply_to(
        message,
        text + f"\nБаланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
        parse_mode='Markdown'
    )

# ===== КВЕСТЫ =====
def show_quests(chat_id, user_id):
    quests = get_player_quests(user_id)
    if not quests:
        bot.send_message(chat_id, "📜 Пока нет активных квестов.")
        return
    
    text = "📜 *Твои квесты:*\n\n"
    for q in quests:
        status = "✅ Выполнен" if q['completed'] else f"📊 {q['progress']}/{q['requirement_value']}"
        text += f"*{q['name']}*\n{q['description']}\n{status}\n\n"
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='close'))
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode='Markdown')

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print("🎰 Игровой бот запущен!")
    bot.polling(non_stop=True)
