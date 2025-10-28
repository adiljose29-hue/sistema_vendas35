from flask import Flask, request, jsonify, session, redirect, render_template_string
import sqlite3
import hashlib
from datetime import datetime
import random
import os
# ========== BIBLIOTECAS PARA RELATÓRIOS ==========
import matplotlib
matplotlib.use('Agg')  # Para uso em servidor web
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'sistema_vendas_2024'

# ========== CONFIGURAÇÃO DO BANCO DE DADOS ==========
def init_db():
    if os.path.exists('sistema_vendas.db'):
        os.remove('sistema_vendas.db')
    
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            sale_price DECIMAL(10,2) NOT NULL,
            stock INTEGER DEFAULT 0,
            iva_rate DECIMAL(5,2) DEFAULT 0.14,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            nif TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            customer_card TEXT UNIQUE,
            discount_rate DECIMAL(5,2) DEFAULT 0,
            total_purchases DECIMAL(10,2) DEFAULT 0,
            last_purchase_date DATETIME,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
        payment_method TEXT NOT NULL,
        valor_pago DECIMAL(10,2) DEFAULT 0,  -- NOVO CAMPO
        troco DECIMAL(10,2) DEFAULT 0,       -- NOVO CAMPO
        status TEXT DEFAULT 'Concluída',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            iva_rate DECIMAL(5,2) NOT NULL,
            line_total DECIMAL(10,2) NOT NULL
        )
    ''')
    
    admin_password = hashlib.md5('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, full_name, role)
        VALUES (?, ?, ?, ?)
    ''', ('admin', admin_password, 'Administrador Sistema', 'Admin'))
    
    caixa_password = hashlib.md5('caixa123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, full_name, role)
        VALUES (?, ?, ?, ?)
    ''', ('caixa', caixa_password, 'Operador de Caixa', 'Caixa'))
    
    products_data = [
        ('P001', 'Água Mineral 1L', 50.0, 100, 0.14),
        ('P002', 'Pão Francês', 25.0, 50, 0.14),
        ('P003', 'Arroz 5kg', 255.0, 20, 0.14),
        ('P004', 'Azeite 1L', 850.0, 30, 0.14),
        ('P005', 'Café 500g', 450.0, 25, 0.14),
        ('P006', 'Leite 1L', 75.0, 80, 0.14),
        ('P007', 'Açúcar 1kg', 120.0, 40, 0.14),
        ('P008', 'Óleo 1L', 150.0, 35, 0.14)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO products (code, name, sale_price, stock, iva_rate)
        VALUES (?, ?, ?, ?, ?)
    ''', products_data)
    
    customers_data = [
        ('C001', 'Maria Silva', '123456789', '912345678', 'maria@email.com', 'Rua A, nº 1', 'CARD001', 5.0),
        ('C002', 'João Santos', '987654321', '923456789', 'joao@email.com', 'Rua B, nº 2', 'CARD002', 10.0),
        ('C003', 'Ana Costa', '456789123', '934567890', 'ana@email.com', 'Rua C, nº 3', 'CARD003', 0.0)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO customers (code, name, nif, phone, email, address, customer_card, discount_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', customers_data)
    
    conn.commit()
    conn.close()
    print("✅ Base de dados criada com sucesso!")

# ========== SISTEMA DE CONFIGURAÇÕES ==========
def init_settings_table():
    """Criar tabela para configurações do sistema"""
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Configurações padrão
    default_settings = [
        ('company_name', 'LOJA EXEMPLO'),
        ('company_address', 'Rua Principal, 123 - Luanda'),
        ('company_phone', '+244 123 456 789'),
        ('company_email', 'loja@exemplo.com'),
        ('company_nif', '123456789'),
        ('iva_default', '0.14'),
        ('currency', '€'),
        ('printer_type', 'file'),
        ('printer_address', '192.168.1.100'),
        ('backup_frequency', 'daily')
    ]
    
    for key, value in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value)
            VALUES (?, ?)
        ''', (key, value))
    
    conn.commit()
    conn.close()
    print("✅ Tabela de configurações criada com sucesso!")

def get_setting(key, default=None):
    """Obter uma configuração do banco de dados"""
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT setting_value FROM system_settings WHERE setting_key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else default

def save_setting(key, value):
    """Salvar uma configuração no banco de dados"""
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value)
        VALUES (?, ?)
    ''', (key, value))
    
    conn.commit()
    conn.close()

# ========== CONFIGURAÇÃO DA IMPRESSORA ==========
try:
    from escpos.printer import Network, File
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    print("⚠️  Biblioteca escpos não instalada. Use: pip install escpos")

class ThermalPrinter:
    def __init__(self):
        self.printer = None
        self.setup_printer()
    
    def setup_printer(self):
        """Configurar a impressora - suporta USB, rede e arquivo"""
        try:
            printer_type = get_setting('printer_type', 'file')
            printer_address = get_setting('printer_address', 'recibo.txt')
            
            if printer_type == 'usb':
                if os.name == 'nt':  # Windows
                    self.printer = File("LPT1:")
                else:  # Linux
                    self.printer = File("/dev/usb/lp0")
                print("✅ Impressora USB configurada")
            elif printer_type == 'network':
                self.printer = Network(printer_address)
                print(f"✅ Impressora de rede configurada: {printer_address}")
            else:  # file
                self.printer = File(printer_address)
                print(f"✅ Modo de teste - impressão em arquivo: {printer_address}")
                
        except Exception as e:
            print(f"❌ Erro ao configurar impressora: {str(e)}")
            # Fallback para arquivo
            self.printer = File("recibo.txt")
            print("⚠️  Usando modo fallback - impressão em arquivo recibo.txt")
    
    def print_receipt(self, sale_data, items, customer=None):
        """Imprimir recibo da venda"""
        print(f"🔍 DEBUG - Iniciando impressão:")
        print(f"🔍 sale_data: {sale_data}")
        print(f"🔍 items: {items}")
        print(f"🔍 customer: {customer}")
        
        try:
            # Obter configurações da empresa
            company_name = get_setting('company_name', 'LOJA EXEMPLO')
            company_address = get_setting('company_address', 'Rua Principal, 123 - Luanda')
            company_nif = get_setting('company_nif', '123456789')
            
            # Criar conteúdo do recibo
            receipt_lines = []
            receipt_lines.append("=" * 50)
            receipt_lines.append(f"           🛒 {company_name}")
            receipt_lines.append(f"        {company_address}")
            receipt_lines.append(f"           NIF: {company_nif}")
            receipt_lines.append("=" * 50)
            receipt_lines.append(f"Venda: {sale_data.get('sale_number', 'N/A')}")
            receipt_lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            receipt_lines.append(f"Operador: {session.get('full_name', 'Sistema')}")
            
            if customer:
                receipt_lines.append(f"Cliente: {customer.get('name', 'N/A')}")
                receipt_lines.append(f"Cartão: {customer.get('customer_card', 'N/A')}")
            
            receipt_lines.append("-" * 50)
            receipt_lines.append("Qtd  Descrição                Preço   Total")
            receipt_lines.append("-" * 50)
            
            # Processar itens
            for item in items:
                name = item.get('name', 'Produto')
                if len(name) > 20:
                    name = name[:17] + "..."
                
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                iva_rate = item.get('iva_rate', 0.14)
                
                item_total = quantity * unit_price
                iva_percent = f"{(iva_rate * 100):.0f}%"
                
                receipt_lines.append(f"{quantity:2d} x {name:<20} {unit_price:6.2f}€ {item_total:6.2f}€")
                receipt_lines.append(f"     IVA {iva_percent}")
            
            receipt_lines.append("=" * 50)
            
            # Totais
            subtotal = sale_data.get('subtotal', 0)
            discount = sale_data.get('discount_amount', 0)
            iva_total = sale_data.get('iva_amount', 0)
            total = sale_data.get('total', 0)
            valor_pago = sale_data.get('valor_pago', 0)
            troco = sale_data.get('troco', 0)
            payment_method = sale_data.get('payment_method', 'N/A')
            
            receipt_lines.append(f"Subtotal: {subtotal:8.2f} €")
            
            if discount > 0:
                receipt_lines.append(f"Desconto: -{discount:7.2f} €")
                subtotal_com_desconto = subtotal - discount
                receipt_lines.append(f"Subtotal c/ Desc: {subtotal_com_desconto:8.2f} €")
            
            receipt_lines.append(f"IVA Total: {iva_total:8.2f} €")
            receipt_lines.append("-" * 50)
            receipt_lines.append(f"TOTAL: {total:8.2f} €")
            
            # Mostrar valor pago e troco apenas para pagamento em dinheiro
            if payment_method == 'Dinheiro' and valor_pago > 0:
                receipt_lines.append(f"Valor pago: {valor_pago:8.2f} €")
                receipt_lines.append(f"Troco: {troco:8.2f} €")
                receipt_lines.append("-" * 50)
            
            receipt_lines.append(f"Pagamento: {payment_method}")
            receipt_lines.append("=" * 50)
            receipt_lines.append("     Obrigado pela sua compra!")
            receipt_lines.append("           Volte sempre!")
            receipt_lines.append("\n" * 2)
            
            # Salvar em arquivo
            filename = get_setting('printer_address', 'recibo.txt')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(receipt_lines))
            
            print(f"✅ Recibo salvo em: {filename}")
            print("📄 Conteúdo do recibo:")
            print('\n'.join(receipt_lines))
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar recibo: {str(e)}")
            return False

printer = ThermalPrinter()

