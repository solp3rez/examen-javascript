import pytest
from unittest.mock import MagicMock
from bot import bot  # Asegúrate de importar correctamente el objeto 'bot' o la clase que estés utilizando

@pytest.mark.asyncio
async def test_crear_partida_success():
    """Verifica que el comando crear_partida inicializa correctamente el estado del juego."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Simulación de la creación de la partida
    await bot.crear_partida(ctx, 5)
    
    # Verificación del estado de la partida
    assert bot.partida_mafia["activa"] is True
    assert bot.partida_mafia["max_jugadores"] == 5
    assert "Partida de Mafia NORMAL creada" in ctx.channel.send.call_args[0][0]
