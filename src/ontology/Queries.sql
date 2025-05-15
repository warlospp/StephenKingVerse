// Contar nodos
MATCH (n) RETURN count(n);

// Ver etiquetas
CALL db.labels();

// Ver propiedades
CALL db.propertyKeys();

//Para ver persnajes
MATCH (p:ns0__Personaje)
WITH p, split(p.uri, "/")[-1] AS nombreFragmento
RETURN nombreFragmento LIMIT 10;

//Para consultar nodos de la clase Personaje, usa la etiqueta ns0__Personaje:
MATCH (p:ns0__Personaje) RETURN p LIMIT 10;

//Para ver relaciones (por ejemplo, co_ocurre_con):
MATCH (a)-[r:ns0__co_ocurre_con]->(b) RETURN a, r, b LIMIT 10;

//Muestro
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 1000

//Depuracion
MATCH (n)
WHERE NOT (n)--()
RETURN n LIMIT 100

MATCH (n)
WHERE NOT (n)--()
DETACH DELETE n;



