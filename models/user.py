from database.db import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import re

class User:
    @staticmethod
    def create(username, email, password, role):
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if email or username already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return None, "An account with this email address already exists."

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return None, "Username is already taken. Please choose another."

        password_hash = generate_password_hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, role)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id, None
        except Exception as e:
            conn.close()
            return None, str(e)

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def get_by_email(email):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def authenticate(login_input, password):
        """Authenticate by either username or email address."""
        user = None
        if "@" in login_input:
            user = User.get_by_email(login_input)
        
        if not user:
            user = User.get_by_username(login_input)

        if not user:
            return None

        if check_password_hash(user["password_hash"], password):
            return user
        return None

    @staticmethod
    def get_all():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY username ASC")
        users = cursor.fetchall()
        conn.close()
        return users

    @staticmethod
    def get_developers():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE role = 'Developer' ORDER BY username ASC")
        devs = cursor.fetchall()
        conn.close()
        return devs
