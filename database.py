import sqlite3
import time

DB_NAME = 'swill_casino.db'

# ===== ПОДКЛЮЧЕНИЕ К БД =====
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ===== ШКАЛА ОПЫТА (1–1000) =====
def get_level_exp(level):
    """Возвращает количество опыта, необходимое для достижения указанного уровня"""
    if level <= 1:
        return 0
    if level <= 10:
        return (level - 1) * 100
    elif level <= 25:
        return 1000 + (level - 10) * 200
    elif level <= 50:
        return 4000 + (level - 25) * 500
    elif level <= 75:
        return 16500 + (level - 50) * 1000
    elif level <= 100:
        return 41500 + (level - 75) * 2000
    else:
        return 91500 + (level - 100) * 5000

def get_max_level():
    return 1000

# ===== ИНИЦИАЛИЗАЦИЯ БД =====
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Таблица игроков
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            money INTEGER DEFAULT 100,
            crystals INTEGER DEFAULT 0,
            shadows INTEGER DEFAULT 0,
            flames INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            loses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            register_date INTEGER DEFAULT 0,
            last_play INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица промокодов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward_type TEXT,
            reward_amount INTEGER,
            uses_left INTEGER,
            created_by INTEGER,
            created_at INTEGER
        )
    ''')
    
    # Таблица квестов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            requirement_type TEXT,
            requirement_value INTEGER,
            reward_exp INTEGER,
            reward_money INTEGER,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Таблица прогресса квестов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS player_quests (
            user_id INTEGER,
            quest_id INTEGER,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, quest_id)
        )
    ''')
    
    # Таблица истории игр
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT,
            players TEXT,
            winner INTEGER,
            bet INTEGER,
            timestamp INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    
    add_default_quests()

# ===== ДЕФОЛТНЫЕ КВЕСТЫ =====
def add_default_quests():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM quests")
    if cur.fetchone()[0] == 0:
        quests = [
            ('Новичок', 'Сыграй 3 игры', 'games_played', 3, 50, 20),
            ('Победитель', 'Выиграй 2 игры', 'wins', 2, 100, 50),
            ('Игроман', 'Сыграй 10 игр', 'games_played', 10, 200, 100),
            ('Профи', 'Выиграй 5 игр', 'wins', 5, 300, 150),
            ('Турнирный боец', 'Сыграй 20 игр', 'games_played', 20, 500, 300),
            ('Чемпион', 'Выиграй 10 игр', 'wins', 10, 800, 500),
        ]
        for q in quests:
            cur.execute('''
                INSERT INTO quests (name, description, requirement_type, requirement_value, reward_exp, reward_money)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', q)
        conn.commit()
    conn.close()

# ===== РАБОТА С ИГРОКАМИ =====
def get_player(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_player(user_id, username, display_name):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO players (user_id, username, display_name, register_date, last_play)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, display_name, int(time.time()), int(time.time())))
    conn.commit()
    conn.close()

def update_player_stats(user_id, wins=0, loses=0, games=0, money=0, crystals=0, shadows=0, flames=0):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE players SET
            wins = wins + ?,
            loses = loses + ?,
            games_played = games_played + ?,
            money = money + ?,
            crystals = crystals + ?,
            shadows = shadows + ?,
            flames = flames + ?,
            last_play = ?
        WHERE user_id = ?
    ''', (wins, loses, games, money, crystals, shadows, flames, int(time.time()), user_id))
    conn.commit()
    conn.close()

