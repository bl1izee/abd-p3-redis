"""EnVivo · fase 2 · consultas e informes.

Cada consulta es un *pipeline* de agregación declarado como una **lista de
diccionarios de Python**, no como una cadena de texto. Así se ejecuta tal cual:

    from consultas import CONSULTAS
    c = CONSULTAS["C1"]
    resultado = list(db[c["coleccion"]].aggregate(c["pipeline"]))

Hay que rellenar los ocho pipelines. El diccionario `CONSULTAS` del final ya
está escrito y **no debe modificarse**: es el contrato de entrega.

Recordatorio del esquema, tal como quedó en la fase 1:

  recinto    nombre, direccion, direccion_loc (punto GeoJSON), ciudad, aforo,
             zonas [{nombre, asientos}], servicios []
  artista    nombre, generos [], pais, anio_inicio
  evento     titulo, artistas [] (nombres), recinto (nombre), fecha,
             precios_por_zona [{zona, precio, vendidas}], entradas_vendidas,
             estado
  asistente  nombre, email, fecha_alta, direccion, direccion_loc, preferencias []

Atención: `titulo` **no es único** (un mismo artista puede repetir recinto en
otra fecha), así que para contar eventos hay que usar `_id`.
"""

# ── C1 · Artistas por género musical ────────────────────────────────────────
# Colección: artista
# Devuelve, por cada género: genero, n (número de artistas) y artistas (lista
# de nombres, ORDENADA). Ordenado por n descendente y, a igualdad, por genero.
C1 = [
    {"$project": { # Seleccionamos los campos que necesitamos y así no trabaja el sort con tantos datos
        "nombre": 1,
        "generos": 1
    }}, 
    {"$sort": {"nombre": 1}},  # Ordenamos por nombre en orden ASC
    {"$unwind": "$generos"},  # Descomponemos el array de géneros de cada colección
    {"$group": { # Agrupamos por géneros y mostramos un acumulador del número de artistas por cada género y un array con todos los artistas que tiene el género
        "_id": "$generos",
        "n": {"$sum": 1},
        "artistas": {"$push": "$nombre"}  # Creamos una lista "artistas" donde vamos agregando los nombres de los artistas
    }},
    {"$sort": {"n": -1, "_id": 1}},  # Ordenamos por el número de artistas en orden DESC y, en caso de igualdad, por género en orden ASC
    {"$project": {
        "_id": 0,
        "genero": "$_id",
        "n": 1,
        "artistas": 1
    }}
]

# ── C2 · Ocupación media por recinto ────────────────────────────────────────
# Colección: evento
# Devuelve, por cada recinto: recinto, eventos y ocupacion_media, esta última
# en PORCENTAJE del aforo del recinto y redondeada a un decimal. Ordenado por
# ocupacion_media descendente y, a igualdad, por recinto.
C2 = [

# Unimos evento y recinto
    {"$lookup": {
        "from": "recinto",
        "localField": "recinto",
        "foreignField": "nombre",
        "as": "datos_recinto"
    }},

 # Convertimos el resultado datos_recinto en un documento
    {"$unwind": "$datos_recinto"},

# Agrupamos los eventos por recinto.
    {"$group": { 
        "_id": "$recinto",
        "eventos": {"$sum": 1},
        "ocupacion_media": {"$avg": { # Ocupacion media en porcentaje
            "$cond": {
                "if": {"$gt": ["$datos_recinto.aforo", 0]}, # Aforo mayor que 0
                "then": {"$multiply": [
                    {"$divide": [
                        "$entradas_vendidas",
                        "$datos_recinto.aforo"
                    ]},
                    100
                ]},
                "else": None
            }
        }}
    }},

    {"$project": {
        "_id": 0,
        "recinto": "$_id", # Renombra _id como recinto
        "eventos": 1,
        "ocupacion_media": {"$round": ["$ocupacion_media", 1]} # Redondea a 1 decimal
    }},

# Ordena descendente en caso de empate alfabeticamente
    {"$sort": {"ocupacion_media": -1, "recinto": 1}}

]

# ── C3 · Ingresos por mes ───────────────────────────────────────────────────
# Colección: evento
# El ingreso de un evento es la suma, por zona, de precio x vendidas.
# Devuelve, por cada mes: mes (formato "AAAA-MM"), ingresos redondeados a dos
# decimales y eventos (número de eventos de ese mes). Ordenado por mes.
C3 = [
    {"$project": {
        "mes": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}},
        "precios_por_zona": 1
    }},
    {"$unwind": "$precios_por_zona"},
    {"$group": {
        "_id": "$mes",
        "ingresos": {"$sum": {"$multiply": ["$precios_por_zona.precio", "$precios_por_zona.vendidas"]}},
        "eventos_lista": {"$addToSet": "$_id"} # Metemos los eventos que coincidan en mes en el array
    }},
    {"$project": {
        "_id": 0,
        "mes": "$_id",
        "ingresos": {"$round": ["$ingresos", 2]},
        "eventos": {"$size": "$eventos_lista"} # Devuelve el tamaño de la lista que guarda los eventos
    }},
    {"$sort": {"mes": 1}}
]

