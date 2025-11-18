import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Importar el módulo principal
import bot 

# Para todos los tests en este archivo, usaremos un contexto de servidor (no DM)
# y asumimos que las fixtures (mock_ctx, cleanup_state) están disponibles por conftest.py

# --- Comandos de Creación de Partida ---

@pytest.mark.asyncio
async def test_crear_partida_normal_exito(mock_ctx):
    """Verifica que el comando !mafia crear inicializa el estado correctamente."""
    await bot.crear_partida(mock_ctx, 3) # Crear partida para 3 jugadores

    assert bot.partida_mafia["activa"] == True
    assert bot.partida_mafia["max_jugadores"] == 3
    assert bot.partida_mafia["modo_rapido"] == False
    
    # Verificar el mensaje de confirmación
    mock_ctx.channel.send.assert_called_with(
        f"Partida de Mafia NORMAL creada para 3 jugadores. "
        f"Usa `!mafia unirme` para participar.\n"
        f"Jugadores actuales: 0/3"
    )

@pytest.mark.asyncio
async def test_crear_partida_rapida_exito(mock_ctx):
    """Verifica que el comando !mafia rapido inicializa el modo rápido."""
    await bot.crear_partida_rapida(mock_ctx, 4) 

    assert bot.partida_mafia["activa"] == True
    assert bot.partida_mafia["max_jugadores"] == 4
    assert bot.partida_mafia["modo_rapido"] == True
    
    # Verificar el mensaje de confirmación (que mencione el modo rápido)
    mock_ctx.channel.send.assert_called_with(
        pytest.approx("Partida de Mafia RÁPIDA creada para 4 jugadores. Límites de tiempo: Noche 30s, Día 60s. Usa `!mafia unirme` para participar.\nJugadores actuales: 0/4")
    )

@pytest.mark.asyncio
async def test_crear_partida_jugadores_insuficientes(mock_ctx):
    """Verifica que el bot rechaza la creación con menos de 2 jugadores."""
    await bot.crear_partida(mock_ctx, 1)

    assert bot.partida_mafia["activa"] == False # No debe activar la partida
    mock_ctx.channel.send.assert_called_with("Necesitas al menos 2 jugadores para empezar Mafia.")

# --- Comandos de Unión a Partida ---

@pytest.mark.asyncio
async def test_unirse_sin_partida_activa(mock_ctx):
    """Verifica que unirse falla si no hay partida activa."""
    bot.partida_mafia["activa"] = False
    await bot.unirse_partida(mock_ctx)

    mock_ctx.channel.send.assert_called_with(
        "No hay una partida de Mafia activa. Usa `!mafia crear <jugadores>` o `!mafia rapido <jugadores>`."
    )
    assert len(bot.partida_mafia["jugadores_unidos"]) == 0

@pytest.mark.asyncio
async def test_unirse_partida_exito(mock_ctx, member_factory):
    """Verifica que el jugador se añade a la lista y el conteo es correcto."""
    
    # Setup: Partida activa para 3 jugadores
    await bot.crear_partida(mock_ctx, 3)
    
    # Mockear un segundo jugador
    jugador2 = member_factory(202, "Jugador2")
    mock_ctx.author = jugador2

    await bot.unirse_partida(mock_ctx)
    
    assert len(bot.partida_mafia["jugadores_unidos"]) == 1 # El autor del ctx inicial no se une en esta prueba

    # Nota: mock_ctx.author es Player1, pero lo reemplazamos por Jugador2 para la unión
    assert bot.partida_mafia["jugadores_unidos"][0].id == 202

@pytest.mark.asyncio
async def test_unirse_partida_completa_e_inicio(mock_ctx, member_factory):
    """Verifica que la partida inicia automáticamente al alcanzar el máximo."""
    
    # Mock de funciones clave para evitar fallos de asyncio/discord
    with patch('bot.asignar_roles', new_callable=AsyncMock) as mock_asignar_roles:
        
        # Setup: Crear partida para 2 jugadores
        await bot.crear_partida(mock_ctx, 2)
        canal_mock = mock_ctx.channel

        # 1. Unirse (Jugador 1)
        jugador1 = member_factory(101, "Jugador1")
        mock_ctx.author = jugador1
        await bot.unirse_partida(mock_ctx)
        
        # 2. Unirse (Jugador 2 - Completa el cupo)
        jugador2 = member_factory(202, "Jugador2")
        mock_ctx.author = jugador2
        await bot.unirse_partida(mock_ctx)
        
        # Asertos
        assert len(bot.partida_mafia["jugadores_unidos"]) == 2
        
        # Verificar que se llama a la función de inicio de juego
        canal_mock.send.assert_any_call(
            "El grupo está completo (2/2)! Iniciando la asignación de roles..."
        )
        mock_asignar_roles.assert_awaited_once()