import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_finalizar_partida():
    """Verifica que la partida termine correctamente y declare a los ganadores."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Simula que la partida ha llegado a su fin
    bot.partida_mafia["activa"] = False
    bot.partida_mafia["resultado"] = "La mafia ha ganado"
    
    # Finaliza la partida
    await bot.finalizar_partida(ctx)
    
    # Verifica el mensaje de victoria y que la partida esté desactivada
    assert "La mafia ha ganado" in ctx.channel.send.call_args[0][0]
    assert bot.partida_mafia["activa"] is False