# ── C4 · Los tres artistas más programados ──────────────────────────────────
# Colección: evento
# Devuelve, para cada uno de los tres primeros: artista, actuaciones y
# recintos (número de recintos DISTINTOS en los que ha actuado). Ordenado por
# actuaciones descendente y, a igualdad, por artista.
C4 = [
# Separamos los artistas de cada evento para tratarlos individualmente.
    {"$unwind": "$artistas"},

# Agrupa los artistas y eventos para no repetirlos
    {"$group": {
        "_id": {"artista": "$artistas", "evento": "$_id"},
        "recinto": {"$first": "$recinto"} # Guarda el primer recinto de cada evento
    }},

# Agrupa todos los eventos de cada artista
    {"$group": {
        "_id": "$_id.artista",
        "actuaciones": {"$sum": 1},
        "recintos_lista": {"$addToSet": "$recinto"} # Guarda los recintos distintos en los que ha actuado
    }},

    {"$project": {
        "_id": 0,
        "artista": "$_id",
        "actuaciones": 1,
        "recintos": {"$size": "$recintos_lista"} # Cuenta cuantos recintos distintos tiene en la lista
    }},

    {"$sort": {"actuaciones": -1, "artista": 1}},
    {"$limit": 3}
]


# ── C5 · Recintos a menos de 5 km de la Puerta del Sol ──────────────────────
# Colección: recinto
# El punto de referencia es [-3.7038, 40.4168].
# Devuelve, por cada recinto: recinto, ciudad, distancia_km redondeada a dos
# decimales, y eventos (número de eventos de ese recinto).

# Funcion para crear el indice que use en MongoDB Compass
# db.recinto.createIndex({ direccion_loc: "2dsphere" })

C5 = [
    {"$geoNear": {
        "near": {
            "type": "Point",
            "coordinates": [-3.7038, 40.4168]
        },
        "key": "direccion_loc", # ubicación GeoJSON
        "distanceField": "distancia", # distancia en metros
        "maxDistance": 5000,
        "spherical": True
    }},
    {"$lookup": {
        "from": "evento",
        "localField": "nombre",
        "foreignField": "recinto",
        "as": "eventos"
    }},
    {"$project": {
        "_id": 0,
        "recinto": "$nombre",
        "ciudad": 1,
        "distancia_km": { # Convierte metros a kilometros
            "$round": [{"$divide": ["$distancia", 1000]}, 2]
        },
        "eventos": {"$size": "$eventos"} 
    }}
]

# ── C6 · Cartel completo de los eventos con varios artistas ─────────────────
# Colección: evento
# Solo los eventos con MÁS DE UN artista. Devuelve: titulo, recinto y cartel,
# una lista con {nombre, pais, generos} de cada artista, ORDENADA por nombre.
# Ordenado por titulo.
C6 = [
    {"$set": {"numeroArtistas": {"$size": "$artistas"}}},  # Creamos un nuevo atributo que tiene el número de artistas
    {"$match": {"numeroArtistas": {"$gt": 1}}},
    {"$project": {
        "titulo": 1,
        "artistas": 1,
        "recinto": 1
    }},
    {"$lookup": {
        "from": "artista",
        "localField": "artistas",
        "foreignField": "nombre",
        "as": "datos_artista"
    }},
    # Primero filtramos los subcampos que queremos conservar de datos_artista
    {"$project": {
        "_id": 1,
        "titulo": 1,
        "recinto": 1,
        "datos_artista.nombre": 1,
        "datos_artista.pais": 1,
        "datos_artista.generos": 1
    }},
    {"$unwind": {"path": "$datos_artista"}},  # Desagrupamos el array
    {"$sort": {"datos_artista.nombre": 1}},  # Ordenamos por el nombre
    {"$group": {  # Volvemos a agrupar los datos, pero con los artistas ordenados
        "_id": "$_id",
        "titulo": {"$first": "$titulo"},
        "recinto_lista": {"$addToSet": "$recinto"},
        "cartel": {"$push": {
            "nombre": "$datos_artista.nombre",
            "pais": "$datos_artista.pais",
            "generos": "$datos_artista.generos"
        }}
    }},
    # Después renombramos datos_artista a cartel
    {"$project": {
        "_id": 0,
        "recinto_lista": 1,
        "titulo": 1,
        "cartel": 1
    }},

    {"$sort": {"titulo": 1}}
]

