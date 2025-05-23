import unicodedata
import re
from urllib.parse import unquote


def normalize_entity(texto):
    diccionario = {
        "Ronald Mcdonal": "Pennywise",
        "Payaso": "Pennywise",
        "Eso": "Pennywise",
        "Bozo": "Pennywise",
        "Clarabell": "Pennywise",
        "IT": "Pennywise",
        "El Tartaja": "Denbrough",
        "Billestaba": "Bill",
        "William Carlos Williams": "",  
        "Georgie": "George",
        "GGeorgie": "George",
        "ben": "Ben",
        "Bev": "Beverly", 
        "Eds": "Eddie",
        "Invierno": "Enero",
        "Otoño": "Octubre",
        "Primavera": "Abril",
        "Verano": "Julio",
        "Turtle": "Tortuga",
        "John Wayne": "",
        "Chet Huthley": "",
        "Bruce Springsteen": "",
        "Judas Priest": "",
        "Kiss": "",
        "Def Leppard": "",
        "derry": "Derry",
        "Dwight Eisenhower": "", 
        "Richard Nixon": "",
        "Ronald Reagan": "",
        "George Bush": "",
    }
    patrones = map(re.escape, diccionario.keys())
    patron_regex = r'\b(' + '|'.join(patrones) + r')\b'

    def reemplazo(match):
        palabra = match.group(0)
        # Buscar en diccionario ignorando mayúsculas
        for clave, valor in diccionario.items():
            if palabra.lower() == clave.lower():
                return valor
        return palabra

    texto_modificado = re.sub(patron_regex, reemplazo, texto, flags=re.IGNORECASE)
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

def limpiar_texto(texto: str) -> str:
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
    # Reemplaza cualquier carácter que no sea una letra, número o guion bajo por un guion bajo
    texto = re.sub(r'[^\w]', ' ', texto, flags=re.UNICODE)    
    #texto = unquote(texto)
    texto = texto.strip(" ")
    return texto