from neo4j import GraphDatabase, exceptions

def clear_graph_tx(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def init_n10s_config_tx(tx):
    tx.run("CALL n10s.graphconfig.init()")

def set_n10s_config_tx(tx):
    # Configura Neosemantics para usar el prefijo ex y otras opciones recomendadas
    tx.run("""
    CALL n10s.graphconfig.set({
      handleVocabUris: 'SHORTEN',
      handleMultival: 'ARRAY',
      keepLangTag: true,
      handleRDFTypes: 'LABELS',
      prefixMappings: { ex: 'http://example.org/' }
    })
    """)

def _import_ontology_tx(tx, turtle_data):
    query = """
    CALL n10s.rdf.import.inline($turtle, 'Turtle')
    """
    tx.run(query, turtle=turtle_data)

def normalize_ns0_nombre_tx(tx):
    tx.run("""
    MATCH (n)
    WHERE exists(n.`ns0__nombre`)
    SET n.name = n.`ns0__nombre`
    REMOVE n.`ns0__nombre`
    """)

def normalize_ns1_name_tx(tx):
    tx.run("""
    MATCH (n)
    WHERE exists(n.`ns1__name`)
    SET n.name = n.`ns1__name`
    REMOVE n.`ns1__name`
    """)

def remove_unconnected_nodes_tx(tx):
    tx.run("""
    MATCH (n)
    WHERE NOT (n)--()
    DELETE n
    """)

def generar_historia_y_guardar(self, archivo_salida):
    query = """
    MATCH (origen)-[relacion]->(destino)
    WITH origen, destino, toLower(replace(type(relacion), "_", " ")) AS rel_text
    WITH origen, destino,
            CASE
            WHEN substring(rel_text, 5) = "co ocurre con" THEN "ocurrir en"
            WHEN substring(rel_text, 5) = "knows" THEN "conocer a"
            ELSE substring(rel_text, 5)
            END AS rel_modificada
    RETURN origen.name + " " + rel_modificada + " " + destino.name AS frase
    """

def validate_import_tx(tx):
    result = tx.run("MATCH (n) RETURN count(n) AS node_count")
    record = result.single()
    return record["node_count"] if record else 0

def insert_ontology(uri, user, password, turtle_data):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            print("Limpiando grafo...")
            session.write_transaction(clear_graph_tx)
            
            print("Inicializando configuración n10s...")
            session.write_transaction(init_n10s_config_tx)
            
            print("Configurando prefijos y opciones n10s...")
            session.write_transaction(set_n10s_config_tx)
            
            print("Importando ontología...")
            session.write_transaction(_import_ontology_tx, turtle_data)

            print("Normalizando propiedad ns0__nombre a name...")
            session.write_transaction(normalize_ns0_nombre_tx)

            print("Normalizando propiedad ns1__name a name...")
            session.write_transaction(normalize_ns1_name_tx)
            
            print("Eliminando nodos sin relaciones...")
            session.write_transaction(remove_unconnected_nodes_tx)

            print("Validando importación...")
            node_count = session.read_transaction(validate_import_tx)
            if node_count > 0:
                print(f"Importación exitosa. Nodos importados: {node_count}")
            else:
                print("Importación fallida o no se importaron nodos.")
    finally:
        driver.close()
