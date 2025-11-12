import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_ranking_mafia():
    """Verifica que el bot actualice el ranking de jugadores correctamente después de cada partida."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Simulación de una partida terminada donde la mafia gana
    bot.partida_mafia["activa"] = False
    bot.partida_mafia["resultado"] = "Mafia ha ganado"
    
    # Actualización del ranking
    await bot.actualizar_ranking(ctx, "Mafia")
    
    # Verificar que el ranking se ha actualizado correctamente
    assert "Mafia" in bot.ranking
    assert bot.ranking["Mafia"] == 1
