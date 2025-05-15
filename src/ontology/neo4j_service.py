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

def remove_unconnected_nodes_tx(tx):
    tx.run("""
    MATCH (n)
    WHERE NOT (n)--()
    DELETE n
    """)

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
            
            #print("Eliminando nodos sin relaciones...")
            #session.write_transaction(remove_unconnected_nodes_tx)

            print("Validando importación...")
            node_count = session.read_transaction(validate_import_tx)
            if node_count > 0:
                print(f"Importación exitosa. Nodos importados: {node_count}")
            else:
                print("Importación fallida o no se importaron nodos.")
    finally:
        driver.close()
