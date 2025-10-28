import sqlite3

class ProductsModule:
    def __init__(self, db_path='sistema_vendas.db'):
        self.db_path = db_path
    
    def create_product(self, product_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (code, barcode, name, description, purchase_price, 
                                sale_price, stock, min_stock, iva_rate, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_data['code'], product_data['barcode'], product_data['name'],
            product_data['description'], product_data['purchase_price'],
            product_data['sale_price'], product_data['stock'],
            product_data['min_stock'], product_data['iva_rate'],
            product_data['category']
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product_id
    
    def get_product_by_code(self, code):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE code = ? AND is_active = 1', (code,))
        product = cursor.fetchone()
        conn.close()
        
        return product
    
    def get_product_by_barcode(self, barcode):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE barcode = ? AND is_active = 1', (barcode,))
        product = cursor.fetchone()
        conn.close()
        
        return product
    
    def update_stock(self, product_id, quantity):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
        conn.commit()
        conn.close()
    
    def get_low_stock_products(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE stock <= min_stock AND is_active = 1')
        products = cursor.fetchall()
        conn.close()
        
        return products