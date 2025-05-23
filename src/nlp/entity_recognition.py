import spacy
from collections import Counter
from src.common.util import normalizar_fecha,limpiar_texto
from spacy.tokens import Token
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification, pipeline
from sklearn.cluster import KMeans
import numpy as np
from collections import Counter
from rapidfuzz import fuzz



# Inicializar pipeline de NER con modelo preentrenado
nlp_hf = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", aggregation_strategy="first", device=-1)  # Cambia a -1 si no tienes GPU
# Cargar modelo transformer avanzado  
nlp_en_core_web_trf = spacy.load("en_core_web_trf")  
nlp_es_core_news_sm= spacy.load("es_core_news_sm") #

# Diccionario para mapear etiquetas spaCy a categorías propias
ETIQUETA_MAPA = {
    "PERSON": "Personaje",
    "GPE": "Lugar",
    "LOC": "Lugar",
    "ORG": "Organización",
    "DATE": "Fecha",
    "EVENT": "Evento",
    "MISC": "Misceláneo"
}


def agrupar_entidades_similares(entities, umbral=25):
    """
    Agrupa entidades similares basándose en la similitud difusa de sus nombres.

    Args:
        entities (list): Lista de tuplas (nombre_entidad, etiqueta).
        umbral (int): Porcentaje mínimo de similitud para agrupar (0-100).

    Returns:
        list: Lista de tuplas (entidad_representante, etiqueta, conteo) donde
              entidad_representante es la entidad más corta del grupo,
              etiqueta es la etiqueta común, y conteo es el número de entidades agrupadas.
    """
    grupos = []
    for ent in entities:
        agregado = False
        for grupo in grupos:
            texto_ent_grupo, etiqueta_ent_grupo = grupo[0]
            texto_ent, etiqueta_ent = ent
            if etiqueta_ent == etiqueta_ent_grupo:
                similitud = fuzz.ratio(texto_ent, texto_ent_grupo)
                if similitud >= umbral:
                    grupo.append(ent)
                    agregado = True
                    break
        if not agregado:
            grupos.append([ent])

    # Elegir representante (la entidad más corta del grupo) y contar
    entidades_agrupadas = []
    for grupo in grupos:
        representante = min(grupo, key=lambda x: len(x[0]))[0]
        etiqueta = grupo[0][1]
        conteo = len(grupo)
        entidades_agrupadas.append((representante, etiqueta, conteo))
    # Filtrar: excluir LOC y PERSON con conteo 1
    entidades_filtradas = []
    for entidad, etiqueta, conteo in entidades_agrupadas:
        if conteo <= 1:
            continue  # Excluir
        entidades_filtradas.append((entidad, etiqueta))

    return entidades_filtradas


# Cargar tokenizer y modelo fine-tuned BETO para NER
model_name = "ifis/BETO-finetuned-ner-3"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

# Crear pipeline de NER con agregación simple para obtener entidades completas
ner_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="first",
    device=-1  # Cambia a -1 si no tienes GPU
)

def cluster_entidades_por_frecuencia(entidades, n_clusters=3):
    """
    Agrupa entidades en clusters según su frecuencia de aparición.
    
    Args:
        entidades (list): Lista de entidades (ej: ["Entity1", "Entity2", ...]).
        n_clusters (int): Número de grupos a crear (ej: alto, medio, bajo).
        
    Returns:
        dict: Diccionario con {cluster_id: lista_de_entidades}.
    """
    # Contar frecuencias
    contador = Counter(entidades)
    entidades_unicas = list(contador.keys())
    frecuencias = np.array([contador[e] for e in entidades_unicas]).reshape(-1, 1)
    
    # Clustering por frecuencia
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(frecuencias)
    
    # Agrupar entidades por cluster
    grupos = {}
    for idx, cluster_id in enumerate(clusters):
        if cluster_id not in grupos:
            grupos[cluster_id] = []
        grupos[cluster_id].append((entidades_unicas[idx], contador[entidades_unicas[idx]]))
    
    # Ordenar clusters por frecuencia promedio (de mayor a menor)
    grupos_ordenados = {
        k: sorted(v, key=lambda x: x[1], reverse=True)
        for k, v in sorted(grupos.items(), key=lambda x: -np.mean([freq for _, freq in x[1]]))
    }
    
    return grupos_ordenados