def get_all_players():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, display_name FROM players")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_top_players(by='money', limit=50):
    conn = get_db()
    cur = conn.cursor()
    if by == 'money':
        cur.execute("SELECT user_id, display_name, money FROM players ORDER BY money DESC LIMIT ?", (limit,))
    else:
        cur.execute("SELECT user_id, display_name, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ===== СИСТЕМА ОПЫТА И УРОВНЕЙ =====
def add_exp(user_id, exp):
    """
    Начисляет опыт игроку, автоматически повышает уровень
    Возвращает (новый_уровень, новый_опыт)
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT exp, level FROM players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    
    if not row:
        conn.close()
        return None, None
    
    new_exp = row['exp'] + exp
    new_level = row['level']
    
    # Автоматическое повышение уровня
    while new_level < get_max_level() and new_exp >= get_level_exp(new_level + 1):
        new_level += 1
        # Бонус за новый уровень (монеты)
        bonus = new_level * 10
        admin_add_money(user_id, bonus)
    
    cur.execute("UPDATE players SET exp = ?, level = ? WHERE user_id = ?", (new_exp, new_level, user_id))
    conn.commit()
    conn.close()
    
    return new_level, new_exp

def add_online_time(user_id, minutes):
    """Начисляет опыт за проведённое время в боте (0.5 опыта в минуту)"""
    from config import EXP_PER_MINUTE
    exp = int(minutes * EXP_PER_MINUTE)
    if exp > 0:
        return add_exp(user_id, exp)
    return None, None

def add_game_exp(user_id, is_win):
    """Начисляет опыт за игру (победа/поражение)"""
    from config import EXP_PER_WIN, EXP_PER_LOSE
    exp = EXP_PER_WIN if is_win else EXP_PER_LOSE
    return add_exp(user_id, exp)

# ===== АДМИН-ФУНКЦИИ =====
def admin_add_money(user_id, amount):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE players SET money = money + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def admin_remove_money(user_id, amount):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def admin_set_level(user_id, level):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE players SET level = ? WHERE user_id = ?", (level, user_id))
    conn.commit()
    conn.close()

def admin_reset_stats(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE players SET
            wins = 0, loses = 0, games_played = 0,
            money = 100, crystals = 0, shadows = 0, flames = 0,
            level = 1, exp = 0
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

# ===== ПРОМОКОДЫ =====
def create_promocode(code, reward_type, reward_amount, uses):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO promocodes (code, reward_type, reward_amount, uses_left, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (code, reward_type, reward_amount, uses, 0, int(time.time())))
    conn.commit()
    conn.close()

def delete_promocode(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def use_promocode(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT reward_type, reward_amount, uses_left FROM promocodes WHERE code = ?", (code,))
    row = cur.fetchone()
    if row and row['uses_left'] > 0:
        cur.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return row['reward_type'], row['reward_amount']
    conn.close()
    return None, None

def get_all_promocodes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM promocodes")
    rows = cur.fetchall()
    conn.close()
    return rows

# ===== ИСТОРИЯ ИГР =====
def add_game_history(game_type, players, winner, bet):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO game_history (game_type, players, winner, bet, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (game_type, ','.join(map(str, players)), winner, bet, int(time.time())))
    conn.commit()
    conn.close()

# ===== КВЕСТЫ =====
def get_player_quests(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT q.*, pq.progress, pq.completed
        FROM quests q
        LEFT JOIN player_quests pq ON q.id = pq.quest_id AND pq.user_id = ?
        WHERE q.is_active = 1
    ''', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_quest_progress(user_id, quest_id, progress):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO player_quests (user_id, quest_id, progress, completed)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, quest_id) DO UPDATE SET progress = progress + ?
    ''', (user_id, quest_id, progress))
    conn.commit()
    conn.close()

def check_quest_completion(user_id, quest_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT q.requirement_value, pq.progress, pq.completed
        FROM quests q
        JOIN player_quests pq ON q.id = pq.quest_id
        WHERE q.id = ? AND pq.user_id = ?
    ''', (quest_id, user_id))
    row = cur.fetchone()
    if row and not row['completed'] and row['progress'] >= row['requirement_value']:
        cur.execute("UPDATE player_quests SET completed = 1 WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ===== ИНИЦИАЛИЗАЦИЯ ПРИ ЗАПУСКЕ =====
init_db()
