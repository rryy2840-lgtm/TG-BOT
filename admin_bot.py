import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from database import *

bot = telebot.TeleBot(ADMIN_BOT_TOKEN)

# Проверка админа
def is_admin(user_id):
    # Простая проверка по юзернейму (можно заменить на ID)
    return True  # Для теста открыт всем, потом заменишь на проверку

@bot.message_handler(commands=['start'])
def start_admin(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ У тебя нет доступа к админ-панели.")
        return
    
    show_admin_panel(message.chat.id)

def show_admin_panel(chat_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('💰 Дать деньги', callback_data='add_money'),
        InlineKeyboardButton('💰 Отнять деньги', callback_data='remove_money'),
        InlineKeyboardButton('⬆️ Повысить уровень', callback_data='up_level'),
        InlineKeyboardButton('⬇️ Понизить уровень', callback_data='down_level'),
        InlineKeyboardButton('🎁 Создать промик', callback_data='create_promo'),
        InlineKeyboardButton('🗑 Удалить промик', callback_data='delete_promo'),
        InlineKeyboardButton('🧹 Очистить статистику', callback_data='reset_stats'),
        InlineKeyboardButton('📢 Рассылка (/zov)', callback_data='zov')
    )
    bot.send_message(
        chat_id,
        "🔧 *Админ-панель*\nВыбери действие:",
        reply_markup=kb,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет доступа.")
        return
    
    data = call.data
    
    if data == 'add_money':
        msg = bot.send_message(call.message.chat.id, "Введи ID пользователя и сумму через пробел (например: 123456 100)")
        bot.register_next_step_handler(msg, process_add_money)
    elif data == 'remove_money':
        msg = bot.send_message(call.message.chat.id, "Введи ID пользователя и сумму через пробел (например: 123456 50)")
        bot.register_next_step_handler(msg, process_remove_money)
    elif data == 'up_level':
        msg = bot.send_message(call.message.chat.id, "Введи ID пользователя для повышения уровня")
        bot.register_next_step_handler(msg, process_up_level)
    elif data == 'down_level':
        msg = bot.send_message(call.message.chat.id, "Введи ID пользователя для понижения уровня")
        bot.register_next_step_handler(msg, process_down_level)
    elif data == 'create_promo':
        msg = bot.send_message(call.message.chat.id, "Введи промик: код, тип (money/crystal/shadow/flame), количество, число использований\nПример: SWILL100 money 100 10")
        bot.register_next_step_handler(msg, process_create_promo)
    elif data == 'delete_promo':
        msg = bot.send_message(call.message.chat.id, "Введи код промика для удаления")
        bot.register_next_step_handler(msg, process_delete_promo)
    elif data == 'reset_stats':
        msg = bot.send_message(call.message.chat.id, "Введи ID пользователя для очистки статистики")
        bot.register_next_step_handler(msg, process_reset_stats)
    elif data == 'zov':
        msg = bot.send_message(call.message.chat.id, "Введи текст рассылки (всем игрокам):")
        bot.register_next_step_handler(msg, process_zov)

# ===== ОБРАБОТЧИКИ АДМИН-КОМАНД =====
def process_add_money(message):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        amount = int(parts[1])
        admin_add_money(user_id, amount)
        bot.reply_to(message, f"✅ Добавлено {amount} {MAIN_CURRENCY} пользователю {user_id}")
    except:
        bot.reply_to(message, "❌ Ошибка. Используй: ID СУММА")

def process_remove_money(message):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        amount = int(parts[1])
        admin_remove_money(user_id, amount)
        bot.reply_to(message, f"✅ Отнято {amount} {MAIN_CURRENCY} у пользователя {user_id}")
    except:
        bot.reply_to(message, "❌ Ошибка. Используй: ID СУММА")

def process_up_level(message):
    try:
        user_id = int(message.text.strip())
        player = get_player(user_id)
        if player:
            admin_set_level(user_id, player['level'] + 1)
            bot.reply_to(message, f"✅ Уровень повышен до {player['level'] + 1} у {user_id}")
        else:
            bot.reply_to(message, "❌ Пользователь не найден.")
    except:
        bot.reply_to(message, "❌ Введи ID пользователя.")

def process_down_level(message):
    try:
        user_id = int(message.text.strip())
        player = get_player(user_id)
        if player and player['level'] > 1:
            admin_set_level(user_id, player['level'] - 1)
            bot.reply_to(message, f"✅ Уровень понижен до {player['level'] - 1} у {user_id}")
        else:
            bot.reply_to(message, "❌ Пользователь не найден или уровень 1.")
    except:
        bot.reply_to(message, "❌ Введи ID пользователя.")

def process_create_promo(message):
    try:
        parts = message.text.split()
        code = parts[0]
        reward_type = parts[1]
        reward_amount = int(parts[2])
        uses = int(parts[3])
        create_promocode(code, reward_type, reward_amount, uses)
        bot.reply_to(message, f"✅ Промокод {code} создан!")
    except:
        bot.reply_to(message, "❌ Ошибка. Пример: SWILL100 money 100 10")

def process_delete_promo(message):
    try:
        code = message.text.strip()
        delete_promocode(code)
        bot.reply_to(message, f"✅ Промокод {code} удалён.")
    except:
        bot.reply_to(message, "❌ Ошибка.")

def process_reset_stats(message):
    try:
        user_id = int(message.text.strip())
        admin_reset_stats(user_id)
        bot.reply_to(message, f"✅ Статистика сброшена для {user_id}")
    except:
        bot.reply_to(message, "❌ Введи ID пользователя.")

def process_zov(message):
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "❌ Текст не может быть пустым.")
        return
    
    players = get_all_players()
    if not players:
        bot.reply_to(message, "❌ Нет игроков для рассылки.")
        return
    
    count = 0
    for p in players:
        try:
            bot.send_message(p['user_id'], f"📢 *ВАЖНОЕ ОБЪЯВЛЕНИЕ*\n\n{text}", parse_mode='Markdown')
            count += 1
        except:
            pass
    
    bot.reply_to(message, f"✅ Рассылка отправлена {count} игрокам.")

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print("🔧 Админ-бот запущен!")
    bot.polling(non_stop=True)
