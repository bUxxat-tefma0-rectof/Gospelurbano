# utils/helpers.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from io import BytesIO

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

def generate_csv_report(data: List[Dict], columns: List[str]) -> BytesIO:
    """
    Gerar relatório CSV (substitui PDF/Excel)
    
    Args:
        data: Dados do relatório
        columns: Nomes das colunas
        
    Returns:
        BytesIO com o CSV
    """
    import csv
    
    buffer = BytesIO()
    # Usar StringIO para escrever texto e depois codificar
    text_buffer = []
    
    # Cabeçalho
    text_buffer.append(",".join(columns))
    
    # Dados
    for row in data:
        text_buffer.append(",".join([str(row.get(col, "")) for col in columns]))
    
    # Escrever no buffer
    content = "\n".join(text_buffer)
    buffer.write(content.encode('utf-8-sig'))
    buffer.seek(0)
    
    return buffer

def generate_text_report(title: str, data: List[Dict], columns: List[str]) -> str:
    """
    Gerar relatório em texto formatado
    
    Args:
        title: Título do relatório
        data: Dados do relatório
        columns: Nomes das colunas
        
    Returns:
        String formatada
    """
    report = f"*{title}*\n"
    report += f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
    if data:
        for row in data:
            for col in columns:
                value = row.get(col, "N/A")
                report += f"• *{col}*: {value}\n"
            report += "\n"
    
    return report
