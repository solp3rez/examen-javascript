import pytest
import unittest.mock
import json
import os
from unittest.mock import AsyncMock, MagicMock

# Importar el módulo principal (bot.py) para acceder a las variables y funciones
import bot 

# --- Rutas y Constantes para el Testing ---
TEST_RANKING_FILE = 'tests/test_ranking.json'
bot.RANKING_FILE = TEST_RANKING_FILE # Sobreescribir la ruta para el testing

# --- Fixture 1: Limpieza del Estado Global y Archivo de Ranking ---
@pytest.fixture(autouse=True)
def cleanup_state():
    """Asegura que el estado global del bot esté limpio antes y después de cada test."""
    
    # 1. Limpieza antes del test
    original_state = {
        "activa": False,
        "max_jugadores": 0,
        "jugadores_unidos": [], 
        "roles": {},        
        "canal_juego": None,        
        "victima_noche_id": None, 
        "fase": "Noche",        
        "modo_rapido": False,    
        "timer_task": None      
    }
    bot.partida_mafia.clear()
    bot.partida_mafia.update(original_state)
    bot.votos_dia.clear()

    if os.path.exists(TEST_RANKING_FILE):
        os.remove(TEST_RANKING_FILE)

    yield # Aquí se ejecuta el test

    # 2. Limpieza después del test (Post-test cleanup)
    bot.partida_mafia.clear()
    bot.partida_mafia.update(original_state)
    bot.votos_dia.clear()
    if os.path.exists(TEST_RANKING_FILE):
        os.remove(TEST_RANKING_FILE)

# --- Fixture 2: Creación de Mock Objects de Discord ---

@pytest.fixture
def member_factory(player_id, player_name):
    """Crea un objeto Mock que simula un discord.Member o discord.User."""
    member = MagicMock()
    member.id = player_id
    member.name = player_name
    member.mention = f"<@{player_id}>"
    member.send = AsyncMock() # Para simular el envío de DMs
    return member

@pytest.fixture
def mock_ctx(mock_bot):
    """Crea un objeto Mock que simula el Contexto de un Comando (ctx)."""
    ctx = MagicMock()
    ctx.bot = mock_bot
    ctx.guild = MagicMock() # Simula un contexto en un servidor (no DM)
    ctx.channel = AsyncMock() # Canal donde se ejecuta el comando
    ctx.channel.send = AsyncMock() # Simular el envío de mensajes al canal
    ctx.send = ctx.channel.send
    
    # Se añade un mock_member por defecto para ctx.author
    ctx.author = member_factory(101, "Player1") 
    
    # Simular la guild (servidor) para asignar roles
    ctx.guild.name = "Test Server" 

    return ctx

@pytest.fixture
def mock_bot():
    """Crea un objeto Mock para el bot, crucial para get_user en ranking."""
    bot_mock = MagicMock()
    bot_mock.get_user = MagicMock() # Será reemplazado por la implementación del test
    return bot_mock