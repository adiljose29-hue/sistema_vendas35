import sqlite3
import hashlib
from datetime import datetime

def init_database():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL, -- Admin, Caixa, Gerente, Supervisor
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            barcode TEXT,
            name TEXT NOT NULL,
            description TEXT,
            purchase_price DECIMAL(10,2) NOT NULL,
            sale_price DECIMAL(10,2) NOT NULL,
            stock INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 5,
            iva_rate DECIMAL(5,2) DEFAULT 0.14, -- IVA Angola 14%
            category TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            nif TEXT UNIQUE,
            phone TEXT,
            email TEXT,
            address TEXT,
            customer_card TEXT UNIQUE, -- Cartão do cliente
            discount_rate DECIMAL(5,2) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Vendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            user_id INTEGER NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL,
            iva_amount DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            total DECIMAL(10,2) NOT NULL,
            payment_method TEXT NOT NULL, -- Dinheiro, Cartão, Transferência, Cartão_Cliente
            payment_status TEXT DEFAULT 'Pago',
            status TEXT DEFAULT 'Concluída',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tabela de Itens da Venda
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            iva_rate DECIMAL(5,2) NOT NULL,
            line_total DECIMAL(10,2) NOT NULL,
            is_voided BOOLEAN DEFAULT 0,
            voided_by INTEGER,
            void_reason TEXT,
            FOREIGN KEY (sale_id) REFERENCES sales (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (voided_by) REFERENCES users (id)
        )
    ''')
    
    # Tabela de Notas Fiscais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            sale_id INTEGER NOT NULL,
            customer_nif TEXT,
            customer_name TEXT NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            iva_amount DECIMAL(10,2) NOT NULL,
            issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            xml_data TEXT, -- XML da nota fiscal
            status TEXT DEFAULT 'Emitida',
            FOREIGN KEY (sale_id) REFERENCES sales (id)
        )
    ''')
    
    # Inserir usuário admin padrão
    admin_password = hashlib.md5('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, full_name, role)
        VALUES (?, ?, ?, ?)
    ''', ('admin', admin_password, 'Administrador', 'Admin'))
    
    # Inserir alguns produtos de exemplo
    cursor.execute('''
        INSERT OR IGNORE INTO products (code, name, purchase_price, sale_price, stock, iva_rate)
        VALUES 
        ('P001', 'Água Mineral 1L', 30.0, 50.0, 100, 0.14),
        ('P002', 'Pão Francês', 15.0, 25.0, 50, 0.14),
        ('P003', 'Arroz 5kg', 180.0, 255.0, 20, 0.14)
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_database()
    print("Base de dados inicializada com sucesso!")