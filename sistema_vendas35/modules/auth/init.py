import hashlib
import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash

class AuthModule:
    def __init__(self, db_path='sistema_vendas.db'):
        self.db_path = db_path
    
    def login(self, username, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        cursor.execute('''
            SELECT id, username, full_name, role FROM users 
            WHERE username = ? AND password = ? AND is_active = 1
        ''', (username, hashed_password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['full_name'] = user[2]
            session['role'] = user[3]
            return True
        return False
    
    def logout(self):
        session.clear()
    
    def get_current_user(self):
        return {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'full_name': session.get('full_name'),
            'role': session.get('role')
        }
    
    def require_role(self, allowed_roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login'))
                
                user_role = session.get('role')
                if user_role not in allowed_roles:
                    flash('Acesso não autorizado!', 'error')
                    return redirect(url_for('dashboard'))
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

# Decorators para diferentes níveis de acesso
def admin_required(f):
    return AuthModule().require_role(['Admin'])(f)

def manager_required(f):
    return AuthModule().require_role(['Admin', 'Gerente'])(f)

def supervisor_required(f):
    return AuthModule().require_role(['Admin', 'Gerente', 'Supervisor'])(f)