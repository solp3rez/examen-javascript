import pytest
import os
from unittest.mock import AsyncMock, MagicMock
import bot
from discord.ext import tasks # Necesario para detener el loop en tests

# Archivo ranking temporal
TEST_RANKING_FILE = "tests/test_ranking.json"
bot.RANKING_FILE = TEST_RANKING_FILE

# Estado inicial del juego (actualizado para coincidir con el bot.py)
ESTADO_INICIAL = {
    "activa": False,
    "max_jugadores": 0,
    "modo": "normal", # Agregado 'modo'
    "fase_actual": "Inscripción", # Cambiado de 'fase' a 'fase_actual'
    "jugadores_vivos": {}, # Cambiado de 'jugadores_unidos'
    "jugadores_muertos": {}, # Agregado
    "roles_asignados": {}, # Cambiado de 'roles'
    "votos_dia": {},
    "acciones_nocturnas": {}, # Cambiado de 'victima_noche_id'
    "canal_juego": None,
}

# -------------------------------
# Reiniciar estado antes/después
# -------------------------------
@pytest.fixture(autouse=True)
def reiniciar_juego():

    # Asegurar que el loop esté detenido antes de iniciar cualquier test
    if bot.partida_loop.is_running():
        bot.partida_loop.stop()

    bot.partida_mafia.clear()
    bot.partida_mafia.update(ESTADO_INICIAL)

    if os.path.exists(TEST_RANKING_FILE):
        os.remove(TEST_RANKING_FILE)

    yield

    # Asegurar que el loop esté detenido al finalizar el test
    if bot.partida_loop.is_running():
        bot.partida_loop.stop()
        
    bot.partida_mafia.clear()
    bot.partida_mafia.update(ESTADO_INICIAL)

    if os.path.exists(TEST_RANKING_FILE):
        os.remove(TEST_RANKING_FILE)


# -------------------------------
# Crear jugador falso
# -------------------------------
@pytest.fixture
def crear_jugador():
    def crear(id, nombre):
        m = MagicMock()
        m.id = id
        m.name = nombre
        m.mention = f"<@{id}>"
        m.send = AsyncMock()
        return m
    return crear


# -------------------------------
# Bot falso
# -------------------------------
@pytest.fixture
def bot_falso():
    b = MagicMock()
    # Usamos AsyncMock para simular métodos asíncronos como get_user si fuera necesario
    b.get_user = MagicMock(return_value=MagicMock(name="UsuarioFalso")) 
    bot.bot = b
    return b


# -------------------------------
# Contexto (ctx) falso
# -------------------------------
@pytest.fixture
def ctx_falso(crear_jugador, bot_falso):

    ctx = MagicMock()
    ctx.guild = MagicMock() # Necesario para diferenciar comandos DM/Canal

    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()
    ctx.send = ctx.channel.send

    ctx.author = crear_jugador(101, "Jugador1")

    ctx.bot = bot_falso

    return ctx