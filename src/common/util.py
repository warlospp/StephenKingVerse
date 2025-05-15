import unicodedata
import re
from urllib.parse import unquote


def normalize_entity(texto):
    diccionario = {
    'Ronald Mcdonal': 'Pennywise',
    'Payaso': 'Pennywise',
    'payaso': 'Pennywise',
    'Eso': 'Pennywise',
    'Bozo': 'Pennywise',
    'Clarabell': 'Pennywise',
    'IT': 'Pennywise',
    'It': 'Pennywise',
    'it': 'Pennywise',
    'el Tartaja': '',
    'El Tartaja': '',
    'William Carlos Williams': '',  
    'Georgie': 'George',
    'Denbrough':'',
    'ben': 'Ben',
    'Bev': 'Beverly', 
    'Eds': 'Eddie',
    "invierno": "enero",
    "otoño": "octubre",
    "primavera": "abril",
    "verano": "Julio",
    "Invierno": "Enero",
    "Otoño": "Octubre",
    "Primavera": "Abril",
    "Verano": "Julio",
    "Turtle": "Tortuga",
    "turtle": "Tortuga",
    "tortuga": "Tortuga",
    "John Wayne": "",
    "Chet Huthley": "",
    "Bruce Springsteen": "",
    "Judas Priest": "",
    "Kiss": "",
    "Def Leppard": "",
    }
    # Escapar claves para usarlas en regex
    patrones = map(re.escape, diccionario.keys())
    # Crear patrón que busca cualquiera de las palabras completas
    patron_regex = r'\b(' + '|'.join(patrones) + r')\b'

    # Función para reemplazo según diccionario
    def reemplazo(match):
        palabra = match.group(0)
        return diccionario.get(palabra, palabra)

    # Reemplazar todas las coincidencias
    texto_modificado = re.sub(patron_regex, reemplazo, texto)
    return texto_modificado


def normalizar_fecha(texto):
    # Buscar año (1900-2099)
    match_anio = re.search(r"(19|20)\d{2}", texto)
    if match_anio:
        texto = match_anio.group(0)

    # Lista de meses en español
    meses = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    for mes in meses:
        if mes in texto.lower():
            return mes  # Retorna mes si se encuentra

    # Estaciones y su mes representativo (hemisferio norte)
    estaciones_meses = {
    "invierno": "enero",
    "otoño": "octubre",
    "primavera": "abril",
    "verano": "julio"
    }
    for estacion, mes_repr in estaciones_meses.items():
        if estacion in texto.lower():
            return mes_repr  # Retorna mes representativo si se encuentra estación

    # Si no se encontró nada, retorna el texto original o un valor por defecto
    return texto

def normalizar_texto(texto):
    texto = ''.join(
    c for c in unicodedata.normalize('NFD', texto)
    if unicodedata.category(c) != 'Mn'
    )
    texto = texto.lower().strip()
    return texto

def limpiar_uri(texto):
    """
    Normaliza texto para crear URIs válidas:
    - Decodifica caracteres URL (%20, etc)
    - Elimina tildes y caracteres diacríticos
    - Reemplaza espacios por guiones bajos
    - Pasa a minúsculas
    """
    # Decodificar URL encoded (%20 -> espacio)
    texto = unquote(texto)

    # Eliminar tildes y diacríticos
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

    # Reemplazar uno o más espacios por un guion bajo
    texto = re.sub(r'\s+', '_', texto)

    return texto

def limpiar_texto(name: str) -> str:
    """
    Limpia y codifica un nombre de entidad para que sea URI-safe.
    - Normaliza caracteres Unicode a ASCII.
    - Elimina caracteres especiales problemáticos.
    - Reemplaza espacios por guiones bajos.
    - Codifica caracteres especiales restantes para URI.

    Args:
    name (str): Nombre original de la entidad.

    Returns:
    str: Nombre limpio y codificado para URI.
    """

    # Elimina acentos y caracteres especiales del alfabeto (ej. ñ → n, á → a)
    name = name.replace('\n', ' ').replace('\r', ' ')    
    # Reemplaza cualquier carácter que no sea una letra, número o guion bajo por un guion bajo
    name = re.sub(r'[^\w]', ' ', name, flags=re.UNICODE)    
    # Reemplaza múltiples espacios en blanco consecutivos por un solo guion bajo
    name = re.sub(r'\s+', ' ', name)    
    # Reemplaza ciertos caracteres especiales comunes (_ - \ " ' `) por guiones bajos
    name = name.replace(' ', ' ')    
    # Codifica la cadena en formato URL, manteniendo los guiones bajos sin modificar
    #name = urllib.parse.quote(name, safe=' ')    
    # Elimina guiones bajos al inicio y al final de la cadena
    name = name.strip(" ")
    return name