import telebot
import random
import time
import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from database import *

bot = telebot.TeleBot(GAME_BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def hello():
    return "I am alive!"

# ===== ПАССИВНЫЙ ОПЫТ =====
last_active = {}

def update_activity(user_id):
    last_active[user_id] = time.time()

def check_online_exp():
    while True:
        time.sleep(60)
        for user_id, last_time in list(last_active.items()):
            minutes = int((time.time() - last_time) / 60)
            if minutes >= 10:
                new_level, new_exp = add_online_time(user_id, minutes)
                if new_level:
                    try:
                        bot.send_message(user_id, f"⏰ Ты получил +{int(minutes * 0.5)} опыта за время в боте!")
                    except:
                        pass
                last_active[user_id] = time.time()

threading.Thread(target=check_online_exp, daemon=True).start()

# ===== РЕГИСТРАЦИЯ =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    player = get_player(user_id)
    
    if not player:
        msg = bot.send_message(
            message.chat.id,
            f"👋 Добро пожаловать в *SWILL CASINO*!\n\n"
            f"Для начала игры введи своё *игровое имя* (никнейм, который будут видеть другие):",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, register_name)
    else:
        show_main_menu(message.chat.id, user_id)

def register_name(message):
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    display_name = message.text.strip()
    
    if len(display_name) < 2 or len(display_name) > 30:
        msg = bot.reply_to(message, "❌ Имя должно быть от 2 до 30 символов. Попробуй снова:")
        bot.register_next_step_handler(msg, register_name)
        return
    
    create_player(user_id, username, display_name)
    bot.send_message(
        message.chat.id,
        f"✅ Отлично, *{display_name}*! Теперь ты в игре.\n"
        f"Твой баланс: {MAIN_CURRENCY} 100\n\n"
        f"Используй /play, чтобы начать!",
        parse_mode='Markdown'
    )
    show_main_menu(message.chat.id, user_id)

def show_main_menu(chat_id, user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🎰 Играть', callback_data='play'),
        InlineKeyboardButton('📊 Статистика', callback_data='stats'),
        InlineKeyboardButton('🏆 Топ игроков', callback_data='top'),
        InlineKeyboardButton('📜 Квесты', callback_data='quests'),
        InlineKeyboardButton('💱 Обменник', callback_data='exchange')
    )
    bot.send_message(
        chat_id,
        "🏠 *Главное меню*\nВыбери действие:",
        reply_markup=kb,
        parse_mode='Markdown'
    )

# ===== КОМАНДЫ =====
@bot.message_handler(commands=['play'])
def play_command(message):
    show_games(message.chat.id)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        bot.reply_to(message, "❌ Сначала зарегистрируйся через /start")
        return
    
    text = (
        f"📊 *Твоя статистика*\n\n"
        f"ID: {player['user_id']}\n"
        f"Имя: {player['display_name']}\n"
        f"Уровень: {player['level']}\n"
        f"Опыт: {player['exp']}\n\n"
        f"🪙 Золото: {player['money']}\n"
        f"💎 Кристаллы: {player['crystals']}\n"
        f"🌑 Тени: {player['shadows']}\n"
        f"🔥 Пламя: {player['flames']}\n\n"
        f"Победы: {player['wins']}\n"
        f"Поражения: {player['loses']}\n"
        f"Игр: {player['games_played']}"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('🔙 Назад', callback_data='close'))
    bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(commands=['top'])
def top_command(message):
    args = message.text.split()
    by = args[1] if len(args) > 1 else 'money'
    
    if by not in ['money', 'crystals', 'shadows', 'flames']:
        bot.reply_to(message, "❌ Доступно: /top money, /top crystals, /top shadows, /top flames")
        return
    
    players = get_top_players(by)
    if not players:
        bot.reply_to(message, "❌ Нет игроков.")
        return
    
    text = f"🏆 *Топ-50 по {by}*\n\n"
    for i, p in enumerate(players, 1):
        text += f"{i}. {p['display_name']} — {p[by]} {by}\n"
        if i >= 50:
            break
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['exchange'])
def exchange_command(message):
    user_id = message.from_user.id
    player = get_player(user_id)
    if not player:
        bot.reply_to(message, "❌ Сначала зарегистрируйся через /start")
        return
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🪙→💎', callback_data='ex_gold_crystal'),
        InlineKeyboardButton('💎→🪙', callback_data='ex_crystal_gold'),
        InlineKeyboardButton('🪙→🌑', callback_data='ex_gold_shadow'),
        InlineKeyboardButton('🌑→🪙', callback_data='ex_shadow_gold'),
        InlineKeyboardButton('🪙→🔥', callback_data='ex_gold_flame'),
        InlineKeyboardButton('🔥→🪙', callback_data='ex_flame_gold')
    )
    bot.send_message(
        message.chat.id,
        "💱 *Обменник валют*\nВыбери направление:",
        reply_markup=kb,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['quests'])
