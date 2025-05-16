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
nlp_hf = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", aggregation_strategy="simple")
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


def agrupar_entidades_similares(entities, umbral=40):
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
        if etiqueta in ("LOC", "PERSON") and conteo == 1:
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
    aggregation_strategy="simple",
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

#def entidad_existe_por_texto(entidad, entidades):
#    """Verifica si la entidad con texto ya existe (sin importar categoría)."""
#    entidad_clean = limpiar_texto(entidad)
#    return any(limpiar_texto(ent) == entidad_clean for ent, _ in entidades)

#def agregar_entidades_validando_texto(entidades_actuales, nuevas_entidades):
#    """
#    Agrega nuevas entidades a entidades_actuales validando solo el texto para evitar duplicados.
#    
#    Args:
#        entidades_actuales (list): Lista existente de (entidad, categoria).
#        nuevas_entidades (list): Lista nueva de (entidad, categoria).
#        
#    Returns:
#        list: Lista actualizada con entidades nuevas no duplicadas (según texto).
#    """
#    for ent, cat in nuevas_entidades:
#        if not entidad_existe_por_texto(ent, entidades_actuales):
#            # Si NO existe el texto, la agregamos
#            entidades_actuales.append((ent, cat))
#    return entidades_actuales


def extract_entities(text):
    """
    Extrae entidades con Hugging Face NER pipeline.
    Retorna lista de tuplas (texto_entidad, etiqueta).
    """
    entities = []
    mapa_etiquetas = {"PER": "PERSON", "LOC": "LOC", "ORG": "ORG", "GPE": "LOC"}
    resultados = ner_pipeline(text.strip())
    for ent in resultados:
        etiqueta = mapa_etiquetas.get(ent['entity_group'], ent['entity_group'])
        if etiqueta in ["PERSON","GPE", "LOC"]:
            texto_limpio = limpiar_texto(ent['word'])
            if len(texto_limpio) >= 2:  # Solo agregar si tiene 2 o más caracteres
                entities.append((texto_limpio, etiqueta))
    #print("ENTIDADES BETO")
    #print(text.strip())
    #print(entities)
    #print("-----")

    entities_new = []
    #print(text)
    #ner_results = nlp_hf(text.strip())    
    #for ent in ner_results:
    #    etiqueta = mapa_etiquetas.get(ent['entity_group'], ent['entity_group'])
    #    if etiqueta in ["PERSON","GPE", "LOC"]:
    #        print(ent['word'])
    #        texto_limpio = limpiar_texto(ent['word'])
    #        if len(texto_limpio) >= 2:  # Solo agregar si tiene 2 o más caracteres
    #            print('----')
    #            print(texto_limpio)
    #            print('----')
    #            entities.append((texto_limpio, etiqueta))
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





