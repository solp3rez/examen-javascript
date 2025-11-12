import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_manejo_fases():
    """Verifica que el bot maneje correctamente las fases del juego."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Fase Día
    bot.partida_mafia["fase"] = "Día"
    await bot.cambiar_fase(ctx)  # Cambia la fase a Noche
    
    # Verificar que la fase cambió a Noche
    assert bot.partida_mafia["fase"] == "Noche"
    assert "La noche cae de nuevo" in ctx.channel.send.call_args[0][0]
    
    # Fase Noche
    bot.partida_mafia["fase"] = "Noche"
    await bot.cambiar_fase(ctx)  # Cambia la fase a Día
    
    # Verificar que la fase cambió a Día
    assert bot.partida_mafia["fase"] == "Día"
    assert "El sol brilla de nuevo" in ctx.channel.send.call_args[0][0]