def quests_command(message):
    user_id = message.from_user.id
    show_quests(message.chat.id, user_id)

# ===== ОБРАБОТЧИК КОЛБЭКОВ =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    if not player:
        bot.answer_callback_query(call.id, "❌ Сначала зарегистрируйся через /start")
        return
    
    data = call.data
    
    if data == 'play':
        show_games(call.message.chat.id)
    elif data == 'stats':
        stats_command(call.message)
    elif data == 'top':
        top_menu(call.message.chat.id)
    elif data == 'quests':
        show_quests(call.message.chat.id, user_id)
    elif data == 'exchange':
        exchange_command(call.message)
    elif data == 'close':
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif data.startswith('ex_'):
        _, from_cur, to_cur = data.split('_')
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
            f"💱 Курс: 1 {from_cur} = {rate} {to_cur}\n"
            f"Сколько {from_cur} хочешь обменять?"
        )
        bot.register_next_step_handler(msg, process_exchange, user_id, from_cur, to_cur, rate)
    
    elif data == 'game_roulette':
        ask_roulette_bet(call.message.chat.id, user_id)
    elif data == 'game_red_black':
        ask_red_black_bet(call.message.chat.id, user_id)
    elif data == 'game_dice':
        ask_dice_bet(call.message.chat.id, user_id)
    
    elif data.startswith('rb_'):
        _, color, bet, uid = data.split('_')
        bet = int(bet)
        uid = int(uid)
        if call.from_user.id != uid:
            bot.answer_callback_query(call.id, "❌ Это не твоя ставка.")
            return
        result = random.choice(['red', 'black'])
        win = bet * 2 if color == result else 0
        if win > 0:
            admin_add_money(uid, win)
            update_player_stats(uid, wins=1, games=1)
            add_game_exp(uid, True)
            text = f"🔴 Выпало *Красное*! Ты выиграл {win} {MAIN_CURRENCY}!"
        else:
            admin_remove_money(uid, bet)
            update_player_stats(uid, loses=1, games=1)
            add_game_exp(uid, False)
            text = f"⚫ Выпало *Чёрное*! Ты проиграл {bet} {MAIN_CURRENCY}."
        bot.edit_message_text(
            text + f"\nБаланс: {get_player(uid)['money']} {MAIN_CURRENCY}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown'
        )
    
    elif data == 'top_money':
        show_top_by(call.message.chat.id, 'money')
    elif data == 'top_level':
        show_top_by(call.message.chat.id, 'level')

# ===== ОБМЕННИК =====
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
    
    balance = player[from_cur]
    if balance < amount:
        bot.reply_to(message, f"❌ Недостаточно {from_cur}. У тебя {balance}.")
        return
    
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
        f"+{new_amount} {to_cur}\n\n"
        f"Новый баланс: {get_player(user_id)[to_cur]} {to_cur}",
        parse_mode='Markdown'
    )

# ===== ИГРЫ =====
def show_games(chat_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton('🔫 Русская рулетка', callback_data='game_roulette'),
        InlineKeyboardButton('🔴 Красное / Чёрное', callback_data='game_red_black'),
        InlineKeyboardButton('🎲 Кости', callback_data='game_dice')
    )
    bot.send_message(chat_id, "🎯 *Выбери игру:*", reply_markup=kb, parse_mode='Markdown')

def ask_roulette_bet(chat_id, user_id):
    player = get_player(user_id)
    min_bet, max_bet = get_bet_limits(player['level'])
    msg = bot.send_message(
        chat_id,
        f"🔫 *Русская рулетка*\n"
        f"Твой уровень: {player['level']}\n"
        f"Ставка от {min_bet} до {max_bet} {MAIN_CURRENCY}:\n"
        f"(введи число)",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_roulette, user_id, min_bet, max_bet)

