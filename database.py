import sqlite3
import time
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    
    conn.commit()
    conn.close()
    
    add_default_quests()

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

# ===== СИСТЕМА ОПЫТА =====
def add_exp(user_id, exp):
    from config import LEVEL_EXP
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT exp, level FROM players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        new_exp = row['exp'] + exp
        level = row['level']
        while level < 1000 and new_exp >= LEVEL_EXP.get(level + 1, 10**9):
            level += 1
            admin_add_money(user_id, level * 10)
        cur.execute("UPDATE players SET exp = ?, level = ? WHERE user_id = ?", (new_exp, level, user_id))
        conn.commit()
        conn.close()
        return level, new_exp
    conn.close()
    return None, None

def add_online_time(user_id, minutes):
    exp = int(minutes * 0.5)
    if exp > 0:
        return add_exp(user_id, exp)
    return None, None

def add_game_exp(user_id, is_win):
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

# ===== ИНИЦИАЛИЗАЦИЯ =====
init_db()
