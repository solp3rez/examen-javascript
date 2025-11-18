import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Importar el módulo principal y las variables/constantes
import bot 
from bot import load_ranking, save_ranking, update_ranking, award_points

# Usaremos la constante TEST_RANKING_FILE de conftest.py

# --- Tests de Carga y Guardado (I/O) ---

def test_load_ranking_archivo_no_existe(cleanup_state):
    """Verifica que load_ranking devuelve {} si el archivo no existe."""
    ranking = load_ranking()
    assert ranking == {}

def test_save_and_load_ranking_exito(cleanup_state):
    """Verifica que los datos se guardan y se cargan correctamente."""
    data = {"1234": {"puntos": 50, "nombre": "Tester"}}
    save_ranking(data)
    
    loaded_data = load_ranking()
    assert loaded_data == data

def test_load_ranking_json_invalido(cleanup_state):
    """Verifica que load_ranking maneja errores JSON y devuelve {}."""
    # Simular un archivo corrupto
    with open(bot.RANKING_FILE, 'w') as f:
        f.write("{esto no es json valido")
    
    ranking = load_ranking()
    assert ranking == {}

# --- Tests de Actualización de Ranking ---

@patch('bot.bot') # Mockear el objeto bot global
def test_update_ranking_nuevo_jugador(mock_bot, cleanup_state, member_factory):
    """Verifica la adición de un nuevo jugador al ranking."""
    jugador_id = 999
    jugador_nombre = "NuevoJugador"
    
    # Configurar el mock para que bot.get_user(999) devuelva el MockMember
    mock_bot.get_user.return_value = member_factory(jugador_id, jugador_nombre)

    update_ranking(jugador_id, 25)
    
    ranking = load_ranking()
    assert str(jugador_id) in ranking
    assert ranking[str(jugador_id)]["puntos"] == 25
    assert ranking[str(jugador_id)]["nombre"] == jugador_nombre

@patch('bot.bot')
def test_update_ranking_existente(mock_bot, cleanup_state, member_factory):
    """Verifica la actualización de puntos de un jugador existente."""
    jugador_id = 1000
    jugador_nombre = "JugadorExistente"
    
    # 1. Setup inicial
    mock_bot.get_user.return_value = member_factory(jugador_id, jugador_nombre)
    update_ranking(jugador_id, 10) # 10 puntos iniciales
    
    # 2. Segunda actualización
    update_ranking(jugador_id, 5) # Sumar 5 puntos
    
    ranking = load_ranking()
    assert ranking[str(jugador_id)]["puntos"] == 15 # 10 + 5
    assert ranking[str(jugador_id)]["nombre"] == jugador_nombre

# --- Tests de Asignación de Puntos (award_points) ---

@pytest.mark.asyncio
@patch('bot.update_ranking')
@patch('bot.bot')
async def test_award_points_victoria_mafia(mock_bot, mock_update_ranking, member_factory):
    """Verifica la asignación de puntos en caso de victoria de la Mafia (15 pts)."""
    
    # Mock de jugadores y estado de partida
    mafia = member_factory(10, "Mafioso1")
    ciudadano = member_factory(20, "Ciudadano1")
    canal = AsyncMock() # Mock del canal para enviar mensajes
    
    bot.partida_mafia["roles"] = {
        mafia.id: "Mafioso",
        ciudadano.id: "Ciudadano"
    }
    # Mockear bot.get_user para que resuelva los nombres
    mock_bot.get_user.side_effect = lambda user_id: {10: mafia, 20: ciudadano}.get(user_id)
    
    await award_points(canal, "Mafia")
    
    # Asertos: Solo el Mafioso debe recibir 15 puntos
    mock_update_ranking.assert_any_call(mafia.id, 15)
    
    # Verificar que el Ciudadano no recibió puntos
    with pytest.raises(AssertionError):
        mock_update_ranking.assert_any_call(ciudadano.id, 15)
        mock_update_ranking.assert_any_call(ciudadano.id, 10)

    # Verificar mensajes de confirmación
    canal.send.assert_any_call(
        f"--- PUNTUACIÓN DE LA PARTIDA ---\n"
        f"Mafioso ({mafia.name}): +15 puntos (Victoria de la Mafia).\n"
    )

@pytest.mark.asyncio
@patch('bot.update_ranking')
@patch('bot.bot')
async def test_award_points_victoria_ciudad(mock_bot, mock_update_ranking, member_factory):
    """Verifica la asignación de puntos en caso de victoria de la Ciudad (10 pts)."""
    
    # Mock de jugadores y estado de partida
    mafia = member_factory(30, "MafiaMala")
    ciudadano = member_factory(40, "CiudadanoBueno")
    canal = AsyncMock()
    
    bot.partida_mafia["roles"] = {
        mafia.id: "Mafioso",
        ciudadano.id: "Ciudadano"
    }
    mock_bot.get_user.side_effect = lambda user_id: {30: mafia, 40: ciudadano}.get(user_id)
    
    await award_points(canal, "Ciudad")
    
    # Asertos: Solo el Ciudadano debe recibir 10 puntos (rol != "Mafioso")
    mock_update_ranking.assert_any_call(ciudadano.id, 10)
    
    # Verificar que el Mafioso no recibió puntos
    with pytest.raises(AssertionError):
        mock_update_ranking.assert_any_call(mafia.id, 10)

    # Verificar mensajes de confirmación
    canal.send.assert_any_call(
        f"--- PUNTUACIÓN DE LA PARTIDA ---\n"
        f"Ciudadano ({ciudadano.name}): +10 puntos (Victoria de la Ciudad).\n"
    )