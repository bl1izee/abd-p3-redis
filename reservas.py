"""EnVivo · fase 3 · reserva temporal de asientos.

Una reserva dura cinco minutos y, si nadie la confirma, **se libera sola**.
No debe haber ningún proceso de limpieza: la propia base de datos se encarga.

Las firmas y los valores de retorno **no deben cambiarse**.
"""

import redis

SEGUNDOS_POR_DEFECTO = 300


def clave(evento_id, asiento) -> str:
    """Clave de Redis. Formato: envivo:asiento:<evento>:<asiento>"""
    
    return f"envivo:asiento:{evento_id}:{asiento}"


def reservar(r: redis.Redis, evento_id, asiento, usuario_id,
             segundos: int = SEGUNDOS_POR_DEFECTO) -> bool:
    """Reserva el asiento si está libre. Devuelve si se ha conseguido.

    Dos usuarios que lo intenten a la vez: **solo uno** puede conseguirlo.
    """
    
    resultado = r.set(
        clave(evento_id, asiento),
        str(usuario_id),
        nx=True, # hace que solo se cree si la clave todavia no existe
        ex=segundos # establece los segundos que tardara en caducar la reserva
    )

    # Redis devuelve True si ha creado la clave y None si ya existia
    return resultado is not None


def propietario(r: redis.Redis, evento_id, asiento) -> str | None:
    """Quién tiene reservado el asiento, o None si está libre."""
    
    usuario_id = r.get(clave(evento_id, asiento))

    if usuario_id is None:
        return None

    # Si Redis devuelve bytes los convertimos a texto
    if isinstance(usuario_id, bytes):
        usuario_id = usuario_id.decode("utf-8")

    return usuario_id


def segundos_restantes(r: redis.Redis, evento_id, asiento) -> int:
    """Segundos que quedan. -1 si la reserva es firme, -2 si no hay reserva."""
    
    return r.ttl(clave(evento_id, asiento))


def liberar(r: redis.Redis, evento_id, asiento, usuario_id) -> bool:
    """Libera la reserva, **solo si es de ese usuario**.

    Devuelve True si la ha liberado y False si el asiento estaba libre o
    reservado por otro. Comprobar y borrar en dos comandos desde el cliente
    **no es correcto**: entre uno y otro la reserva puede caducar y pasar a
    otro usuario, y se le borraría la suya.
    """

    # GET comprueba el propietario y DEL elimina la reserva (devuelve 1 si ha borrado la clave y 0 si no)
    script = """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    else
        return 0
    end
    """

    # EVAL ejecuta el script directamente en Redis
    # Ejecutamos el script sobre una clave y pasamos el usuario como argumento
    resultado = r.eval(
        script,
        1,
        clave(evento_id, asiento),
        str(usuario_id)
    )

    return bool(resultado)


def confirmar(r: redis.Redis, evento_id, asiento, usuario_id) -> bool:
    """Convierte la reserva en firme: deja de caducar.

    Solo puede hacerlo el propietario. Devuelve si se ha confirmado.
    """

    # GET comprueba el propietario y PERSIST elimina la caducidad (si coincide)
    script = """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        redis.call('PERSIST', KEYS[1])
        return 1
    else
        return 0
    end
    """

    resultado = r.eval(
        script,
        1,
        clave(evento_id, asiento),
        str(usuario_id)
    )

    return bool(resultado)