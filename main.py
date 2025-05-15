from src.extraction.extract_text import extract_text_from_pdf
from src.nlp.keyphrase_extraction import extraer_keyphrases_keybert_potente_con_scores
from src.nlp.entity_recognition import extract_entities,agrupar_entidades_similares
from collections import defaultdict
from src.ontology.ontology_builder import extract_relationships,generate_ontology
from src.ontology.neo4j_service import insert_ontology
from src.graph.graph_builder import build_graph, draw_graph

def save_text(text, filepath):
    """
    Guarda el texto extraído del PDF en un archivo.
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Texto guardado en {filepath}")
    except Exception as e:
        print(f"Error al guardar el texto: {e}")

def load_text_from_file(filepath):
    """
    Lee el texto desde un archivo.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return text
    except Exception as e:
        print(f"Error al leer el archivo {filepath}: {e}")
        return ""

#def calcular_corte(texto, chunk_size):
#    inicio = 0
#    longitud = len(texto)
#    while inicio < longitud:
#        if inicio + chunk_size >= longitud:
#            yield texto[inicio:].strip()
#            break

#        corte_pos = texto.find('.', inicio + chunk_size)
#        if corte_pos == -1:
#            yield texto[inicio:].strip()
#            break

#        corte_pos += 1
#        fragmento = texto[inicio:corte_pos].strip()
#        yield fragmento
#        inicio = corte_pos

def process_text_in_parts(text, output_text_Keyphrase_path, chunk_size=1000):    
    """
    Procesa el texto por partes, extrayendo entidades y relaciones de cada parte.
    """
    # Inicializa una lista vacía para acumular frases clave
    frases_acumuladas = [] 
    # Dividir el texto en partes de tamaño definido
    for i in range(0, len(text), chunk_size):
    #for fragmento in calcular_corte(text, chunk_size):
        fragmento = text[i:i+chunk_size]        
        resultados = extraer_keyphrases_keybert_potente_con_scores(fragmento, max_phrases=5 , max_words=7)
        # Extraer solo las frases (sin puntuación) y acumularlas
        frases_acumuladas.extend([frase for frase in resultados])
    # Opcional: eliminar duplicados manteniendo orden
    frases_unicas = list(dict.fromkeys(frases_acumuladas))
    # Convertir la lista en un texto con saltos de línea
    texto_final = "\n".join(frases_unicas)    
    ## Guardar en archivo
    save_text(texto_final, output_text_Keyphrase_path)
    print(f"Se guardaron {len(frases_unicas)} frases clave en el archivo.")    
    # Leer el texto guardado en el archivo
    texto_final = load_text_from_file (output_text_Keyphrase_path)
    if not texto_final:
        raise Exception("No se pudo leer el texto del archivo.")
    
    entidades = []
    relaciones = []
    # Dividir el texto en partes de tamaño definido

    #for fragmento in calcular_corte(texto_final, chunk_size):
    for i in range(0, len(texto_final), chunk_size):
        fragmento = text[i:i+chunk_size]   
        # Extraer entidades de este fragmento
        fragmento_entidades = extract_entities(fragmento)
        entidades.extend(fragmento_entidades)        
        # Extraer relaciones de este fragmento
        fragmento_relaciones = extract_relationships(fragmento, fragmento_entidades)
        relaciones.extend(fragmento_relaciones)


    return entidades, relaciones


def show_entities(entidades):
    """
    Muestra todas las entidades extraídas y un resumen agrupado por tipo.

    Args:
        entidades (list of tuples): Lista de tuplas (texto_entidad, tipo_entidad).
    """
    print("Entidades encontradas:")
    for texto, etiqueta in entidades:
        print(f"- {texto} ({etiqueta})")

    # Agrupar entidades por tipo
    agrupadas = defaultdict(set)
    for texto, etiqueta in entidades:
        agrupadas[etiqueta].add(texto)

    print("\nResumen por tipo de entidad:")
    #for etiqueta, textos in agrupadas.items():
    print(f"{etiqueta} ({len(texto)}): {', '.join(texto)}")

def save_ontology_to_file(serialized_ontology, filepath, format="turtle"):
    """
    Guarda la ontología serializada (string) en un archivo.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(serialized_ontology)
    print(f"Ontología guardada en {filepath}")

def process_pdf_and_generate_ontology(pdf_path, output_text_path, output_text_Keyphrase_path, ontology_path, neo4j_url, user, password):
    try:
        # Extraer texto del PDF
        texto = extract_text_from_pdf(pdf_path, 2)
        # Guardar texto
        save_text(texto, output_text_path)
        # Leer el texto guardado en el archivo
        texto_leido = load_text_from_file(output_text_path)    
        if not texto_leido:
            raise Exception("No se pudo leer el texto del archivo.")

        # Procesar el texto por partes, obteniendo frases clave, entidades y relaciones
        entidades, relaciones = process_text_in_parts(texto_leido, output_text_Keyphrase_path, 4000)
        
        # Mostrar algunas entidades encontradas
        #show_entities(entidades)
        #print(relaciones)


        # Agrupar entidades similares
        entities_agrupadas = agrupar_entidades_similares(entidades)
        print("AGRUPADO")
        print(entities_agrupadas)

        # Generar ontología con entidades y relaciones
        ontologia = generate_ontology([(e[0], e[1]) for e in entities_agrupadas], relaciones)
        #print(ontologia)
        save_ontology_to_file(ontologia, ontology_path)
        turtle_data = ontologia
        if isinstance(turtle_data, bytes):
            turtle_data = turtle_data.decode("utf-8")
        insert_ontology(neo4j_url, user, password, turtle_data)

        # Construir y mostrar grafo
        #G = build_graph(relaciones)
        #draw_graph(G)
    except Exception as e:
        print(f"Error en el procesamiento del PDF: {e}")

def main():
    # Definir las rutas y parámetros de entrada
    pdf_path = "data/raw/It.pdf"
    output_text_path = "data/processed/It.txt"
    output_text_Keyphrase_path = "data/processed/It_kp.txt"
    ontology_path = "data/processed/ontology.ttl"
    neo4j_url = "bolt://localhost:7687"
    user = "neo4j"
    password = "Admin.123"

    # Procesar PDF y generar ontología
    process_pdf_and_generate_ontology(pdf_path, output_text_path, output_text_Keyphrase_path, ontology_path, neo4j_url, user, password)





    #print("en_core_web_trf")
    #nlp = spacy.load("en_core_web_trf")
    #doc = nlp("cosas.")
    #for token in doc:
    #    print(f"Token: {token.text}, Lema: {token.lemma_}, POS: {token.pos_}")

    #print("es_core_news_sm")
    #nlp = spacy.load("es_core_news_sm")
    #doc = nlp("cosas.")
    #for token in doc:
    #    print(f"Token: {token.text}, Lema: {token.lemma_}, POS: {token.pos_}")

if __name__ == "__main__":
    main()