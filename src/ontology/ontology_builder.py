from rdflib import Graph, URIRef, Literal, RDF, Namespace
from rdflib.namespace import OWL, RDFS, FOAF
from src.common.util import limpiar_uri
from rapidfuzz import fuzz


def extract_relationships(text, entities, umbral=44):
    """
    Extrae relaciones de co-ocurrencia entre entidades en el texto.
    Usa similitud difusa para detectar presencia en párrafos.
    """
    relationships = set()
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for para in paragraphs:
        para_norm = para.lower()
        para_entities = []
        for ent_text, ent_type in entities:
            # Aquí puedes limpiar la entidad para la búsqueda si quieres
            ent_text_for_search = limpiar_uri(ent_text).replace('_', ' ').lower()
            score = fuzz.partial_ratio(ent_text_for_search, para_norm)
            if score >= umbral:
                para_entities.append(ent_text)
        # Crear relaciones entre entidades detectadas en el mismo párrafo
        for i in range(len(para_entities)):
            for j in range(i+1, len(para_entities)):
                src, tgt = sorted([para_entities[i], para_entities[j]])
                relationships.add((src, "co_ocurre_con", tgt))
    return list(relationships)


def generate_ontology(entities, relationships):
    """
    Genera un grafo RDF con clases, instancias y relaciones, usando categorías amplias y verbos adecuados.
    """
    EX = Namespace("http://stephenkingverse.org/")
    g = Graph()
    g.bind("ex", EX)
    g.bind("foaf", FOAF)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)

    verbs = ["co_ocurre_con", "trabajar_en", "ocurrir_en", "conocer"]
    relation_map = {verb: EX[verb] for verb in verbs}

    categorias = {
        "person": FOAF.Person,
        "personaje": FOAF.Person,
        "gpe": EX.lugar,
        "loc": EX.lugar,
        "lugar": EX.lugar,
        "org": EX.organizacion,
        "organizacion": EX.organizacion,
        "organización": EX.organizacion,
        "date": EX.fecha,
        "fecha": EX.fecha,
        "event": EX.evento,
        "evento": EX.evento,
        "misc": EX.miscelaneo,
        "miscelaneo": EX.miscelaneo,
        "misceláneo": EX.miscelaneo
    }

    # Normalizar tipos y crear clases RDF
    tipos_unicos = set(label.lower() for _, label in entities)
    for tipo in tipos_unicos:
        clase_uri = categorias.get(tipo, EX[limpiar_uri(tipo)])  # limpiar_uri aquí
        g.add((clase_uri, RDF.type, OWL.Class))
        g.add((clase_uri, RDFS.label, Literal(tipo.capitalize())))

    # Definir propiedad co_ocurre_con
    g.add((EX.co_ocurre_con, RDF.type, OWL.ObjectProperty))
    g.add((EX.co_ocurre_con, RDFS.label, Literal("co_ocurre_con")))

    # Crear instancias y asignar tipo
    for nombre, tipo in entities:
        nombre_uri = limpiar_uri(nombre)  # limpiar_uri aquí
        tipo_norm = tipo.lower()
        clase = categorias.get(tipo_norm, EX[limpiar_uri(tipo_norm)])  # limpiar_uri aquí
        entidad_uri = EX[nombre_uri]
        if clase == FOAF.Person:
            g.add((entidad_uri, RDF.type, FOAF.Person))
            g.add((entidad_uri, FOAF.name, Literal(nombre)))
        else:
            g.add((entidad_uri, RDF.type, clase))
            g.add((entidad_uri, EX.nombre, Literal(nombre)))

    # Verbos específicos según tipos
    verbos_por_tipo = {
        ("person", "org"): "trabajar_en",
        ("personaje", "organizacion"): "trabajar_en",
        ("personaje", "organización"): "trabajar_en",
        ("event", "loc"): "ocurrir_en",
        ("evento", "lugar"): "ocurrir_en",
        ("event", "gpe"): "ocurrir_en",
        ("person", "person"): "conocer",
        ("personaje", "personaje"): "conocer",
    }

    def verbo_adecuado(src_tipo, tgt_tipo, verbo_original):
        if verbo_original in relation_map:
            return relation_map[verbo_original]
        verbo_esperado = verbos_por_tipo.get((src_tipo, tgt_tipo))
        if verbo_esperado and verbo_esperado in relation_map:
            return relation_map[verbo_esperado]
        return EX.co_ocurre_con

    # Construir relaciones RDF
    for src, verbo, tgt in relationships:
        if src == tgt:
            continue

        src_tipo = next((label.lower() for ent, label in entities if limpiar_uri(ent) == limpiar_uri(src)), None)
        tgt_tipo = next((label.lower() for ent, label in entities if limpiar_uri(ent) == limpiar_uri(tgt)), None)

        if src_tipo is None or tgt_tipo is None:
            continue

        src_uri = EX[limpiar_uri(src)]  # limpiar_uri aquí
        tgt_uri = EX[limpiar_uri(tgt)]  # limpiar_uri aquí

        predicado = verbo_adecuado(src_tipo, tgt_tipo, verbo)

        if predicado == EX.co_ocurre_con and src_tipo in {"person", "personaje"} and tgt_tipo in {"person", "personaje"}:
            g.add((src_uri, FOAF.knows, tgt_uri))
        else:
            g.add((src_uri, predicado, tgt_uri))

    turtle_data = g.serialize(format="turtle")
    header = (
        "@prefix ex: <http://stephenkingverse.org/> .\n"
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
    )
    if not turtle_data.startswith("@prefix ex:"):
        turtle_data = header + turtle_data

    return turtle_data