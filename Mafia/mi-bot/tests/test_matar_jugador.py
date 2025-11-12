import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_matar_jugador():
    """Verifica que el comando !matar mate correctamente a un jugador y muestra el mensaje adecuado."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Simula la situación en que un mafioso mata a un jugador
    bot.partida_mafia["roles"] = {1: "Mafioso", 2: "Ciudadano"}
    await bot.matar(ctx, "Player_2")  # El mafioso mata al ciudadano
    
    # Verifica que el jugador ha sido eliminado del juego
    assert "has sido eliminado del juego" in ctx.channel.send.call_args[0][0]
    assert 2 not in bot.partida_mafia["jugadores_unidos"]