def cluster_entidades_por_categoria_y_frecuencia(entities, n_clusters=3):
    """
    Agrupa entidades similares basándose en la frecuencia de aparición y categoría.
    
    Args:
        entities (list of tuples): Lista de (nombre_entidad, categoria).
        n_clusters (int): Número de clusters para agrupar por frecuencia.
        
    Returns:
        dict: { categoria: { cluster_id: [(entidad, frecuencia), ...] } }
    """
    # Contar frecuencias por entidad con categoría
    contador = Counter(entities)  # cuenta (nombre, categoria) como clave
    
    # Organizar entidades por categoría
    categorias = {}
    for (nombre, categoria), freq in contador.items():
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append((nombre, freq))
    
    resultado = {}
    for categoria, lista_entidades in categorias.items():
        # Extraer frecuencias para clustering
        frecuencias = np.array([freq for _, freq in lista_entidades]).reshape(-1, 1)
        
        # Si hay menos entidades que clusters, ajustar n_clusters
        n_clus = min(n_clusters, len(lista_entidades))
        if n_clus == 0:
            continue
        
        kmeans = KMeans(n_clusters=n_clus, random_state=42)
        clusters = kmeans.fit_predict(frecuencias)
        
        # Agrupar entidades por cluster
        grupos = {}
        for idx, cluster_id in enumerate(clusters):
            if cluster_id not in grupos:
                grupos[cluster_id] = []
            grupos[cluster_id].append(lista_entidades[idx])
        
        # Ordenar clusters por frecuencia promedio descendente
        grupos_ordenados = dict(sorted(
            grupos.items(),
            key=lambda x: -np.mean([freq for _, freq in x[1]])
        ))
        
        resultado[categoria] = grupos_ordenados
    
    return resultado



def procesar_entidades_con_excepcion(entidades, num_entidades=2, umbral_score=0.9, excepcion="Pennywise"):
    """
    Procesa el arreglo de entidades en tres pasos:
    1) Elimina entidades cortadas (con '##') y sus num_entidades antes y después.
    2) Elimina entidades con score menor al umbral, excepto la excepción.
    3) Retorna el arreglo filtrado.

    Args:
        entidades (list): Lista de dicts con keys 'word', 'score', etc.
        num_entidades (int): Cantidad de entidades antes y después a eliminar.
        umbral_score (float): Score mínimo para conservar una entidad.
        excepcion (str): Palabra que no debe eliminarse.

    Returns:
        list: Arreglo filtrado de entidades.
    """
    total = len(entidades)
    indices_a_eliminar = set()

    # Paso 1: Eliminar entidades cortadas y sus alrededores
    for i, ent in enumerate(entidades):
        if '##' in ent['word']:
            inicio = max(0, i - num_entidades)
            fin = min(total - 1, i + num_entidades)
            for idx in range(inicio, fin + 1):
                indices_a_eliminar.add(idx)

    # Construir arreglo temporal sin las entidades eliminadas en paso 1
    entidades_paso1 = [ent for idx, ent in enumerate(entidades) if idx not in indices_a_eliminar]

    # Paso 2: Eliminar entidades con score menor al umbral, excepto la excepción
    entidades_filtradas = []
    for ent in entidades_paso1:
        if ent['word'] == excepcion:
            entidades_filtradas.append(ent)
        elif ent.get('score', 0) >= umbral_score:
            entidades_filtradas.append(ent)
        # Si no cumple, se elimina

    return entidades_filtradas



