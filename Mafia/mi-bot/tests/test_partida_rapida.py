import pytest
import bot

@pytest.mark.asyncio
async def test_crear_partida_rapida(ctx_falso):
    # Se llama al comando `crear_partida_rapida`
    await bot.crear_partida_rapida(ctx_falso, 4) # Mínimo 4 jugadores

    assert bot.partida_mafia["activa"] is True
    assert bot.partida_mafia["modo"] == "rapido" # Verificación de 'modo'