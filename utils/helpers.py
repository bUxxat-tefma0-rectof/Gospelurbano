# utils/helpers.py
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd

def format_currency(value: float) -> str:
    """
    Formatar valor para moeda brasileira
    
    Args:
        value: Valor float
        
    Returns:
        String formatada
    """
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(date: datetime, format: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formatar data
    
    Args:
        date: Objeto datetime
        format: Formato desejado
        
    Returns:
        String formatada
    """
    if date:
        return date.strftime(format)
    return "N/A"

def generate_pdf_report(title: str, data: List[Dict], columns: List[str]) -> BytesIO:
    """
    Gerar relatório PDF
    
    Args:
        title: Título do relatório
        data: Dados do relatório
        columns: Nomes das colunas
        
    Returns:
        BytesIO com o PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    
    # Tabela
    if data:
        table_data = [columns]
        for row in data:
            table_data.append([str(row.get(col, "")) for col in columns])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def generate_excel_report(data: List[Dict], filename: str) -> BytesIO:
    """
    Gerar relatório Excel
    
    Args:
        data: Dados do relatório
        filename: Nome do arquivo
        
    Returns:
        BytesIO com o Excel
    """
    df = pd.DataFrame(data)
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Relatório', index=False)
    
    buffer.seek(0)
    return buffer
