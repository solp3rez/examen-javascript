import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_partida_rapida():
    """Verifica que el bot pueda crear partidas rápidas y gestionar jugadores de manera fluida."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()

    # Verificar que una partida rápida se crea con 2 jugadores
    await bot.crear_partida(ctx, 2)
    assert bot.partida_mafia["activa"] is True
    assert bot.partida_mafia["max_jugadores"] == 2
