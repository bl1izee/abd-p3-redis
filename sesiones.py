"""EnVivo · fase 3 · usuarios y sesiones.

De cada usuario se guarda: nombre completo, nombre de usuario, contraseña
(puede estar en plano), privilegios (entero positivo) y el token de sesión si
tiene una activa. Las sesiones duran **un mes** y al caducar desaparecen solas.

Las firmas y los valores de retorno **no deben cambiarse**.
"""

import redis
import secrets # se usa para crear los tokens de sesión

DURACION_SESION = 30 * 24 * 60 * 60      # un mes
SIN_ACCESO = -1


def clave_usuario(usuario: str) -> str:
    """Formato: envivo:usuario:<usuario>"""
    # TODO
    return f"envivo:usuario:{usuario}"


def clave_sesion(token: str) -> str:
    """Formato: envivo:sesion:<token>"""
    # TODO
    return f"envivo:sesion:{token}"


# ── Gestión de usuarios (CRUD) ──────────────────────────────────────────────

def crear_usuario(r: redis.Redis, usuario: str, nombre: str,
                  password: str, privilegios: int) -> bool:
    """Crea el usuario si no existe. Devuelve si se ha creado."""
    # TODO
    # Creamos la clave del usuario
    claveU = clave_usuario(usuario)

    # Comprobamos si el usuario ya existe
    if r.exists(claveU):
        return False

    # Guardamos los datos del usuario en una tabla hash, mapping equivale a hacer varias llamadas individuales
    r.hset(claveU, mapping={
        "nombre": nombre,
        "usuario": usuario,
        "password": password,
        "privilegios": privilegios,
        "token": ""
    })

    return True


def obtener_usuario(r: redis.Redis, usuario: str) -> dict | None:
    """Todos los campos del usuario, o None si no existe.

    `privilegios` debe venir como **entero**, no como cadena.
    """
    # TODO
    # Creamos la clave del usuario
    claveU = clave_usuario(usuario)

    # Obtenemos todos los campos del usuario
    datos = r.hgetall(claveU)

    # Comprobamos si existe
    if not datos:
        return None

    # Convertimos privilegios a entero
    datos["privilegios"] = int(datos["privilegios"])

    return datos

# **campos contiene un diccionario
def actualizar_usuario(r: redis.Redis, usuario: str, **campos) -> bool:
    """Modifica los campos indicados y **solo** esos.

    Devuelve False si el usuario no existe.
    """
    # TODO
    # Creamos la clave del usuario
    claveU = clave_usuario(usuario)

    # Comprobamos si existe el usuario
    if not r.exists(claveU):
        return False

    # Actualizamos únicamente los campos recibidos
    r.hset(claveU, mapping=campos)

    return True


def borrar_usuario(r: redis.Redis, usuario: str) -> bool:
    """Borra el usuario. Si tenía sesión abierta, debe quedar cerrada."""
    # TODO
    # Creamos la clave del usuario
    claveU = clave_usuario(usuario)

    # Comprobamos si existe el usuario
    if not r.exists(claveU):
        return False

    # Obtenemos el token de sesión
    token = r.hget(claveU, "token")

    # Comprobamos que tenga un token guardado el usuario
    if token != "":

        # permite que funcione independientemente de si Redis está configurado con decode_responses=True
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        # Creamos la clave de la sesión
        claveS = clave_sesion(token)

        # Eliminamos la sesión si existe
        if r.exists(claveS):
            r.delete(claveS)

        # Eliminamos el usuario
        r.delete(claveU)

    return True


# ── Sesiones ────────────────────────────────────────────────────────────────

def login(r: redis.Redis, usuario: str, password: str) -> tuple[int, str | None]:
    """Comprueba las credenciales y abre una sesión.

    Devuelve `(privilegios, token)` si son correctas y `(-1, None)` si no.
    Un login nuevo debe invalidar la sesión anterior del mismo usuario.
    """
    # TODO
    raise NotImplementedError


def login_por_token(r: redis.Redis, token: str) -> int:
    """Privilegios asociados al token, o -1 si no vale.

    Un token cuya sesión ha caducado devuelve -1, igual que uno inventado.
    """
    # TODO
    raise NotImplementedError


def logout(r: redis.Redis, token: str) -> bool:
    """Cierra la sesión. Devuelve si había una sesión que cerrar."""
    # TODO
    raise NotImplementedError


def segundos_de_sesion(r: redis.Redis, token: str) -> int:
    """Segundos que le quedan a la sesión. -2 si no existe."""
    # TODO
    raise NotImplementedError
