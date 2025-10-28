import sqlite3
from datetime import datetime
import xml.etree.ElementTree as ET

class TaxModule:
    def __init__(self, db_path='sistema_vendas.db'):
        self.db_path = db_path
    
    def generate_invoice_number(self):
        # Implementar lógica de numeração conforme AGT
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"FT{timestamp}001"
    
    def create_invoice(self, sale_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obter dados da venda
        cursor.execute('''
            SELECT s.*, c.nif, c.name, u.full_name
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.id
            JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        ''', (sale_id,))
        
        sale = cursor.fetchone()
        
        if not sale:
            return None
        
        # Gerar XML da nota fiscal
        xml_data = self.generate_invoice_xml(sale)
        
        # Inserir na tabela de notas fiscais
        invoice_number = self.generate_invoice_number()
        cursor.execute('''
            INSERT INTO invoices (invoice_number, sale_id, customer_nif, customer_name, 
                                total_amount, iva_amount, xml_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (invoice_number, sale_id, sale[12], sale[13], sale[6], sale[5], xml_data))
        
        invoice_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return invoice_id
    
    def generate_invoice_xml(self, sale_data):
        # Implementar geração de XML conforme normas AGT Angola
        root = ET.Element("Invoice")
        ET.SubElement(root, "InvoiceNumber").text = self.generate_invoice_number()
        ET.SubElement(root, "IssueDate").text = datetime.now().isoformat()
        ET.SubElement(root, "TotalAmount").text = str(sale_data[6])
        ET.SubElement(root, "TaxAmount").text = str(sale_data[5])
        
        return ET.tostring(root, encoding='unicode')
    
    def generate_saft_file(self, start_date, end_date):
        # Implementar geração de ficheiro SAFT (Standard Audit File for Tax)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM invoices 
            WHERE issue_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        
        invoices = cursor.fetchall()
        conn.close()
        
        # Gerar XML SAFT conforme normas AGT
        saft_root = ET.Element("AuditFile")
        header = ET.SubElement(saft_root, "Header")
        ET.SubElement(header, "AuditFileVersion").text = "1.04_01"
        ET.SubElement(header, "CompanyID").text = "123456789"  # NIF da empresa
        
        return ET.tostring(saft_root, encoding='unicode')