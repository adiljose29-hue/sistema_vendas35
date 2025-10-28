import sqlite3
from datetime import datetime
import random

class SalesModule:
    def __init__(self, db_path='sistema_vendas.db'):
        self.db_path = db_path
    
    def generate_sale_number(self):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_num = random.randint(1000, 9999)
        return f"V{timestamp}{random_num}"
    
    def create_sale(self, sale_data, items):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Criar venda
            sale_number = self.generate_sale_number()
            cursor.execute('''
                INSERT INTO sales (sale_number, customer_id, user_id, subtotal, 
                                 iva_amount, discount_amount, total, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sale_number, sale_data.get('customer_id'), sale_data['user_id'],
                sale_data['subtotal'], sale_data['iva_amount'],
                sale_data['discount_amount'], sale_data['total'],
                sale_data['payment_method']
            ))
            
            sale_id = cursor.lastrowid
            
            # Adicionar itens
            for item in items:
                cursor.execute('''
                    INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, iva_rate, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    sale_id, item['product_id'], item['quantity'],
                    item['unit_price'], item['iva_rate'], item['line_total']
                ))
                
                # Atualizar estoque
                cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', 
                             (item['quantity'], item['product_id']))
            
            conn.commit()
            return sale_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def void_sale_line(self, sale_item_id, user_id, reason):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Obter dados do item para restaurar estoque
            cursor.execute('SELECT product_id, quantity FROM sale_items WHERE id = ?', (sale_item_id,))
            item = cursor.fetchone()
            
            if item:
                # Restaurar estoque
                cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', 
                             (item[1], item[0]))
                
                # Anular linha
                cursor.execute('''
                    UPDATE sale_items SET is_voided = 1, voided_by = ?, void_reason = ?
                    WHERE id = ?
                ''', (user_id, reason, sale_item_id))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_sale_by_number(self, sale_number):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, u.full_name as cashier_name, c.name as customer_name
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.id
            LEFT JOIN customers c ON s.customer_id = c.id
            WHERE s.sale_number = ?
        ''', (sale_number,))
        
        sale = cursor.fetchone()
        conn.close()
        return sale
    
    def get_sale_items(self, sale_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT si.*, p.name as product_name, p.code as product_code
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        ''', (sale_id,))
        
        items = cursor.fetchall()
        conn.close()
        return items