# ── C7 · Eventos por franja de ocupación ────────────────────────────────────
# Colección: evento
# Clasifica cada evento según su ocupación sobre el aforo del recinto:
#   agotado  >= 0,99      alta  >= 0,85      media  >= 0,70      baja  el resto
# Devuelve, por franja: franja y eventos. Ordenado por eventos descendente y,
# a igualdad, por franja.
C7 = [
    {"$lookup": {
        "from": "recinto",
        "localField": "recinto",
        "foreignField": "nombre",
        "as": "datos_recinto"
    }},
# Convierte el array datos_recinto en un documento
    {"$unwind": "$datos_recinto"},

# Calcula la ocupacion del evento
    {"$set": {
        "ocupacion": {
            "$divide": ["$entradas_vendidas", "$datos_recinto.aforo"]
        }
    }},
# Clasificamos
    {"$group": {
        "_id": {
            "$switch": {
                "branches": [
                    {"case": {"$gte": ["$ocupacion", 0.99]}, "then": "agotado"},
                    {"case": {"$gte": ["$ocupacion", 0.85]}, "then": "alta"},
                    {"case": {"$gte": ["$ocupacion", 0.70]}, "then": "media"}
                ],
                "default": "baja" # Menos de 70%
            }
        },
        "eventos": {"$sum": 1} # Cuenta los eventos de cada franja
    }},
    {"$project": {
        "_id": 0,
        "franja": "$_id",
        "eventos": 1
    }},
    {"$sort": {"eventos": -1, "franja": 1}}
]

# ── C8 · Informe materializado por recinto ──────────────────────────────────
# Colección: evento
# Escribe en la colección `informe_recintos` un documento por recinto, con
# _id = nombre del recinto, ingresos, eventos y aforo.
# Requisito: una SEGUNDA ejecución debe ACTUALIZAR la colección, no
# reemplazarla, de modo que se conserven los campos que se le hayan añadido
# por fuera.
C8 = [
    {
    "$project": {
        "titulo": 1,
        "recinto": 1,
        "precios_por_zona": 1
    }
    },
    {"$unwind": {"path": "$precios_por_zona"}},
    {
        "$group": {
            "_id": "$recinto",
            "ingresos": {
                "$sum": {
                    "$multiply": ["$precios_por_zona.precio", "$precios_por_zona.vendidas"]
                }
            },
            "eventos": {"$addToSet": "$_id"}
        }
    },
    {"$lookup": {
        "from": "recinto",
        "localField": "_id",
        "foreignField": "nombre",
        "as": "datos_recinto"
    }},
    {"$project": {
        "_id": 1,
        "ingresos": {
            "$round": ["$ingresos", 2]
        },
        "eventos": 1,
        "datos_recinto.aforo": 1
    }},
    {"$project": {
        "_id": 1,
        "ingresos": {"$round": ["$ingresos", 2]},
        "eventos": {"$size": "$eventos"},
        "aforo": "$datos_recinto"
    }},
    {"$merge": { # Escribe en la colección informe_recinto
        "into": "informe_recintos",
        "on": "_id",
        "whenMatched": "merge", # Si exist el documento se actualizan los campos necesarios
        "whenNotMatched": "insert" # Si no existe el documento se inserta
    }}
]


# ── Contrato de entrega · no modificar ──────────────────────────────────────
CONSULTAS = {
    "C1": {"coleccion": "artista", "pipeline": C1,
           "descripcion": "Artistas por género musical"},
    "C2": {"coleccion": "evento", "pipeline": C2,
           "descripcion": "Ocupación media por recinto"},
    "C3": {"coleccion": "evento", "pipeline": C3,
           "descripcion": "Ingresos por mes"},
    "C4": {"coleccion": "evento", "pipeline": C4,
           "descripcion": "Los tres artistas más programados"},
    "C5": {"coleccion": "recinto", "pipeline": C5,
           "descripcion": "Recintos a menos de 5 km de la Puerta del Sol"},
    "C6": {"coleccion": "evento", "pipeline": C6,
           "descripcion": "Cartel completo de los eventos con varios artistas"},
    "C7": {"coleccion": "evento", "pipeline": C7,
           "descripcion": "Eventos por franja de ocupación"},
    "C8": {"coleccion": "evento", "pipeline": C8,
           "descripcion": "Informe materializado por recinto"},
}
