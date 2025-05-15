import yake

def extraer_keyphrases_keybert_potente_con_scores(texto, max_phrases = 40 , max_words = 10):
    # Configuración de YAKE para español, frases de hasta 3 palabras
    kw_extractor = yake.KeywordExtractor(lan="es", n=max_words, top=max_phrases)
    
    # Extraer frases clave con sus puntuaciones
    keywords = kw_extractor.extract_keywords(texto)

    # Extraer solo las frases (sin puntuación)
    if not keywords:
        return []

    # Extraer solo los scores para normalización
    scores = [score for _, score in keywords]
    min_score = min(scores)
    max_score = max(scores)

    # Normalizar scores invertidos: 1 = más importante, 0 = menos importante
    if max_score == min_score:
        scores_norm = [1.0 for _ in scores]
    else:
        scores_norm = [1 - (s - min_score) / (max_score - min_score) for s in scores]

    # Combinar frase, score original y score normalizado
    resultados = [(frase, score, norm) for (frase, score), norm in zip(keywords, scores_norm)]

    # Filtrar frases válidas con condiciones adicionales
    frases_validas = []
    for (frase, _), norm_score in zip(keywords, scores_norm):
        if norm_score >= 0.7:
            palabras = frase.split()            
            # Validar: omitir si es una palabra con primera letra minúscula
            if len(palabras) == 1:
                #primera_letra = palabras[0][0] if palabras[0] else ''
                #if primera_letra.islower():
                continue  # Omitir esta frase
                    
            frases_validas.append(frase)


    #frases_validas = [frase for frase, score, norm_score in resultados if norm_score >= 0.7]


    return frases_validas
    #return keywords

#def keyphrases_a_parrafo_natural(frases_clave):
#    if len(frases_clave) == 0:
#        return ""
#    elif len(frases_clave) == 1:
#        return frases_clave[0] + "."
#    else:
#        parrafo = ", ".join(frases_clave[:-1]) + " y " + frases_clave[-1] + "."
#        return parrafo

