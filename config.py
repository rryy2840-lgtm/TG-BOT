# ===== КОНФИГ =====
GAME_BOT_TOKEN = '8902715438:AAGC5vjT4LT9BRvkwfNle1imvjZMYe9i_vE'
ADMIN_BOT_TOKEN = '7973103417:AAEW4Z-lnpdMCMgeku_Y7owwlXvRs6g4Fso'
ADMIN_ID = '@krak2222'

# ===== ВАЛЮТЫ =====
MAIN_CURRENCY = '🪙 Золото'
CURRENCIES = {
    'crystal': '💎 Кристаллы',
    'shadow': '🌑 Тени',
    'flame': '🔥 Пламя'
}

# ===== СТАВКИ ПО УРОВНЯМ =====
def get_bet_limits(level):
    if level <= 10:
        return 5, 50
    elif level <= 25:
        return 10, 200
    elif level <= 50:
        return 25, 500
    elif level <= 75:
        return 50, 1500
    elif level <= 100:
        return 100, 5000
    else:
        return 500, 50000

# ===== ШКАЛА ОПЫТА (1–1000) =====
LEVEL_EXP = {}
for i in range(1, 1001):
    if i <= 10:
        LEVEL_EXP[i] = i * 100
    elif i <= 25:
        LEVEL_EXP[i] = 1000 + (i-10) * 200
    elif i <= 50:
        LEVEL_EXP[i] = 4000 + (i-25) * 500
    elif i <= 75:
        LEVEL_EXP[i] = 16500 + (i-50) * 1000
    elif i <= 100:
        LEVEL_EXP[i] = 41500 + (i-75) * 2000
    else:
        LEVEL_EXP[i] = 91500 + (i-100) * 5000

# ===== НАЧИСЛЕНИЕ ОПЫТА =====
EXP_PER_MINUTE = 0.5   # +5 за 10 минут
EXP_PER_5_GAMES = 25   # +25 за 5 игр
EXP_PER_WIN = 10       # +10 за победу
EXP_PER_LOSE = 3       # +3 за поражение