def process_roulette(message, user_id, min_bet, max_bet):
    try:
        bet = int(message.text.strip())
        if bet < min_bet or bet > max_bet:
            bot.reply_to(message, f"❌ Ставка от {min_bet} до {max_bet}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    chamber = random.randint(1, 6)
    bullet = random.randint(1, 6)
    
    if chamber == bullet:
        admin_remove_money(user_id, bet)
        update_player_stats(user_id, loses=1, games=1)
        add_game_exp(user_id, False)
        bot.reply_to(
            message,
            f"💥 *БАХ!* Ты проиграл {bet} {MAIN_CURRENCY}.\n"
            f"Баланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
            parse_mode='Markdown'
        )
    else:
        win = bet * 5
        admin_add_money(user_id, win)
        update_player_stats(user_id, wins=1, games=1)
        add_game_exp(user_id, True)
        bot.reply_to(
            message,
            f"🍀 *Клик!* Ты выжил! Выигрыш: {win} {MAIN_CURRENCY}.\n"
            f"Баланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
            parse_mode='Markdown'
        )

def ask_red_black_bet(chat_id, user_id):
    player = get_player(user_id)
    min_bet, max_bet = get_bet_limits(player['level'])
    msg = bot.send_message(
        chat_id,
        f"🔴 *Красное / Чёрное*\n"
        f"Твой уровень: {player['level']}\n"
        f"Ставка от {min_bet} до {max_bet} {MAIN_CURRENCY}:\n"
        f"(введи число)",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_red_black_bet, user_id, min_bet, max_bet)

def process_red_black_bet(message, user_id, min_bet, max_bet):
    try:
        bet = int(message.text.strip())
        if bet < min_bet or bet > max_bet:
            bot.reply_to(message, f"❌ Ставка от {min_bet} до {max_bet}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🔴 Красное', callback_data=f'rb_red_{bet}_{user_id}'),
        InlineKeyboardButton('⚫ Чёрное', callback_data=f'rb_black_{bet}_{user_id}')
    )
    bot.send_message(
        message.chat.id,
        f"Выбери цвет (ставка {bet} {MAIN_CURRENCY}):",
        reply_markup=kb,
        parse_mode='Markdown'
    )

def ask_dice_bet(chat_id, user_id):
    player = get_player(user_id)
    min_bet, max_bet = get_bet_limits(player['level'])
    msg = bot.send_message(
        chat_id,
        f"🎲 *Кости*\n"
        f"Твой уровень: {player['level']}\n"
        f"Ставка от {min_bet} до {max_bet} {MAIN_CURRENCY}:\n"
        f"(введи число)",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_dice, user_id, min_bet, max_bet)

def process_dice(message, user_id, min_bet, max_bet):
    try:
        bet = int(message.text.strip())
        if bet < min_bet or bet > max_bet:
            bot.reply_to(message, f"❌ Ставка от {min_bet} до {max_bet}.")
            return
    except:
        bot.reply_to(message, "❌ Введи число.")
        return
    
    player = get_player(user_id)
    if player['money'] < bet:
        bot.reply_to(message, f"❌ Недостаточно {MAIN_CURRENCY}.")
        return
    
    user_dice = random.randint(1, 6) + random.randint(1, 6)
    bot_dice = random.randint(1, 6) + random.randint(1, 6)
    
    if user_dice > bot_dice:
        win = bet * 2
        admin_add_money(user_id, win)
        update_player_stats(user_id, wins=1, games=1)
        add_game_exp(user_id, True)
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n✅ Победа! +{win} {MAIN_CURRENCY}"
    elif user_dice < bot_dice:
        admin_remove_money(user_id, bet)
        update_player_stats(user_id, loses=1, games=1)
        add_game_exp(user_id, False)
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n❌ Поражение! -{bet} {MAIN_CURRENCY}"
    else:
        text = f"🎲 Ты: {user_dice} | Бот: {bot_dice}\n🤝 Ничья!"
    
    bot.reply_to(
        message,
        text + f"\nБаланс: {get_player(user_id)['money']} {MAIN_CURRENCY}",
        parse_mode='Markdown'
    )

# ===== ТОП =====
def top_menu(chat_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('💰 По деньгам', callback_data='top_money'),
        InlineKeyboardButton('🏅 По уровню', callback_data='top_level')
    )
    bot.send_message(chat_id, "🏆 *Выбери категорию топа:*", reply_markup=kb, parse_mode='Markdown')

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
    # Запускаем веб-сервер в отдельном потоке
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)).start()
    print("🎰 Игровой бот запущен!")
    bot.polling(non_stop=True)