def extract_entities(text):
    """
    Extrae entidades con Hugging Face NER pipeline.
    Retorna lista de tuplas (texto_entidad, etiqueta).
    """
    #print(text)
    entities = []
    mapa_etiquetas = {"PER": "PERSON", "LOC": "LOC", "ORG": "ORG", "GPE": "LOC"}
    
    resultados = ner_pipeline(text.strip())
    resultados = procesar_entidades_con_excepcion(resultados)
    for ent in resultados:
        etiqueta = mapa_etiquetas.get(ent['entity_group'], ent['entity_group'])
        if etiqueta in ["PERSON","GPE", "LOC"]:
            #print(ent['word'])
            texto_limpio = limpiar_texto(ent['word'])
            if len(texto_limpio) >= 2:  # Solo agregar si tiene 2 o más caracteres
                entities.append((texto_limpio, etiqueta))
    #print("ENTIDADES BETO")
    #print(text.strip())
    #print(entities)
    #print("-----")

    entities_new = []
    #print(text)
    ner_results = nlp_hf(text.strip())  
    ner_results = procesar_entidades_con_excepcion(ner_results)  
    for ent in ner_results:
        etiqueta = mapa_etiquetas.get(ent['entity_group'], ent['entity_group'])
        if etiqueta in ["PERSON","GPE", "LOC"]:
            #print(ent['word'])
            #texto_limpio = ent['word']
            texto_limpio = limpiar_texto(ent['word'])
            if len(texto_limpio) >= 2:  # Solo agregar si tiene 2 o más caracteres
                entities.append((texto_limpio, etiqueta))
    #print("ENTIDADES HUGGING FACE")
    #print(ner_results)

    """
    Extrae entidades del texto usando spaCy transformer, dividiendo el texto en fragmentos,
    y clasifica las entidades según categorías definidas, excluyendo entidades que
    no contengan sustantivos o nombres propios (filtra conjugaciones verbales).
    """
    #entities_new = []
    doc = nlp_en_core_web_trf(text.strip())
    for ent in doc.ents:
        # Filtrar solo etiquetas relevantes
        #if ent.label_ in ["PERSON", "GPE", "ORG", "LOC", "DATE", "EVENT", "MISC"]:
        if ent.label_ in ["DATE"]:
            ent_text = limpiar_texto(ent.text)
            ent_text = normalizar_fecha(ent_text)  
            ent_label_ = ent.label_
            entities.append((ent_text, ent_label_))
    #print("ENTIDADES SPACY nlp_en_core_web_trf")
    #print([(ent.text, ent.label_) for ent in doc.ents if ent.label_ == "DATE"])

    doc = nlp_es_core_news_sm(text.strip())
    for ent in doc.ents:
        # Filtrar solo etiquetas relevantes
        #if ent.label_ in ["PERSON", "GPE", "ORG", "LOC", "DATE", "EVENT", "MISC"]:
        if ent.label_ in ["DATE"]:
            ent_text = limpiar_texto(ent.text)
            ent_text = normalizar_fecha(ent_text)  
            ent_label_ = ent.label_
            entities.append((ent_text, ent_label_))
    #print("ENTIDADES SPACY nlp_es_core_news_lg")
    #print([(ent.text, ent.label_) for ent in doc.ents if ent.label_ == "DATE"])





    #print("ANTES")
    #print(entities)
    
    #entidades_clasificadas = entity_normalization(entidades_agrupadas)
    #print("CLASIFICADAS")
    #print(entidades_clasificadas)

    #clusters = cluster_entidades_por_categoria_y_frecuencia(entities, n_clusters=3)
    #for categoria, grupos in clusters.items():
    #    print(f"\nCategoría: {categoria}")
    #    for cluster_id, entidades in grupos.items():
    #        print(f"  Cluster {cluster_id}:")
    #        for entidad, freq in entidades:
    #            print(f"    - {entidad}: {freq} apariciones")


    return entities





