import fitz  # PyMuPDF
from pathlib import Path
import re
import unicodedata
from src.common.util import normalize_entity



def clean_extracted_text(text: str) -> str:
    """
    Limpia y normaliza el texto extraído del PDF,
    eliminando caracteres especiales específicos en todo el texto.

    Args:
        text (str): Texto extraído sin procesar.

    Returns:
        str: Texto limpio y normalizado.
    """
    # Definir patrón para letras ASCII + letras con tilde + ñ + números + coma, punto y espacios
    # Usamos rangos Unicode para vocales acentuadas y ñ
    patron = r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ,.\s]'
    
    text = re.sub(patron, ' ', text)

    # 1. Reemplazar saltos de línea múltiples por espacio
    text = re.sub(r'\n+', ' ', text)
    
    # 2. Reemplazar múltiples puntos consecutivos por un solo punto
    text = re.sub(r'\.{2,}', ' ', text)
    
    # 3. Reemplazar múltiples comas consecutivas por una sola coma
    text = re.sub(r',{2,}', ' ', text)
    
    # 5. Eliminar letras sueltas (palabras de un solo carácter)
    text = re.sub(r'\b[a-zA-Z]\b', ' ', text)
    
    # 6. Eliminar espacios múltiples y dejar solo uno
    text = re.sub(r'\s+', ' ', text)

    # Patrón que detecta palabras repetidas consecutivas (ignorando mayúsculas/minúsculas)
    patron  = re.compile(r'\b(\w+)( \1\b)+', flags=re.IGNORECASE)    
    # Función para reemplazar las repeticiones por una sola palabra
    while True:
        nuevo_texto = patron .sub(r'\1', text)
        if nuevo_texto == text:
            break
        text = nuevo_texto
        
    # 8. Opcional: eliminar espacios al inicio y final
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    text = normalize_entity(text)

    return text.strip()

def extract_texts_from_folder(folder_path):
    texts = {}
    for pdf in Path(folder_path).glob("*.pdf"):
        texts[pdf.name] = extract_text_from_pdf(pdf)
    return texts

def extract_text_from_pdf(pdf_path, skip_pages=2):
    """
    Extrae el texto de un archivo PDF usando PyMuPDF, omitiendo las primeras páginas.
    
    Args:
    - pdf_path (str): La ruta al archivo PDF.
    - skip_pages (int): Número de páginas a omitir desde el inicio. Por defecto son 2.
    
    Returns:
    - str: El texto extraído del PDF limpio.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(skip_pages, len(doc)):
        page = doc[page_num]
        text += page.get_text()
    
    return clean_extracted_text(text)


