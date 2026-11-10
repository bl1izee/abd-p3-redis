"""EnVivo · fase 3 · sala de espera virtual.

Cola de prioridad: los valores grandes son peticiones de alta prioridad y los
pequeños de baja. El operador atiende siempre la de mayor prioridad y, si no
hay ninguna, **espera** hasta que llegue.

Las firmas y los valores de retorno **no deben cambiarse**.
"""

import redis

# TODO: mayor que cualquier prioridad presente o futura.
PRIORIDAD_ABSOLUTA = float("inf")

def clave(evento_id) -> str:
    """Clave de Redis. Formato: envivo:sala:<evento>"""

    return f"envivo:sala:{evento_id}"


def entrar(r: redis.Redis, evento_id, usuario_id, prioridad: float) -> bool:
    """Registra al usuario en la sala con esa prioridad.

    Devuelve True si es nuevo en la cola y False si ya estaba (en ese caso se
    le actualiza la prioridad). Un usuario **no puede ocupar dos puestos**.
    """

    # Si la prioridad es absoluta, utilizamos +inf
    if float(prioridad) == PRIORIDAD_ABSOLUTA:
        prioridad = "+inf"
    else:
        prioridad = repr(float(prioridad))

    script = """
    local existe = redis.call('ZSCORE', KEYS[1], ARGV[1])

    redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])

    if existe then
        return 0
    else
        return 1
    end
    """

    resultado = r.eval(
        script,
        1,
        clave(evento_id),
        str(usuario_id),
        prioridad
    )

    return bool(resultado)


def atender_siguiente(r: redis.Redis, evento_id, timeout: int = 0):
    """Toma y elimina la petición de mayor prioridad.

    Devuelve `(usuario_id, prioridad)`, o None si se agota el `timeout`.
    Con `timeout=0` espera indefinidamente. Obtener y eliminar deben ser una
    sola operación, o dos operadores podrían atender al mismo usuario.
    """

    # BZPOPMAX obtiene y elimina el usuario con mayor prioridad.
    # Si la cola esta vacia, espera hasta que llegue una peticion.
    resultado = r.bzpopmax(clave(evento_id), timeout=timeout)

    # Si se agota el tiempo y no llega nadie, devuelve None.
    if resultado is None:
        return None

    # Redis devuelve la clave, el usuario y su prioridad.
    _, usuario_id, prioridad = resultado

    if isinstance(usuario_id, bytes):
        usuario_id = usuario_id.decode("utf-8")

    # Convertimos la prioridad a numero decimal.
    prioridad = float(prioridad)

    return usuario_id, prioridad


def en_espera(r: redis.Redis, evento_id) -> int:
    """Cuántos usuarios hay en la sala."""

    # ZCARD devuelve el numero de elementos
    return r.zcard(clave(evento_id))


def posicion(r: redis.Redis, evento_id, usuario_id) -> int | None:
    """Puesto en la cola **empezando en 1**, o None si el usuario no está.

    El puesto 1 es el que se va a atender antes.
    """

    # ZREVRANK obtiene la posicion ordenando de mayor a menor prioridad.
    puesto = r.zrevrank(clave(evento_id), str(usuario_id))

    # Si el usuario no esta en la cola, devuelve None.
    if puesto is None:
        return None

    # Redis empieza a contar desde 0, por eso sumamos 1.
    return puesto + 1
