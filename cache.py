"""EnVivo · fase 3 · caché de documentos.

Hay que implementar la clase `CacheDocumentos`. Las firmas y los valores de
retorno **no deben cambiarse**: son el contrato con el que se corrige.
"""

import redis

# El módulo nativo json de Python solo entiende tipos de datos básicos, no entiende datetime o ObjectId. En cambio json_util si.
from bson import json_util

TTL_POR_DEFECTO = 24 * 60 * 60      # 24 horas
MEMORIA_MAXIMA = "150mb"
POLITICA_DESALOJO = None            # TODO: la política que pide el enunciado


class CacheDocumentos:
    """Caché de documentos con caducidad renovada en cada acceso."""

    def __init__(self, cliente: redis.Redis, ttl: int = TTL_POR_DEFECTO):
        self._r = cliente
        self.ttl = ttl

    def configurar_limite(self, memoria: str = MEMORIA_MAXIMA,
                          politica: str = POLITICA_DESALOJO) -> None:
        """Fija el límite de memoria y la política de desalojo de la caché."""
        # TODO
        raise NotImplementedError

    @staticmethod
    def clave(coleccion: str, id_documento) -> str:
        """Clave de Redis para un documento. Formato: envivo:cache:<col>:<id>"""
        # TODO
        raise NotImplementedError

    def get(self, coleccion: str, id_documento) -> dict | None:
        """Devuelve el documento cacheado, o None si no está.

        Cada acceso debe **renovar la caducidad** a `self.ttl`.
        """
        # TODO
        # usar json_util.loads
        raise NotImplementedError

    def set(self, coleccion: str, id_documento, documento: dict) -> None:
        """Guarda el documento en la caché con su caducidad.

        `get` tiene que devolverlo igual, con los mismos tipos: las fechas como
        fechas y los ObjectId como ObjectId.
        """
        # TODO
        # Construimos la clave en Redis (ej: "usuario:100")
        key = f"{coleccion}:{id_documento}"
        
        # Serializamos usando json_util para conservar ObjectId, datetime, etc.
        documento_serializado = json_util.dumps(documento)
        
        # Guardamos en Redis
        self._r.set(key, documento_serializado, ex=TTL_POR_DEFECTO)
        
    def invalidar(self, coleccion: str, id_documento) -> bool:
        """Saca el documento de la caché. Devuelve si estaba."""
        # TODO
        raise NotImplementedError

    def caducidad(self, coleccion: str, id_documento) -> int:
        """Segundos restantes. -1 si no caduca, -2 si no existe."""
        # TODO
        raise NotImplementedError
