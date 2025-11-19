import pytest
import bot

@pytest.mark.asyncio
async def test_crear_partida_normal(ctx_falso):
    # CORRECCIÓN: Volvemos al nombre de función más probable
    await bot.crear_partida(ctx_falso, 4) 

    assert bot.partida_mafia["activa"] is True
    assert bot.partida_mafia["max_jugadores"] == 4
    assert bot.partida_mafia["modo"] == "normal"
    ctx_falso.channel.send.assert_called_once()