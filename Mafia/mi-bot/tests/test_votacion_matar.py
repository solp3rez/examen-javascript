import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_votacion_matar():
    """Verifica que el comando !matar maneje correctamente las votaciones y restricciones."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()

    # Simulación de la fase Día con un mafioso y un ciudadano
    bot.partida_mafia["fase"] = "Día"
    bot.partida_mafia["roles"] = {1: "Mafioso", 2: "Ciudadano"}
    
    # El mafioso vota para matar al ciudadano
    await bot.votar_matar(ctx, "Player_2")
    
    # Verificar que el jugador ha sido marcado para matar
    assert "Has votado para matar" in ctx.channel.send.call_args[0][0]
