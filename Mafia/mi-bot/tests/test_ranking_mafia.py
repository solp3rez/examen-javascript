import pytest
import bot

@pytest.mark.asyncio
async def test_ranking_update(bot_falso):

    # Simular que el bot encuentra al usuario 101 y su nombre es "Karen"
    bot.bot.get_user.return_value.name = "Karen"

    bot.update_ranking(101, 10)
    bot.update_ranking(101, 5) # Sumar más puntos

    ranking = bot.load_ranking()

    assert ranking["101"]["puntos"] == 15 # Verificar la suma
    assert ranking["101"]["nombre"] == "Karen"