# ========== SISTEMA DE RELATÓRIOS AVANÇADOS ==========
class AdvancedReports:
    def __init__(self, db_path='sistema_vendas.db'):
        self.db_path = db_path
    
    def get_sales_summary(self, start_date=None, end_date=None):
        """Resumo geral de vendas"""
        conn = sqlite3.connect(self.db_path)
        
        # Converter datas para formato SQLite
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '') + ' 23:59:59'
        
        query = '''
            SELECT 
                COUNT(*) as total_vendas,
                SUM(total) as total_faturado,
                AVG(total) as media_venda,
                SUM(iva_amount) as total_iva,
                SUM(discount_amount) as total_descontos
            FROM sales 
            WHERE status = 'Concluída'
        '''
        
        params = []
        if start_date and end_date:
            query += ' AND date(created_at) BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        elif start_date:
            query += ' AND date(created_at) >= ?'
            params.append(start_date)
        elif end_date:
            query += ' AND date(created_at) <= ?'
            params.append(end_date)
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_vendas': result[0] or 0,
            'total_faturado': float(result[1] or 0),
            'media_venda': float(result[2] or 0),
            'total_iva': float(result[3] or 0),
            'total_descontos': float(result[4] or 0)
        }
    
    def get_top_products(self, limit=10, start_date=None, end_date=None):
        """Produtos mais vendidos"""
        conn = sqlite3.connect(self.db_path)
        
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '') + ' 23:59:59'
        
        query = '''
            SELECT 
                p.name as produto,
                SUM(si.quantity) as quantidade_vendida,
                SUM(si.line_total) as total_faturado,
                COUNT(DISTINCT s.id) as vezes_vendido
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sale_id = s.id
            WHERE s.status = 'Concluída'
        '''
        
        params = []
        if start_date and end_date:
            query += ' AND date(s.created_at) BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        elif start_date:
            query += ' AND date(s.created_at) >= ?'
            params.append(start_date)
        elif end_date:
            query += ' AND date(s.created_at) <= ?'
            params.append(end_date)
        
        query += '''
            GROUP BY p.id, p.name
            ORDER BY quantidade_vendida DESC
            LIMIT ?
        '''
        params.append(limit)
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        products = []
        for row in results:
            products.append({
                'produto': row[0],
                'quantidade': row[1],
                'total': float(row[2]),
                'vezes_vendido': row[3]
            })
        
        return products
    
    def get_sales_by_period(self, period='daily', days=30):
        """Vendas por período (diário, semanal, mensal)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if period == 'daily':
            query = '''
                SELECT 
                    date(created_at) as data,
                    COUNT(*) as vendas,
                    SUM(total) as total
                FROM sales 
                WHERE status = 'Concluída' AND date(created_at) BETWEEN ? AND ?
                GROUP BY date(created_at)
                ORDER BY data
            '''
        elif period == 'weekly':
            query = '''
                SELECT 
                    strftime('%Y-%W', created_at) as semana,
                    COUNT(*) as vendas,
                    SUM(total) as total
                FROM sales 
                WHERE status = 'Concluída' AND date(created_at) BETWEEN ? AND ?
                GROUP BY strftime('%Y-%W', created_at)
                ORDER BY semana
            '''
        else:  # monthly
            query = '''
                SELECT 
                    strftime('%Y-%m', created_at) as mes,
                    COUNT(*) as vendas,
                    SUM(total) as total
                FROM sales 
                WHERE status = 'Concluída' AND date(created_at) BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY mes
            '''
        
        cursor.execute(query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        results = cursor.fetchall()
        conn.close()
        
        data = []
        for row in results:
            data.append({
                'periodo': row[0],
                'vendas': row[1],
                'total': float(row[2])
            })
        
        return data
    
    def get_payment_methods_summary(self, start_date=None, end_date=None):
        """Resumo por métodos de pagamento"""
        conn = sqlite3.connect(self.db_path)
        
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '') + ' 23:59:59'
        
        query = '''
            SELECT 
                payment_method,
                COUNT(*) as quantidade,
                SUM(total) as total
            FROM sales 
            WHERE status = 'Concluída'
        '''
        
        params = []
        if start_date and end_date:
            query += ' AND date(created_at) BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        elif start_date:
            query += ' AND date(created_at) >= ?'
            params.append(start_date)
        elif end_date:
            query += ' AND date(created_at) <= ?'
            params.append(end_date)
        
        query += ' GROUP BY payment_method ORDER BY total DESC'
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        methods = []
        for row in results:
            methods.append({
                'metodo': row[0],
                'quantidade': row[1],
                'total': float(row[2])
            })
        
        return methods
    
    def create_sales_chart(self, period='daily', days=30):
        """Criar gráfico de vendas"""
        sales_data = self.get_sales_by_period(period, days)
        
        if not sales_data:
            return None
        
        periods = [item['periodo'] for item in sales_data]
        totals = [item['total'] for item in sales_data]
        
        plt.figure(figsize=(12, 6))
        plt.bar(periods, totals, color='skyblue', alpha=0.7)
        plt.title(f'Vendas por Período - Últimos {days} dias', fontsize=14, fontweight='bold')
        plt.xlabel('Período')
        plt.ylabel('Total (€)')
        plt.xticks(rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        # Converter gráfico para base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def create_top_products_chart(self, limit=10):
        """Criar gráfico de produtos mais vendidos"""
        top_products = self.get_top_products(limit)
        
        if not top_products:
            return None
        
        products = [item['produto'][:15] + '...' if len(item['produto']) > 15 else item['produto'] 
                   for item in top_products]
        quantities = [item['quantidade'] for item in top_products]
        
        plt.figure(figsize=(12, 6))
        colors = plt.cm.Set3(range(len(products)))
        bars = plt.barh(products, quantities, color=colors)
        
        plt.title(f'Top {limit} Produtos Mais Vendidos', fontsize=14, fontweight='bold')
        plt.xlabel('Quantidade Vendida')
        plt.tight_layout()
        
        # Adicionar valores nas barras
        for bar, quantity in zip(bars, quantities):
            plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{quantity}', ha='left', va='center')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def create_payment_methods_chart(self):
        """Criar gráfico de métodos de pagamento"""
        payment_data = self.get_payment_methods_summary()
        
        if not payment_data:
            return None
        
        methods = [item['metodo'] for item in payment_data]
        totals = [item['total'] for item in payment_data]
        
        plt.figure(figsize=(10, 8))
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        plt.pie(totals, labels=methods, autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title('Distribuição por Método de Pagamento', fontsize=14, fontweight='bold')
        plt.axis('equal')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"

# Instância global dos relatórios
reports = AdvancedReports()

# ========== ROTAS PRINCIPAIS ==========
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    return redirect('/pos')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, full_name, role FROM users WHERE username = ? AND password = ? AND is_active = 1', (username, hashed_password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['full_name'] = user[2]
            session['role'] = user[3]
            return '''
            <script>
                alert('Login realizado com sucesso!');
                window.location.href = '/pos';
            </script>
            '''
        else:
            return '''
            <script>
                alert('Usuário ou senha incorretos!');
                window.location.href = '/login';
            </script>
            '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Sistema de Vendas</title>
        <style>
            body { font-family: Arial; background: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); width: 300px; }
            h2 { text-align: center; color: #333; margin-bottom: 20px; }
            input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .test-info { margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>🛒 Sistema de Vendas</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="Usuário" value="admin" required>
                <input type="password" name="password" placeholder="Senha" value="admin123" required>
                <button type="submit">Entrar</button>
            </form>
            <div class="test-info">
                <strong>Contas para teste:</strong><br>
                Admin: admin / admin123<br>
                Caixa: caixa / caixa123
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ========== ROTAS DO SISTEMA ==========
@app.route('/pos')
def pos():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ponto de Venda</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }
            .container { display: flex; padding: 20px; gap: 20px; height: calc(100vh - 80px); }
            .products-panel { flex: 2; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); overflow-y: auto; }
            .cart-panel { flex: 1; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
            .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }
            .product-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; cursor: pointer; transition: all 0.3s; }
            .product-card:hover { border-color: #007bff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .product-code { font-size: 12px; color: #666; }
            .product-name { font-weight: bold; margin: 5px 0; }
            .product-price { color: #28a745; font-weight: bold; }
            .product-stock { font-size: 12px; color: #999; }
            .cart-items { flex: 1; overflow-y: auto; margin: 15px 0; }
            .cart-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
            .cart-totals { border-top: 2px solid #eee; padding-top: 15px; }
            .total-line { display: flex; justify-content: space-between; margin: 5px 0; }
            .total-final { font-weight: bold; font-size: 18px; border-top: 1px solid #ccc; padding-top: 10px; }
            .payment-btn { width: 100%; padding: 12px; margin: 5px 0; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn-cash { background: #28a745; color: white; }
            .btn-card { background: #007bff; color: white; }
            .btn-transfer { background: #6f42c1; color: white; }
            .btn-clear { background: #dc3545; color: white; margin-top: 10px; }
            .nav-menu { background: #343a40; padding: 0; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .customer-section { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 15px; }
            .customer-info { background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .barcode-scanner { background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 15px; border: 1px solid #ffeaa7; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛒 Ponto de Venda</h1>
            <div>
                <span>Bem-vindo, ''' + session.get('full_name', 'Usuário') + '''</span>
                <a href="/logout" style="margin-left: 20px; color: #dc3545; text-decoration: none;">Sair</a>
            </div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos" class="active">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="products-panel">
                <h3>Produtos Disponíveis</h3>
                
                <div class="barcode-scanner">
                    <strong>📷 Leitor de Código de Barras:</strong>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        Posicione o cursor no campo abaixo e passe o código de barras
                    </div>
                    <input type="text" id="barcodeInput" placeholder="🟢 Pronto para leitura..." 
                           style="width: 100%; padding: 10px; margin-top: 5px; border: 2px solid #28a745; border-radius: 5px; font-size: 16px;"
                           onfocus="this.style.borderColor='#007bff'" 
                           onblur="this.style.borderColor='#28a745'">
                </div>
                
                <input type="text" id="searchProduct" placeholder="🔍 Pesquisar..." style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                <div class="products-grid" id="productsGrid">
                    <!-- Produtos carregados via JavaScript -->
                </div>
            </div>

            <div class="cart-panel">
                <h3>🛍️ Carrinho de Vendas</h3>
                
                <div class="customer-section">
                    <h4>👥 Cliente:</h4>
                    <select id="customerSelect" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
                        <option value="">-- Cliente Anónimo --</option>
                    </select>
                    <div id="customerInfo" class="customer-info" style="display: none;">
                        <!-- Informações do cliente -->
                    </div>
                    <button onclick="applyCustomerDiscount()" style="width: 100%; padding: 8px; margin-top: 5px; background: #17a2b8; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        💳 Aplicar Desconto do Cartão
                    </button>
                </div>
                
                <div class="cart-items" id="cartItems">
                    <div style="text-align: center; color: #999; padding: 20px;">Carrinho vazio</div>
                </div>

                <div class="cart-totals">
                    <div class="total-line">
                        <span>Subtotal:</span>
                        <span id="subtotal">0,00 €</span>
                    </div>
                    <div class="total-line">
                        <span>Desconto:</span>
                        <span id="discount">0,00 €</span>
                    </div>
                    <div class="total-line">
                        <span>IVA:</span>
                        <span id="iva">0,00 €</span>
                    </div>
                    <div class="total-line total-final">
                        <span>TOTAL:</span>
                        <span id="total">0,00 €</span>
                    </div>
                </div>

                <div style="margin: 15px 0;">
                    <h4>💳 Método de Pagamento:</h4>
                    <button class="payment-btn btn-cash" onclick="finalizeSale('Dinheiro')">💵 Dinheiro</button>
                    <button class="payment-btn btn-card" onclick="finalizeSale('Cartão')">💳 Cartão</button>
                    <button class="payment-btn btn-transfer" onclick="finalizeSale('Transferência')">🏦 Transferência</button>
                </div>

                <button class="payment-btn btn-clear" onclick="clearCart()">🗑️ Limpar Carrinho</button>
            </div>
        </div>

        <script>
            let cart = [];
            let products = [];
            let customers = [];
            let selectedCustomer = null;
            let discountApplied = false;

            // Carregar produtos
            async function loadProducts() {
                try {
                    const response = await fetch('/api/products');
                    products = await response.json();
                    displayProducts(products);
                } catch (error) {
                    console.error('Erro ao carregar produtos:', error);
                }
            }

            // Carregar clientes
            async function loadCustomers() {
                try {
                    const response = await fetch('/api/customers');
                    customers = await response.json();
                    displayCustomers(customers);
                } catch (error) {
                    console.error('Erro ao carregar clientes:', error);
                }
            }

            // Configurar leitor de código de barras
            function setupBarcodeScanner() {
                const barcodeInput = document.getElementById('barcodeInput');
                let barcode = '';
                let lastKeyTime = Date.now();
                
                barcodeInput.addEventListener('keydown', function(event) {
                    const currentTime = Date.now();
                    
                    if (currentTime - lastKeyTime > 100) {
                        barcode = '';
                    }
                    
                    lastKeyTime = currentTime;
                    
                    if (event.key.length === 1) {
                        barcode += event.key;
                    }
                    
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        
                        if (barcode.length >= 3) {
                            const cleanBarcode = barcode.replace('Enter', '');
                            searchProductByBarcode(cleanBarcode);
                            barcodeInput.value = '';
                            barcode = '';
                        }
                    }
                });
            }

            async function searchProductByBarcode(barcode) {
                try {
                    let product = products.find(p => p.code === barcode);
                    
                    if (!product) {
                        const response = await fetch(`/api/products/${barcode}`);
                        if (response.ok) {
                            product = await response.json();
                        }
                    }
                    
                    if (product) {
                        addToCart(product);
                        document.getElementById('barcodeInput').style.background = '#d4edda';
                        setTimeout(() => {
                            document.getElementById('barcodeInput').style.background = '';
                        }, 500);
                    } else {
                        document.getElementById('barcodeInput').style.background = '#f8d7da';
                        setTimeout(() => {
                            document.getElementById('barcodeInput').style.background = '';
                        }, 1000);
                    }
                    
                } catch (error) {
                    console.error('Erro ao buscar produto:', error);
                }
            }

            // Mostrar produtos
            function displayProducts(productsToShow) {
                const grid = document.getElementById('productsGrid');
                grid.innerHTML = '';

                productsToShow.forEach(product => {
                    const productCard = document.createElement('div');
                    productCard.className = 'product-card';
                    
                    let ivaBadge = '';
                    if (product.iva_rate === 0.07) {
                        ivaBadge = '<span style="background: #ffc107; color: black; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 5px;">IVA 7%</span>';
                    } else if (product.iva_rate === 0.00) {
                        ivaBadge = '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 5px;">ISENTO</span>';
                    } else {
                        ivaBadge = '<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 5px;">IVA 14%</span>';
                    }
                    
                    productCard.innerHTML = `
                        <div class="product-code">${product.code} ${ivaBadge}</div>
                        <div class="product-name">${product.name}</div>
                        <div class="product-price">${product.sale_price.toFixed(2)} €</div>
                        <div class="product-stock">Stock: ${product.stock}</div>
                    `;
                    productCard.addEventListener('click', () => addToCart(product));
                    grid.appendChild(productCard);
                });
            }

            // Mostrar clientes no dropdown
            function displayCustomers(customersList) {
                const select = document.getElementById('customerSelect');
                select.innerHTML = '<option value="">-- Cliente Anónimo --</option>';
                
                customersList.forEach(customer => {
                    const option = document.createElement('option');
                    option.value = customer.id;
                    option.textContent = `${customer.code} - ${customer.name}`;
                    select.appendChild(option);
                });

                select.addEventListener('change', function() {
                    const customerId = this.value;
                    selectedCustomer = customers.find(c => c.id == customerId) || null;
                    updateCustomerInfo();
                    discountApplied = false;
                    updateCartDisplay();
                });
            }

            // Atualizar informações do cliente
            function updateCustomerInfo() {
                const customerInfo = document.getElementById('customerInfo');
                
                if (selectedCustomer) {
                    customerInfo.innerHTML = `
                        <strong>${selectedCustomer.name}</strong><br>
                        Cartão: ${selectedCustomer.customer_card}<br>
                        Desconto: ${selectedCustomer.discount_rate}%<br>
                        Total Compras: ${selectedCustomer.total_purchases.toFixed(2)} €
                    `;
                    customerInfo.style.display = 'block';
                } else {
                    customerInfo.style.display = 'none';
                }
            }

            // Aplicar desconto do cartão
            function applyCustomerDiscount() {
                if (!selectedCustomer) {
                    alert('Selecione um cliente primeiro!');
                    return;
                }

                if (discountApplied) {
                    alert('Desconto já aplicado!');
                    return;
                }

                discountApplied = true;
                updateCartDisplay();
                alert(`Desconto de ${selectedCustomer.discount_rate}% aplicado!`);
            }

            // Adicionar ao carrinho
            function addToCart(product) {
                const existingItem = cart.find(item => item.code === product.code);
                
                if (existingItem) {
                    if (existingItem.quantity < product.stock) {
                        existingItem.quantity++;
                    } else {
                        alert('Stock insuficiente!');
                        return;
                    }
                } else {
                    if (product.stock > 0) {
                        cart.push({
                            ...product,
                            quantity: 1
                        });
                    } else {
                        alert('Produto sem stock!');
                        return;
                    }
                }
                
                updateCartDisplay();
            }

            // Atualizar display do carrinho
            function updateCartDisplay() {
                const cartItems = document.getElementById('cartItems');
                const subtotalEl = document.getElementById('subtotal');
                const discountEl = document.getElementById('discount');
                const ivaEl = document.getElementById('iva');
                const totalEl = document.getElementById('total');

                if (cart.length === 0) {
                    cartItems.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">Carrinho vazio</div>';
                    subtotalEl.textContent = '0,00 €';
                    discountEl.textContent = '0,00 €';
                    ivaEl.textContent = '0,00 €';
                    totalEl.textContent = '0,00 €';
                    return;
                }

                let subtotal = 0;
                let totalIva = 0;
                cartItems.innerHTML = '';

                cart.forEach(item => {
                    const itemTotal = item.sale_price * item.quantity;
                    const itemIva = itemTotal * item.iva_rate;
                    subtotal += itemTotal;
                    totalIva += itemIva;

                    const cartItem = document.createElement('div');
                    cartItem.className = 'cart-item';
                    cartItem.innerHTML = `
                        <div>
                            <div style="font-weight: bold;">${item.name}</div>
                            <div style="font-size: 12px; color: #666;">
                                ${item.sale_price.toFixed(2)} € × ${item.quantity} = ${itemTotal.toFixed(2)} €
                                <br><small>IVA: ${(item.iva_rate * 100).toFixed(0)}%</small>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button onclick="changeQuantity('${item.code}', -1)" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer;">-</button>
                            <span>${item.quantity}</span>
                            <button onclick="changeQuantity('${item.code}', 1)" style="padding: 5px 10px; border: 1px solid #ddd; background: white; cursor: pointer;">+</button>
                            <button onclick="removeFromCart('${item.code}')" style="color: #dc3545; border: none; background: none; cursor: pointer; margin-left: 10px;">❌</button>
                        </div>
                    `;
                    cartItems.appendChild(cartItem);
                });

                let discount = 0;
                if (selectedCustomer && discountApplied) {
                    discount = subtotal * (selectedCustomer.discount_rate / 100);
                }

                const subtotalAfterDiscount = subtotal - discount;
                const total = subtotalAfterDiscount + totalIva;

                subtotalEl.textContent = subtotal.toFixed(2) + ' €';
                discountEl.textContent = discount.toFixed(2) + ' €';
                ivaEl.textContent = totalIva.toFixed(2) + ' €';
                totalEl.textContent = total.toFixed(2) + ' €';
            }

            // Alterar quantidade
            function changeQuantity(productCode, change) {
                const item = cart.find(item => item.code === productCode);
                if (item) {
                    const newQuantity = item.quantity + change;
                    if (newQuantity < 1) {
                        removeFromCart(productCode);
                    } else {
                        const product = products.find(p => p.code === productCode);
                        if (newQuantity > product.stock) {
                            alert('Stock insuficiente!');
                            return;
                        }
                        item.quantity = newQuantity;
                    }
                    updateCartDisplay();
                }
            }

            // Remover do carrinho
            function removeFromCart(productCode) {
                cart = cart.filter(item => item.code !== productCode);
                updateCartDisplay();
            }

            // Limpar carrinho
            function clearCart() {
                if (cart.length === 0) return;
                if (confirm('Tem certeza que deseja limpar o carrinho?')) {
                    cart = [];
                    selectedCustomer = null;
                    discountApplied = false;
                    document.getElementById('customerSelect').value = '';
                    document.getElementById('customerInfo').style.display = 'none';
                    updateCartDisplay();
                }
            }

// Finalizar venda
async function finalizeSale(paymentMethod) {
    if (cart.length === 0) {
        alert('Adicione produtos ao carrinho primeiro!');
        return;
    }

    // Calcular totais
    let subtotal = 0;
    let totalIva = 0;

    cart.forEach(item => {
        const itemTotal = item.sale_price * item.quantity;
        const itemIva = itemTotal * item.iva_rate;
        subtotal += itemTotal;
        totalIva += itemIva;
    });

    let discount = 0;
    if (selectedCustomer && discountApplied) {
        discount = subtotal * (selectedCustomer.discount_rate / 100);
    }

    const subtotalAfterDiscount = subtotal - discount;
    const total = subtotalAfterDiscount + totalIva;

    // Se for pagamento em dinheiro, pedir valor pago
    let valorPago = 0;
    let troco = 0;
    
    if (paymentMethod === 'Dinheiro') {
        const valorPagoInput = prompt(
            `💵 Pagamento em Dinheiro\n\n` +
            `Total a pagar: ${total.toFixed(2)} €\n` +
            `Digite o valor recebido:`,
            total.toFixed(2)
        );
        
        if (valorPagoInput === null) {
            return; // Usuário cancelou
        }
        
        valorPago = parseFloat(valorPagoInput);
        
        if (isNaN(valorPago) || valorPago < total) {
            alert('Valor insuficiente! O valor pago deve ser maior ou igual ao total.');
            return;
        }
        
        troco = valorPago - total;
        
        if (!confirm(
            `💵 Confirmar Pagamento\n\n` +
            `Total: ${total.toFixed(2)} €\n` +
            `Valor pago: ${valorPago.toFixed(2)} €\n` +
            `Troco: ${troco.toFixed(2)} €\n\n` +
            `Confirmar venda?`
        )) {
            return;
        }
    } else {
        if (!confirm('Confirmar venda com pagamento em ' + paymentMethod + '?')) {
            return;
        }
    }

    try {
        // GERAR NÚMERO DA VENDA
        const saleNumber = 'V' + new Date().getTime() + Math.floor(Math.random() * 1000);

        const saleData = {
            sale_number: saleNumber,
            customer_id: selectedCustomer ? selectedCustomer.id : null,
            subtotal: subtotal,
            discount_amount: discount,
            iva_amount: totalIva,
            total: total,
            payment_method: paymentMethod,
            valor_pago: valorPago,  // Adicionar valor pago
            troco: troco,           // Adicionar troco
            items: cart.map(item => ({
                product_id: item.id,
                code: item.code,
                name: item.name,
                quantity: item.quantity,
                unit_price: item.sale_price,
                iva_rate: item.iva_rate,
                line_total: item.sale_price * item.quantity
            }))
        };

        console.log("📦 Dados enviados para venda:", saleData);

        const response = await fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(saleData)
        });

        const result = await response.json();

        if (result.success) {
            let mensagem = result.message;
            if (paymentMethod === 'Dinheiro') {
                mensagem += `\n\n💵 Troco: ${troco.toFixed(2)} €`;
            }
            alert(mensagem);
            
            // Preparar dados para impressão (incluindo troco)
            const printData = {
                sale_data: {
                    sale_number: saleNumber,
                    subtotal: subtotal,
                    discount_amount: discount,
                    iva_amount: totalIva,
                    total: total,
                    payment_method: paymentMethod,
                    valor_pago: valorPago,
                    troco: troco
                },
                items: cart.map(item => ({
                    name: item.name,
                    quantity: item.quantity,
                    unit_price: item.sale_price,
                    iva_rate: item.iva_rate,
                    line_total: item.sale_price * item.quantity
                })),
                customer: selectedCustomer ? {
                    name: selectedCustomer.name,
                    customer_card: selectedCustomer.customer_card
                } : null
            };

            console.log("🖨️ Dados enviados para impressão:", printData);
            
            // Imprimir recibo automaticamente
            await printReceipt(printData);
            
            // Limpar carrinho
            cart = [];
            selectedCustomer = null;
            discountApplied = false;
            document.getElementById('customerSelect').value = '';
            document.getElementById('customerInfo').style.display = 'none';
            updateCartDisplay();
            await loadProducts();
            await loadCustomers();
        } else {
            alert(result.message);
        }

    } catch (error) {
        alert('Erro ao processar venda: ' + error.message);
    }
}

// Função para imprimir recibo (CORRIGIDA)
async function printReceipt(printData) {
    try {
        console.log("🖨️ Enviando para impressão:", printData);
        
        const response = await fetch('/api/print_receipt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(printData)
        });
        
        const result = await response.json();
        console.log("🖨️ Resposta da impressão:", result);
        
        if (!result.success) {
            console.warn('Aviso: Não foi possível imprimir o recibo:', result.message);
        } else {
            console.log('✅ Recibo impresso com sucesso!');
        }
    } catch (error) {
        console.warn('Aviso: Erro ao tentar imprimir:', error.message);
    }
}

            // Pesquisar produtos
            document.getElementById('searchProduct').addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                const filteredProducts = products.filter(product => 
                    product.name.toLowerCase().includes(searchTerm) || 
                    product.code.toLowerCase().includes(searchTerm)
                );
                displayProducts(filteredProducts);
            });

            // Inicializar
            document.addEventListener('DOMContentLoaded', function() {
                loadProducts();
                loadCustomers();
                setupBarcodeScanner();
            });
        </script>
    </body>
    </html>
    ''')

# ========== ROTAS PARA PRODUTOS ==========
@app.route('/products')
def products_route():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gestão de Produtos</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #343a40; color: white; }
            tr:hover { background: #f8f9fa; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn-add { background: #28a745; }
            .btn-edit { background: #ffc107; color: black; }
            .btn-delete { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📋 Gestão de Produtos</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products" class="active">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>Lista de Produtos</h3>
                    <a href="/add_product" class="btn btn-add">➕ Adicionar Produto</a>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Nome</th>
                            <th>Preço (€)</th>
                            <th>Stock</th>
                            <th>IVA</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="productsTable">
                        <!-- Produtos carregados via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function loadProducts() {
                try {
                    const response = await fetch('/api/products_admin');
                    const products = await response.json();
                    displayProducts(products);
                } catch (error) {
                    console.error('Erro ao carregar produtos:', error);
                }
            }

            function displayProducts(products) {
                const tbody = document.getElementById('productsTable');
                tbody.innerHTML = '';

                products.forEach(product => {
                    const row = document.createElement('tr');
                    
                    let ivaText = '';
                    if (product.iva_rate === 0.07) {
                        ivaText = '7%';
                    } else if (product.iva_rate === 0.00) {
                        ivaText = 'ISENTO';
                    } else {
                        ivaText = '14%';
                    }
                    
                    row.innerHTML = `
                        <td>${product.code}</td>
                        <td>${product.name}</td>
                        <td>${product.sale_price.toFixed(2)}</td>
                        <td>${product.stock}</td>
                        <td>${ivaText}</td>
                        <td>
                            <a href="/edit_product/${product.id}" class="btn btn-edit" style="padding: 5px 10px; margin-right: 5px;">✏️ Editar</a>
                            <button onclick="deleteProduct(${product.id})" class="btn btn-delete" style="padding: 5px 10px;">🗑️ Eliminar</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }

            async function deleteProduct(productId) {
                if (!confirm('Tem certeza que deseja eliminar este produto?')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/delete_product/${productId}`, {
                        method: 'DELETE'
                    });

                    const result = await response.json();

                    if (result.success) {
                        alert(result.message);
                        loadProducts();
                    } else {
                        alert(result.message);
                    }
                } catch (error) {
                    alert('Erro ao eliminar produto: ' + error.message);
                }
            }

            document.addEventListener('DOMContentLoaded', loadProducts);
        </script>
    </body>
    </html>
    ''')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        sale_price = float(request.form['sale_price'])
        stock = int(request.form['stock'])
        iva_rate = float(request.form['iva_rate'])
        
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO products (code, name, sale_price, stock, iva_rate)
                VALUES (?, ?, ?, ?, ?)
            ''', (code, name, sale_price, stock, iva_rate))
            
            conn.commit()
            conn.close()
            
            return '''
            <script>
                alert('Produto adicionado com sucesso!');
                window.location.href = '/products';
            </script>
            '''
        except sqlite3.IntegrityError:
            conn.close()
            return '''
            <script>
                alert('Erro: Código do produto já existe!');
                window.location.href = '/add_product';
            </script>
            '''
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Adicionar Produto</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; }
            .form-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], input[type="number"], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>➕ Adicionar Produto</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="form-box">
                <h3>Informações do Produto</h3>
                <form method="POST">
                    <div class="form-group">
                        <label for="code">Código do Produto:</label>
                        <input type="text" id="code" name="code" required placeholder="Ex: P001">
                    </div>
                    
                    <div class="form-group">
                        <label for="name">Nome do Produto:</label>
                        <input type="text" id="name" name="name" required placeholder="Ex: Água Mineral 1L">
                    </div>
                    
                    <div class="form-group">
                        <label for="sale_price">Preço de Venda (€):</label>
                        <input type="number" id="sale_price" name="sale_price" step="0.01" min="0" required placeholder="0.00">
                    </div>
                    
                    <div class="form-group">
                        <label for="stock">Stock Inicial:</label>
                        <input type="number" id="stock" name="stock" min="0" required value="0">
                    </div>
                    
                    <div class="form-group">
                        <label for="iva_rate">Taxa de IVA:</label>
                        <select id="iva_rate" name="iva_rate">
                            <option value="0.14" selected>14%</option>
                            <option value="0.07">7%</option>
                            <option value="0.00">0% (Isento)</option>
                        </select>
                    </div>
                    
                    <button type="submit">💾 Guardar Produto</button>
                    <a href="/products" style="margin-left: 15px; color: #6c757d; text-decoration: none;">↩️ Cancelar</a>
                </form>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Processar edição do produto
        code = request.form['code']
        name = request.form['name']
        sale_price = float(request.form['sale_price'])
        stock = int(request.form['stock'])
        iva_rate = float(request.form['iva_rate'])
        
        try:
            cursor.execute('''
                UPDATE products 
                SET code = ?, name = ?, sale_price = ?, stock = ?, iva_rate = ?
                WHERE id = ?
            ''', (code, name, sale_price, stock, iva_rate, product_id))
            
            conn.commit()
            conn.close()
            
            return '''
            <script>
                alert('Produto atualizado com sucesso!');
                window.location.href = '/products';
            </script>
            '''
        except sqlite3.IntegrityError:
            conn.close()
            return '''
            <script>
                alert('Erro: Código do produto já existe!');
                window.location.href = '/products';
            </script>
            '''
    
    # Carregar dados do produto
    cursor.execute('SELECT id, code, name, sale_price, stock, iva_rate FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        return '''
        <script>
            alert('Produto não encontrado!');
            window.location.href = '/products';
        </script>
        '''
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Editar Produto</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; }
            .form-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], input[type="number"], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✏️ Editar Produto</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="form-box">
                <h3>Editar Produto: {{ product[1] }}</h3>
                <form method="POST">
                    <div class="form-group">
                        <label for="code">Código do Produto:</label>
                        <input type="text" id="code" name="code" value="{{ product[1] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="name">Nome do Produto:</label>
                        <input type="text" id="name" name="name" value="{{ product[2] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="sale_price">Preço de Venda (€):</label>
                        <input type="number" id="sale_price" name="sale_price" step="0.01" min="0" value="{{ "%.2f"|format(product[3]) }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="stock">Stock:</label>
                        <input type="number" id="stock" name="stock" min="0" value="{{ product[4] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="iva_rate">Taxa de IVA:</label>
                        <select id="iva_rate" name="iva_rate">
                            <option value="0.14" {{ "selected" if product[5] == 0.14 else "" }}>14%</option>
                            <option value="0.07" {{ "selected" if product[5] == 0.07 else "" }}>7%</option>
                            <option value="0.00" {{ "selected" if product[5] == 0.00 else "" }}>0% (Isento)</option>
                        </select>
                    </div>
                    
                    <button type="submit">💾 Atualizar Produto</button>
                    <a href="/products" style="margin-left: 15px; color: #6c757d; text-decoration: none;">↩️ Cancelar</a>
                </form>
            </div>
        </div>
    </body>
    </html>
    ''', product=product)

# ========== ROTAS PARA CLIENTES ==========
@app.route('/customers')
def customers_route():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gestão de Clientes</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #343a40; color: white; }
            tr:hover { background: #f8f9fa; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn-add { background: #28a745; }
            .btn-edit { background: #ffc107; color: black; }
            .btn-delete { background: #dc3545; }
            .btn-history { background: #17a2b8; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👥 Gestão de Clientes</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers" class="active">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>Lista de Clientes</h3>
                    <a href="/add_customer" class="btn btn-add">➕ Adicionar Cliente</a>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Código</th>
                            <th>Nome</th>
                            <th>Telefone</th>
                            <th>Cartão</th>
                            <th>Desconto</th>
                            <th>Total Compras</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="customersTable">
                        <!-- Clientes carregados via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function loadCustomers() {
                try {
                    const response = await fetch('/api/customers');
                    const customers = await response.json();
                    displayCustomers(customers);
                } catch (error) {
                    console.error('Erro ao carregar clientes:', error);
                }
            }

            function displayCustomers(customers) {
                const tbody = document.getElementById('customersTable');
                tbody.innerHTML = '';

                customers.forEach(customer => {
                    const row = document.createElement('tr');
                    
                    row.innerHTML = `
                        <td>${customer.code}</td>
                        <td>${customer.name}</td>
                        <td>${customer.phone || '-'}</td>
                        <td>${customer.customer_card}</td>
                        <td>${customer.discount_rate}%</td>
                        <td>${customer.total_purchases.toFixed(2)} €</td>
                        <td>
                            <a href="/customer_history/${customer.id}" class="btn btn-history" style="padding: 5px 10px; margin-right: 5px;">📊 Histórico</a>
                            <a href="/edit_customer/${customer.id}" class="btn btn-edit" style="padding: 5px 10px; margin-right: 5px;">✏️ Editar</a>
                            <button onclick="deleteCustomer(${customer.id})" class="btn btn-delete" style="padding: 5px 10px;">🗑️ Eliminar</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }

            async function deleteCustomer(customerId) {
                if (!confirm('Tem certeza que deseja eliminar este cliente?')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/delete_customer/${customerId}`, {
                        method: 'DELETE'
                    });

                    const result = await response.json();

                    if (result.success) {
                        alert(result.message);
                        loadCustomers();
                    } else {
                        alert(result.message);
                    }
                } catch (error) {
                    alert('Erro ao eliminar cliente: ' + error.message);
                }
            }

            document.addEventListener('DOMContentLoaded', loadCustomers);
        </script>
    </body>
    </html>
    ''')

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        nif = request.form.get('nif', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        customer_card = request.form['customer_card']
        discount_rate = float(request.form['discount_rate'])
        
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO customers (code, name, nif, phone, email, address, customer_card, discount_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, name, nif, phone, email, address, customer_card, discount_rate))
            
            conn.commit()
            conn.close()
            
            return '''
            <script>
                alert('Cliente adicionado com sucesso!');
                window.location.href = '/customers';
            </script>
            '''
        except sqlite3.IntegrityError:
            conn.close()
            return '''
            <script>
                alert('Erro: Código ou cartão do cliente já existe!');
                window.location.href = '/add_customer';
            </script>
            '''
    
    # Gerar código e cartão automáticos
    code = f"C{random.randint(1000, 9999)}"
    customer_card = f"CARD{random.randint(10000, 99999)}"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Adicionar Cliente</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; }
            .form-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], input[type="number"], input[type="email"], textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>➕ Adicionar Cliente</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="form-box">
                <h3>Informações do Cliente</h3>
                <form method="POST">
                    <div class="form-group">
                        <label for="code">Código do Cliente:</label>
                        <input type="text" id="code" name="code" value="''' + code + '''" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="name">Nome Completo:</label>
                        <input type="text" id="name" name="name" required placeholder="Ex: Maria Silva">
                    </div>
                    
                    <div class="form-group">
                        <label for="nif">NIF:</label>
                        <input type="text" id="nif" name="nif" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Telefone:</label>
                        <input type="text" id="phone" name="phone" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="address">Endereço:</label>
                        <textarea id="address" name="address" rows="3" placeholder="Opcional"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="customer_card">Nº Cartão do Cliente:</label>
                        <input type="text" id="customer_card" name="customer_card" value="''' + customer_card + '''" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="discount_rate">Taxa de Desconto (%):</label>
                        <input type="number" id="discount_rate" name="discount_rate" step="0.1" min="0" max="50" value="0.0" required>
                    </div>
                    
                    <button type="submit">💾 Guardar Cliente</button>
                    <a href="/customers" style="margin-left: 15px; color: #6c757d; text-decoration: none;">↩️ Cancelar</a>
                </form>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Processar edição do cliente
        code = request.form['code']
        name = request.form['name']
        nif = request.form.get('nif', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        customer_card = request.form['customer_card']
        discount_rate = float(request.form['discount_rate'])
        
        try:
            cursor.execute('''
                UPDATE customers 
                SET code = ?, name = ?, nif = ?, phone = ?, email = ?, address = ?, customer_card = ?, discount_rate = ?
                WHERE id = ?
            ''', (code, name, nif, phone, email, address, customer_card, discount_rate, customer_id))
            
            conn.commit()
            conn.close()
            
            return '''
            <script>
                alert('Cliente atualizado com sucesso!');
                window.location.href = '/customers';
            </script>
            '''
        except sqlite3.IntegrityError:
            conn.close()
            return '''
            <script>
                alert('Erro: Código ou cartão do cliente já existe!');
                window.location.href = '/customers';
            </script>
            '''
    
    # Carregar dados do cliente
    cursor.execute('''
        SELECT id, code, name, nif, phone, email, address, customer_card, discount_rate 
        FROM customers WHERE id = ?
    ''', (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    
    if not customer:
        return '''
        <script>
            alert('Cliente não encontrado!');
            window.location.href = '/customers';
        </script>
        '''
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Editar Cliente</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; }
            .form-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], input[type="number"], input[type="email"], textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✏️ Editar Cliente</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="form-box">
                <h3>Editar Cliente: {{ customer[2] }}</h3>
                <form method="POST">
                    <div class="form-group">
                        <label for="code">Código do Cliente:</label>
                        <input type="text" id="code" name="code" value="{{ customer[1] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="name">Nome Completo:</label>
                        <input type="text" id="name" name="name" value="{{ customer[2] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="nif">NIF:</label>
                        <input type="text" id="nif" name="nif" value="{{ customer[3] or '' }}" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Telefone:</label>
                        <input type="text" id="phone" name="phone" value="{{ customer[4] or '' }}" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" value="{{ customer[5] or '' }}" placeholder="Opcional">
                    </div>
                    
                    <div class="form-group">
                        <label for="address">Endereço:</label>
                        <textarea id="address" name="address" rows="3" placeholder="Opcional">{{ customer[6] or '' }}</textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="customer_card">Nº Cartão do Cliente:</label>
                        <input type="text" id="customer_card" name="customer_card" value="{{ customer[7] }}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="discount_rate">Taxa de Desconto (%):</label>
                        <input type="number" id="discount_rate" name="discount_rate" step="0.1" min="0" max="50" value="{{ "%.1f"|format(customer[8]) }}" required>
                    </div>
                    
                    <button type="submit">💾 Atualizar Cliente</button>
                    <a href="/customers" style="margin-left: 15px; color: #6c757d; text-decoration: none;">↩️ Cancelar</a>
                </form>
            </div>
        </div>
    </body>
    </html>
    ''', customer=customer)

@app.route('/customer_history/<int:customer_id>')
def customer_history(customer_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    
    # Carregar informações do cliente
    cursor.execute('SELECT name, customer_card FROM customers WHERE id = ?', (customer_id,))
    customer = cursor.fetchone()
    
    if not customer:
        conn.close()
        return '''
        <script>
            alert('Cliente não encontrado!');
            window.location.href = '/customers';
        </script>
        '''
    
    # Carregar histórico de compras
    cursor.execute('''
        SELECT s.sale_number, s.total, s.payment_method, s.created_at, u.full_name
        FROM sales s
        JOIN users u ON s.user_id = u.id
        WHERE s.customer_id = ?
        ORDER BY s.created_at DESC
    ''', (customer_id,))
    sales_history = cursor.fetchall()
    
    # Calcular estatísticas
    cursor.execute('''
        SELECT COUNT(*), SUM(total), AVG(total), MAX(created_at)
        FROM sales 
        WHERE customer_id = ?
    ''', (customer_id,))
    stats = cursor.fetchone()
    
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Histórico do Cliente</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
            .stat-value { font-size: 24px; font-weight: bold; color: #007bff; margin: 10px 0; }
            .stat-label { color: #666; font-size: 14px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #343a40; color: white; }
            tr:hover { background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Histórico do Cliente</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="card">
                <h2>{{ customer[0] }}</h2>
                <p><strong>Cartão:</strong> {{ customer[1] }}</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total de Compras</div>
                    <div class="stat-value">{{ stats[0] or 0 }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Valor Total Gasto</div>
                    <div class="stat-value">{{ "%.2f"|format(stats[1] or 0) }} €</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Valor Médio por Compra</div>
                    <div class="stat-value">{{ "%.2f"|format(stats[2] or 0) }} €</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Última Compra</div>
                    <div class="stat-value" style="font-size: 16px;">{{ stats[3] or 'Nunca' }}</div>
                </div>
            </div>

            <div class="card">
                <h3>Histórico de Compras</h3>
                {% if sales_history %}
                <table>
                    <thead>
                        <tr>
                            <th>Nº Venda</th>
                            <th>Valor</th>
                            <th>Pagamento</th>
                            <th>Operador</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sale in sales_history %}
                        <tr>
                            <td>{{ sale[0] }}</td>
                            <td>{{ "%.2f"|format(sale[1]) }} €</td>
                            <td>{{ sale[2] }}</td>
                            <td>{{ sale[4] }}</td>
                            <td>{{ sale[3] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="text-align: center; color: #999; padding: 20px;">Nenhuma compra registrada</p>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    ''', customer=customer, sales_history=sales_history, stats=stats)

# ========== ROTAS PARA RELATÓRIOS AVANÇADOS ==========
@app.route('/advanced_reports')
def advanced_reports():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Obter parâmetros de filtro
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    summary = reports.get_sales_summary(start_date, end_date)
    top_products = reports.get_top_products(10, start_date, end_date)
    payment_methods = reports.get_payment_methods_summary(start_date, end_date)
    
    # Gerar gráficos
    sales_chart = reports.create_sales_chart('daily', 30)
    products_chart = reports.create_top_products_chart(10)
    payment_chart = reports.create_payment_methods_chart()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Relatórios Avançados - Sistema de Vendas</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; }
            .filters { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
            .stat-value { font-size: 24px; font-weight: bold; color: #007bff; margin: 10px 0; }
            .stat-label { color: #666; font-size: 14px; }
            .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .chart-container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .table-container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #343a40; color: white; }
            tr:hover { background: #f8f9fa; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn-export { background: #28a745; margin-left: 10px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📈 Relatórios Avançados</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports" class="active">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <!-- Filtros -->
            <div class="filters">
                <h3>🔍 Filtros do Relatório</h3>
                <form method="GET" action="/advanced_reports" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; align-items: end;">
                    <div>
                        <label for="start_date">Data Início:</label>
                        <input type="date" id="start_date" name="start_date" value="{{ start_date }}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
                    </div>
                    <div>
                        <label for="end_date">Data Fim:</label>
                        <input type="date" id="end_date" name="end_date" value="{{ end_date }}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
                    </div>
                    <div>
                        <button type="submit" class="btn">🔍 Aplicar Filtros</button>
                        <a href="/advanced_reports" class="btn" style="background: #6c757d;">🔄 Limpar</a>
                    </div>
                </form>
            </div>

            <!-- Estatísticas -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total de Vendas</div>
                    <div class="stat-value">{{ summary['total_vendas'] }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Faturação Total</div>
                    <div class="stat-value">{{ "%.2f"|format(summary['total_faturado']) }} €</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Média por Venda</div>
                    <div class="stat-value">{{ "%.2f"|format(summary['media_venda']) }} €</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total IVA</div>
                    <div class="stat-value">{{ "%.2f"|format(summary['total_iva']) }} €</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Descontos</div>
                    <div class="stat-value">{{ "%.2f"|format(summary['total_descontos']) }} €</div>
                </div>
            </div>

            <!-- Gráficos -->
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>📊 Evolução de Vendas</h3>
                    {% if sales_chart %}
                        <img src="{{ sales_chart }}" style="width: 100%;" alt="Gráfico de Vendas">
                    {% else %}
                        <p>Sem dados para exibir</p>
                    {% endif %}
                </div>
                <div class="chart-container">
                    <h3>🏆 Produtos Mais Vendidos</h3>
                    {% if products_chart %}
                        <img src="{{ products_chart }}" style="width: 100%;" alt="Gráfico de Produtos">
                    {% else %}
                        <p>Sem dados para exibir</p>
                    {% endif %}
                </div>
                <div class="chart-container">
                    <h3>💳 Métodos de Pagamento</h3>
                    {% if payment_chart %}
                        <img src="{{ payment_chart }}" style="width: 100%;" alt="Gráfico de Pagamentos">
                    {% else %}
                        <p>Sem dados para exibir</p>
                    {% endif %}
                </div>
            </div>

            <!-- Tabelas -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="table-container">
                    <h3>🏆 Top 10 Produtos</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Produto</th>
                                <th>Qtd Vendida</th>
                                <th>Total (€)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for p in top_products %}
                            <tr>
                                <td>{{ p['produto'] }}</td>
                                <td>{{ p['quantidade'] }}</td>
                                <td>{{ "%.2f"|format(p['total']) }}</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="3">Sem dados</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                <div class="table-container">
                    <h3>💳 Métodos de Pagamento</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Método</th>
                                <th>Qtd Vendas</th>
                                <th>Total (€)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for p in payment_methods %}
                            <tr>
                                <td>{{ p['metodo'] }}</td>
                                <td>{{ p['quantidade'] }}</td>
                                <td>{{ "%.2f"|format(p['total']) }}</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="3">Sem dados</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Botões de Exportação -->
            <div style="margin-top: 20px; text-align: center;">
                <a href="/api/export_reports?type=excel&start_date={{ start_date }}&end_date={{ end_date }}" class="btn btn-export">📊 Exportar Excel</a>
                <a href="/api/export_reports?type=csv&start_date={{ start_date }}&end_date={{ end_date }}" class="btn btn-export">📁 Exportar CSV</a>
            </div>
        </div>
    </body>
    </html>
    ''', summary=summary, top_products=top_products, payment_methods=payment_methods, 
    sales_chart=sales_chart, products_chart=products_chart, payment_chart=payment_chart,
    start_date=start_date, end_date=end_date)

# ========== APIs PARA EXPORTAÇÃO ==========
@app.route('/api/export_reports')
def api_export_reports():
    if 'user_id' not in session:
        return redirect('/login')
    
    export_type = request.args.get('type', 'excel')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Coletar dados
    summary = reports.get_sales_summary(start_date, end_date)
    top_products = reports.get_top_products(50, start_date, end_date)
    payment_methods = reports.get_payment_methods_summary(start_date, end_date)
    sales_data = reports.get_sales_by_period('daily', 365)
    
    if export_type == 'csv':
        # Gerar CSV
        output = io.StringIO()
        
        # Resumo
        output.write("RELATÓRIO DE VENDAS - RESUMO\n")
        output.write(f"Período: {start_date} a {end_date}\n\n")
        for key, value in summary.items():
            output.write(f"{key},{value}\n")
        
        output.write("\nTOP PRODUTOS\n")
        output.write("Produto,Quantidade,Total\n")
        for product in top_products:
            output.write(f"{product['produto']},{product['quantidade']},{product['total']:.2f}\n")
        
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=relatorio_vendas_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    
    else:  # Excel
        # Criar DataFrame do pandas
        df_summary = pd.DataFrame([summary])
        df_products = pd.DataFrame(top_products)
        df_payments = pd.DataFrame(payment_methods)
        df_sales = pd.DataFrame(sales_data)
        
        # Criar arquivo Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Resumo', index=False)
            df_products.to_excel(writer, sheet_name='Top Produtos', index=False)
            df_payments.to_excel(writer, sheet_name='Métodos Pagamento', index=False)
            df_sales.to_excel(writer, sheet_name='Vendas por Período', index=False)
        
        output.seek(0)
        
        return output.getvalue(), 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': f'attachment; filename=relatorio_vendas_{datetime.now().strftime("%Y%m%d")}.xlsx'
        }

# ========== SISTEMA DE CONFIGURAÇÕES ==========
# ========== SISTEMA DE CONFIGURAÇÕES ==========
@app.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        # Salvar configurações da empresa
        save_setting('company_name', request.form.get('company_name', 'LOJA EXEMPLO'))
        save_setting('company_address', request.form.get('company_address', ''))
        save_setting('company_phone', request.form.get('company_phone', ''))
        save_setting('company_email', request.form.get('company_email', ''))
        
        # Salvar configurações fiscais
        save_setting('company_nif', request.form.get('company_nif', ''))
        save_setting('iva_default', request.form.get('iva_default', '0.14'))
        save_setting('currency', request.form.get('currency', '€'))
        
        # Salvar configurações de backup
        save_setting('backup_frequency', request.form.get('backup_frequency', 'daily'))
        
        return '''
        <script>
            alert('Configurações do sistema salvas com sucesso!');
            window.location.href = '/system_settings';
        </script>
        '''
    
    # Carregar configurações atuais
    company_name = get_setting('company_name', 'LOJA EXEMPLO')
    company_address = get_setting('company_address', '')
    company_phone = get_setting('company_phone', '')
    company_email = get_setting('company_email', '')
    company_nif = get_setting('company_nif', '')
    iva_default = get_setting('iva_default', '0.14')
    currency = get_setting('currency', '€')
    backup_frequency = get_setting('backup_frequency', 'daily')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configurações do Sistema</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 800px; margin: 0 auto; }
            .settings-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], input[type="number"], input[type="email"], select, textarea { 
                width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; 
            }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .tab-container { margin-bottom: 20px; }
            .tab-buttons { display: flex; border-bottom: 1px solid #ddd; }
            .tab-button { padding: 10px 20px; background: #f8f9fa; border: none; cursor: pointer; }
            .tab-button.active { background: #007bff; color: white; }
            .tab-content { display: none; padding: 20px 0; }
            .tab-content.active { display: block; }
            .btn-backup { background: #28a745; margin-right: 10px; }
            .btn-restore { background: #ffc107; color: black; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚙️ Configurações do Sistema</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings" class="active">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="settings-box">
                <div class="tab-container">
                    <div class="tab-buttons">
                        <button class="tab-button active" onclick="openTab('empresa')">🏢 Empresa</button>
                        <button class="tab-button" onclick="openTab('fiscal')">💰 Fiscal</button>
                        <button class="tab-button" onclick="openTab('backup')">💾 Backup</button>
                    </div>
                    
                    <form method="POST">
                        <!-- Tab Empresa -->
                        <div id="empresa" class="tab-content active">
                            <h3>Informações da Empresa</h3>
                            
                            <div class="form-group">
                                <label for="company_name">Nome da Empresa:</label>
                                <input type="text" id="company_name" name="company_name" value="''' + company_name + '''" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="company_address">Endereço:</label>
                                <textarea id="company_address" name="company_address" rows="3" placeholder="Endereço completo da empresa">''' + company_address + '''</textarea>
                            </div>
                            
                            <div class="form-group">
                                <label for="company_phone">Telefone:</label>
                                <input type="text" id="company_phone" name="company_phone" value="''' + company_phone + '''" placeholder="+244 XXX XXX XXX">
                            </div>
                            
                            <div class="form-group">
                                <label for="company_email">Email:</label>
                                <input type="email" id="company_email" name="company_email" value="''' + company_email + '''" placeholder="empresa@exemplo.com">
                            </div>
                        </div>
                        
                        <!-- Tab Fiscal -->
                        <div id="fiscal" class="tab-content">
                            <h3>Configurações Fiscais</h3>
                            
                            <div class="form-group">
                                <label for="company_nif">NIF:</label>
                                <input type="text" id="company_nif" name="company_nif" value="''' + company_nif + '''" placeholder="Número de Identificação Fiscal">
                            </div>
                            
                            <div class="form-group">
                                <label for="iva_default">IVA Padrão (%):</label>
                                <select id="iva_default" name="iva_default">
                                    <option value="0.14" ''' + ('selected' if iva_default == '0.14' else '') + '''>14%</option>
                                    <option value="0.07" ''' + ('selected' if iva_default == '0.07' else '') + '''>7%</option>
                                    <option value="0.00" ''' + ('selected' if iva_default == '0.00' else '') + '''>0%</option>
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label for="currency">Moeda:</label>
                                <select id="currency" name="currency">
                                    <option value="€" ''' + ('selected' if currency == '€' else '') + '''>Euro (€)</option>
                                    <option value="Kz" ''' + ('selected' if currency == 'Kz' else '') + '''>Kwanza (Kz)</option>
                                    <option value="$" ''' + ('selected' if currency == '$' else '') + '''>Dólar ($)</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- Tab Backup -->
                        <div id="backup" class="tab-content">
                            <h3>Backup e Segurança</h3>
                            
                            <div class="form-group">
                                <label>Backup Automático:</label>
                                <div>
                                    <input type="radio" id="backup_daily" name="backup_frequency" value="daily" ''' + ('checked' if backup_frequency == 'daily' else '') + '''>
                                    <label for="backup_daily" style="display: inline; margin-right: 15px;">Diário</label>
                                    
                                    <input type="radio" id="backup_weekly" name="backup_frequency" value="weekly" ''' + ('checked' if backup_frequency == 'weekly' else '') + '''>
                                    <label for="backup_weekly" style="display: inline; margin-right: 15px;">Semanal</label>
                                    
                                    <input type="radio" id="backup_manual" name="backup_frequency" value="manual" ''' + ('checked' if backup_frequency == 'manual' else '') + '''>
                                    <label for="backup_manual" style="display: inline;">Manual</label>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <button type="button" class="btn-backup" onclick="createBackup()">💾 Criar Backup Agora</button>
                                <button type="button" class="btn-restore" onclick="restoreBackup()">🔄 Restaurar Backup</button>
                            </div>
                            
                            <div class="form-group">
                                <label>Último Backup:</label>
                                <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
                                    <span id="lastBackupInfo">Carregando...</span>
                                </div>
                            </div>
                        </div>
                        
                        <button type="submit">💾 Salvar Configurações</button>
                    </form>
                </div>
            </div>
        </div>

        <script>
            function openTab(tabName) {
                // Esconder todas as tabs
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.tab-button').forEach(button => {
                    button.classList.remove('active');
                });
                
                // Mostrar tab selecionada
                document.getElementById(tabName).classList.add('active');
                event.currentTarget.classList.add('active');
            }
            
            function createBackup() {
                if (confirm('Deseja criar um backup do sistema agora?')) {
                    fetch('/api/create_backup', {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Backup criado com sucesso!');
                            updateLastBackupInfo();
                        } else {
                            alert('Erro ao criar backup: ' + data.message);
                        }
                    })
                    .catch(error => {
                        alert('Erro ao criar backup: ' + error.message);
                    });
                }
            }
            
            function restoreBackup() {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = '.db,.sqlite,.sqlite3';
                
                fileInput.onchange = function(event) {
                    const file = event.target.files[0];
                    if (file) {
                        if (confirm('ATENÇÃO: Esta ação irá substituir todos os dados atuais. Continuar?')) {
                            const formData = new FormData();
                            formData.append('backup_file', file);
                            
                            fetch('/api/restore_backup', {
                                method: 'POST',
                                body: formData
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    alert('Backup restaurado com sucesso! O sistema será reiniciado.');
                                    setTimeout(() => {
                                        window.location.href = '/';
                                    }, 2000);
                                } else {
                                    alert('Erro ao restaurar backup: ' + data.message);
                                }
                            })
                            .catch(error => {
                                alert('Erro ao restaurar backup: ' + error.message);
                            });
                        }
                    }
                };
                
                fileInput.click();
            }
            
            function updateLastBackupInfo() {
                fetch('/api/get_backup_info')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('lastBackupInfo').textContent = data.last_backup || 'Nenhum backup realizado';
                    })
                    .catch(error => {
                        document.getElementById('lastBackupInfo').textContent = 'Erro ao carregar informação';
                    });
            }
            
            // Carregar informações do backup ao abrir a página
            document.addEventListener('DOMContentLoaded', updateLastBackupInfo);
        </script>
    </body>
    </html>
    ''')

# ========== ROTAS PARA IMPRESSORA ==========
@app.route('/printer_settings', methods=['GET', 'POST'])
def printer_settings():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        # Salvar configurações da impressora
        save_setting('printer_type', request.form.get('printer_type', 'file'))
        save_setting('printer_address', request.form.get('printer_address', '192.168.1.100'))
        save_setting('company_name', request.form.get('company_name', 'LOJA EXEMPLO'))
        save_setting('company_address', request.form.get('company_address', 'Rua Principal, 123 - Luanda'))
        save_setting('company_nif', request.form.get('company_nif', '123456789'))
        
        # Reconfigurar a impressora com as novas configurações
        printer.setup_printer()
        
        return '''
        <script>
            alert('Configurações da impressora salvas com sucesso!');
            window.location.href = '/printer_settings';
        </script>
        '''
    
    # Carregar configurações atuais
    printer_type = get_setting('printer_type', 'file')
    printer_address = get_setting('printer_address', '192.168.1.100')
    company_name = get_setting('company_name', 'LOJA EXEMPLO')
    company_address = get_setting('company_address', 'Rua Principal, 123 - Luanda')
    company_nif = get_setting('company_nif', '123456789')
    
    status_class = 'status-success' if ESCPOS_AVAILABLE else 'status-error'
    status_message = 'Biblioteca escpos instalada' if ESCPOS_AVAILABLE else 'Biblioteca escpos não encontrada'
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configurações da Impressora</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; max-width: 600px; margin: 0 auto; }
            .form-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
            input[type="text"], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .btn-test { background: #28a745; margin-left: 10px; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .status-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🖨️ Configurações da Impressora</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings" class="active">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="form-box">
                <h3>Configurações da Impressora Térmica</h3>
                
                <div class="status ''' + status_class + '''">
                    <strong>Status:</strong> ''' + status_message + '''
                </div>
                
                <form method="POST">
                    <div class="form-group">
                        <label for="printer_type">Tipo de Impressora:</label>
                        <select id="printer_type" name="printer_type">
                            <option value="usb" ''' + ('selected' if printer_type == 'usb' else '') + '''>USB</option>
                            <option value="network" ''' + ('selected' if printer_type == 'network' else '') + '''>Rede (IP)</option>
                            <option value="file" ''' + ('selected' if printer_type == 'file' else '') + '''>Arquivo (Teste)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="printer_address">Endereço/IP da Impressora:</label>
                        <input type="text" id="printer_address" name="printer_address" value="''' + printer_address + '''" placeholder="Ex: 192.168.1.100 ou /dev/usb/lp0">
                    </div>
                    
                    <div class="form-group">
                        <label for="company_name">Nome da Empresa:</label>
                        <input type="text" id="company_name" name="company_name" value="''' + company_name + '''" placeholder="Nome que aparece no recibo">
                    </div>
                    
                    <div class="form-group">
                        <label for="company_address">Endereço da Empresa:</label>
                        <input type="text" id="company_address" name="company_address" value="''' + company_address + '''" placeholder="Endereço para o recibo">
                    </div>
                    
                    <div class="form-group">
                        <label for="company_nif">NIF da Empresa:</label>
                        <input type="text" id="company_nif" name="company_nif" value="''' + company_nif + '''" placeholder="NIF para o recibo">
                    </div>
                    
                    <button type="submit">💾 Salvar Configurações</button>
                    <button type="button" class="btn-test" onclick="testPrint()">🖨️ Testar Impressão</button>
                </form>
                
                <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
                    <h4>📋 Instruções de Instalação:</h4>
                    <ol>
                        <li>Instale a biblioteca: <code>pip install escpos</code></li>
                        <li>Conecte a impressora térmica via USB ou rede</li>
                        <li>Configure o endereço correto acima</li>
                        <li>Teste a impressão com o botão "Testar Impressão"</li>
                    </ol>
                    
                    <h4 style="margin-top: 15px;">📝 Informações:</h4>
                    <ul>
                        <li><strong>USB:</strong> Use "LPT1:" no Windows ou "/dev/usb/lp0" no Linux</li>
                        <li><strong>Rede:</strong> Digite o IP da impressora (ex: 192.168.1.100)</li>
                        <li><strong>Arquivo:</strong> Gera um arquivo "recibo.txt" para teste</li>
                    </ul>
                </div>
            </div>
        </div>

        <script>
            async function testPrint() {
                try {
                    const response = await fetch('/api/test_print', {
                        method: 'POST'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        alert('Teste de impressão enviado com sucesso! Verifique a impressora ou o arquivo recibo.txt');
                    } else {
                        alert('Erro no teste de impressão: ' + result.message);
                    }
                } catch (error) {
                    alert('Erro ao testar impressão: ' + error.message);
                }
            }
            
            // Atualizar campo de endereço baseado no tipo selecionado
            document.getElementById('printer_type').addEventListener('change', function() {
                const addressField = document.getElementById('printer_address');
                const type = this.value;
                
                if (type === 'usb') {
                    addressField.value = navigator.platform.toLowerCase().includes('win') ? 'LPT1:' : '/dev/usb/lp0';
                    addressField.placeholder = 'Ex: LPT1: ou /dev/usb/lp0';
                } else if (type === 'network') {
                    addressField.value = '192.168.1.100';
                    addressField.placeholder = 'Ex: 192.168.1.100';
                } else {
                    addressField.value = 'recibo.txt';
                    addressField.placeholder = 'Nome do arquivo para teste';
                }
            });
        </script>
    </body>
    </html>
    ''')

# ========== APIs PARA IMPRESSORA ==========
@app.route('/api/test_print', methods=['POST'])
def api_test_print():
    try:
        test_sale = {
            'sale_number': 'TEST123',
            'subtotal': 100.0,
            'discount_amount': 10.0,
            'iva_amount': 12.6,
            'total': 102.6,
            'payment_method': 'Dinheiro'
        }
        
        test_items = [
            {
                'name': 'Produto Teste 1',
                'quantity': 2,
                'unit_price': 25.0,
                'iva_rate': 0.14,
                'line_total': 50.0
            },
            {
                'name': 'Produto Teste 2 com IVA 7%',
                'quantity': 1,
                'unit_price': 50.0,
                'iva_rate': 0.07,
                'line_total': 50.0
            }
        ]
        
        test_customer = {
            'name': 'Cliente Teste',
            'customer_card': 'CARD_TEST'
        }
        
        success = printer.print_receipt(test_sale, test_items, test_customer)
        
        return jsonify({
            'success': success,
            'message': 'Teste de impressão realizado' if success else 'Falha na impressão'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/print_receipt', methods=['POST'])
def api_print_receipt():
    try:
        data = request.json
        print(f"🖨️ Dados recebidos para impressão: {data}")
        
        # Verificar se os dados necessários estão presentes
        if not data or 'sale_data' not in data or 'items' not in data:
            return jsonify({
                'success': False, 
                'message': 'Dados incompletos para impressão'
            }), 400
        
        success = printer.print_receipt(
            data['sale_data'], 
            data['items'], 
            data.get('customer')
        )
        
        return jsonify({
            'success': success,
            'message': 'Recibo impresso com sucesso' if success else 'Falha na impressão'
        })
        
    except Exception as e:
        print(f"❌ Erro na impressão: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Erro na impressão: {str(e)}'
        }), 500

# ========== APIs EXISTENTES ==========
@app.route('/api/products')
def api_products():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, name, sale_price, stock, iva_rate FROM products WHERE is_active = 1 AND stock > 0 ORDER BY name')
    products = cursor.fetchall()
    conn.close()
    
    products_list = []
    for product in products:
        products_list.append({
            'id': product[0],
            'code': product[1],
            'name': product[2],
            'sale_price': float(product[3]),
            'stock': product[4],
            'iva_rate': float(product[5])
        })
    
    return jsonify(products_list)

@app.route('/api/products_admin')
def api_products_admin():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, name, sale_price, stock, iva_rate FROM products WHERE is_active = 1 ORDER BY name')
    products = cursor.fetchall()
    conn.close()
    
    products_list = []
    for product in products:
        products_list.append({
            'id': product[0],
            'code': product[1],
            'name': product[2],
            'sale_price': float(product[3]),
            'stock': product[4],
            'iva_rate': float(product[5])
        })
    
    return jsonify(products_list)

@app.route('/api/products/<code>')
def api_get_product(code):
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, name, sale_price, stock, iva_rate FROM products WHERE code = ? AND is_active = 1', (code,))
    product = cursor.fetchone()
    conn.close()
    
    if product:
        return jsonify({
            'id': product[0],
            'code': product[1],
            'name': product[2],
            'sale_price': float(product[3]),
            'stock': product[4],
            'iva_rate': float(product[5])
        })
    return jsonify({'error': 'Produto não encontrado'}), 404

@app.route('/api/customers')
def api_customers():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, name, phone, customer_card, discount_rate, total_purchases FROM customers WHERE is_active = 1 ORDER BY name')
    customers = cursor.fetchall()
    conn.close()
    
    customers_list = []
    for customer in customers:
        customers_list.append({
            'id': customer[0],
            'code': customer[1],
            'name': customer[2],
            'phone': customer[3],
            'customer_card': customer[4],
            'discount_rate': float(customer[5]),
            'total_purchases': float(customer[6])
        })
    
    return jsonify(customers_list)

@app.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    try:
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Produto eliminado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/delete_customer/<int:customer_id>', methods=['DELETE'])
def api_delete_customer(customer_id):
    try:
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE customers SET is_active = 0 WHERE id = ?', (customer_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Cliente eliminado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/sales', methods=['POST'])
def api_create_sale():
    try:
        data = request.json
        user_id = session['user_id']
        
        sale_number = f"V{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        
        conn = sqlite3.connect('sistema_vendas.db')
        cursor = conn.cursor()
        
        # Inserir venda com os novos campos (valor_pago e troco)
        cursor.execute('''
            INSERT INTO sales (sale_number, customer_id, user_id, subtotal, discount_amount, iva_amount, total, payment_method, valor_pago, troco)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sale_number, 
            data.get('customer_id'), 
            user_id, 
            data['subtotal'], 
            data['discount_amount'], 
            data['iva_amount'], 
            data['total'], 
            data['payment_method'],
            data.get('valor_pago', 0),  # Novo campo
            data.get('troco', 0)        # Novo campo
        ))
        
        sale_id = cursor.lastrowid
        
        for item in data['items']:
            cursor.execute('''
                INSERT INTO sale_items (sale_id, product_id, product_code, product_name, quantity, unit_price, iva_rate, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sale_id, item['product_id'], item['code'], item['name'], item['quantity'], item['unit_price'], item['iva_rate'], item['line_total']))
            
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['product_id']))
        
        if data.get('customer_id'):
            cursor.execute('UPDATE customers SET total_purchases = total_purchases + ?, last_purchase_date = CURRENT_TIMESTAMP WHERE id = ?', 
                         (data['total'], data['customer_id']))
        
        conn.commit()
        conn.close()
        
        mensagem = f'Venda {sale_number} registrada com sucesso! Total: {data["total"]:.2f} €'
        if data['payment_method'] == 'Dinheiro' and data.get('troco', 0) > 0:
            mensagem += f'\nTroco: {data["troco"]:.2f} €'
        
        return jsonify({
            'success': True, 
            'sale_number': sale_number,
            'message': mensagem
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

@app.route('/api/sales')
def api_get_sales():
    conn = sqlite3.connect('sistema_vendas.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.sale_number, s.total, s.payment_method, s.created_at, u.full_name, c.name
        FROM sales s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN customers c ON s.customer_id = c.id
        ORDER BY s.created_at DESC
        LIMIT 50
    ''')
    sales_data = cursor.fetchall()
    conn.close()
    
    sales_list = []
    for sale in sales_data:
        sales_list.append({
            'sale_number': sale[0],
            'total': float(sale[1]),
            'payment_method': sale[2],
            'created_at': sale[3],
            'cashier': sale[4],
            'customer': sale[5] or 'Anónimo'
        })
    
    return jsonify(sales_list)

# ========== ROTAS PARA RELATÓRIOS SIMPLES ==========
@app.route('/reports')
def reports_route():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Relatórios de Vendas</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; background: #f5f5f5; }
            .header { background: white; padding: 15px 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .nav-menu { background: #343a40; }
            .nav-menu ul { list-style: none; display: flex; margin: 0; padding: 0; }
            .nav-menu li a { color: white; text-decoration: none; padding: 15px 20px; display: block; }
            .nav-menu li a:hover { background: #495057; }
            .nav-menu li a.active { background: #007bff; }
            .container { padding: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #343a40; color: white; }
            tr:hover { background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Relatórios de Vendas</h1>
            <div>Bem-vindo, ''' + session.get('full_name', 'Usuário') + ''' | <a href="/logout" style="color: #dc3545; text-decoration: none;">Sair</a></div>
        </div>

        <nav class="nav-menu">
            <ul>
                <li><a href="/pos">📦 Vendas</a></li>
                <li><a href="/products">📋 Produtos</a></li>
                <li><a href="/customers">👥 Clientes</a></li>
                <li><a href="/reports" class="active">📊 Relatórios</a></li>
                <li><a href="/advanced_reports">📈 Avançados</a></li>
                <li><a href="/printer_settings">🖨️ Impressora</a></li>
                <li><a href="/system_settings">⚙️ Sistema</a></li>
            </ul>
        </nav>

        <div class="container">
            <div class="card">
                <h3>Últimas Vendas</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Nº Venda</th>
                            <th>Cliente</th>
                            <th>Operador</th>
                            <th>Total</th>
                            <th>Pagamento</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody id="salesTable">
                        <!-- Vendas carregadas via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function loadSales() {
                try {
                    const response = await fetch('/api/sales');
                    const sales = await response.json();
                    displaySales(sales);
                } catch (error) {
                    console.error('Erro ao carregar vendas:', error);
                }
            }

            function displaySales(sales) {
                const tbody = document.getElementById('salesTable');
                tbody.innerHTML = '';

                sales.forEach(sale => {
                    const row = document.createElement('tr');
                    const date = new Date(sale.created_at).toLocaleString('pt-PT');
                    
                    row.innerHTML = `
                        <td>${sale.sale_number}</td>
                        <td>${sale.customer}</td>
                        <td>${sale.cashier}</td>
                        <td>${sale.total.toFixed(2)} €</td>
                        <td>${sale.payment_method}</td>
                        <td>${date}</td>
                    `;
                    tbody.appendChild(row);
                });
            }

            document.addEventListener('DOMContentLoaded', loadSales);
        </script>
    </body>
    </html>
    ''')
    # ========== APIs PARA BACKUP ==========
@app.route('/api/create_backup', methods=['POST'])
def api_create_backup():
    try:
        # Criar cópia do banco de dados
        import shutil
        from datetime import datetime
        
        backup_filename = f"backup_sistema_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('sistema_vendas.db', backup_filename)
        
        # Salvar informação do último backup
        save_setting('last_backup', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return jsonify({
            'success': True,
            'message': f'Backup criado com sucesso: {backup_filename}',
            'filename': backup_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao criar backup: {str(e)}'}), 500

@app.route('/api/restore_backup', methods=['POST'])
def api_restore_backup():
    try:
        if 'backup_file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
        
        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
        
        # Fazer backup do banco atual antes de restaurar
        import shutil
        from datetime import datetime
        current_backup = f"backup_antes_restauracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('sistema_vendas.db', current_backup)
        
        # Salvar o arquivo de backup
        backup_file.save('sistema_vendas.db')
        
        return jsonify({
            'success': True,
            'message': 'Backup restaurado com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao restaurar backup: {str(e)}'}), 500

@app.route('/api/get_backup_info')
def api_get_backup_info():
    last_backup = get_setting('last_backup', 'Nenhum backup realizado')
    return jsonify({'last_backup': last_backup})
    # Adicione isto no final para testar
def test_receipt():
    test_data = {
        'sale_number': 'TEST001',
        'subtotal': 150.0,
        'discount_amount': 15.0,
        'iva_amount': 18.9,
        'total': 153.9,
        'payment_method': 'Cartão'
    }
    test_items = [
        {
            'name': 'Água Mineral 1L',
            'quantity': 3,
            'unit_price': 50.0,
            'iva_rate': 0.14
        }
    ]
    printer.print_receipt(test_data, test_items)

# Descomente a linha abaixo para testar
# test_receipt()

if __name__ == '__main__':
    init_db()
    init_settings_table()  # Adicione esta linha
    print("🛒 SISTEMA DE VENDAS - FASE 3 IMPLEMENTADA!")
    print("📍 Acesse: http://localhost:5000/login")
    print("👤 Usuários para teste:")
    print("   - admin / admin123 (Administrador)")
    print("   - caixa / caixa123 (Operador de Caixa)")
    print("")
    print("🚀 NOVAS FUNCIONALIDADES:")
    print("   🖨️  Sistema de impressão térmica")
    print("   📷  Leitor de código de barras")
    print("   💰  Cálculo correto de IVA por produto")
    print("   📈  Relatórios avançados com gráficos")
    print("   ✏️  Edição completa de produtos e clientes")
    print("   💾  Sistema de configurações persistente")
    print("   🔄  Sistema de backup e restauração")
    print("")
    print("📋 Para usar a impressora:")
    print("   1. pip install escpos")
    print("   2. Configure em: http://localhost:5000/printer_settings")
    app.run(debug=True, host='0.0.0.0', port=5000)