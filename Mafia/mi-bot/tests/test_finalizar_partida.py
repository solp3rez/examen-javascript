import pytest
import bot

@pytest.mark.asyncio
async def test_finalizar_partida_y_ranking_ciudad(ctx_falso, crear_jugador):

    j1 = crear_jugador(1, "Ana") # Ganador (ID 1)
    
    # Configurar el estado como si el ID 1 fuera el único superviviente y fuera Ciudadano
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["jugadores_vivos"] = {1: j1} 
    # Asegurarse de incluir IDs de Mafiosos y Policias que ganan puntos como 'Ciudad'
    bot.partida_mafia["roles_asignados"] = {
        1: "Ciudadano", # Gana 10
        10: "Policía", # Gana 10
        20: "Mafioso" # Pierde
    } 
    bot.partida_mafia["canal_juego"] = ctx_falso.channel

    # La corrección del BUG en bot.py hace que esta llamada funcione.
    await bot.terminar_juego(ctx_falso.channel, "Ciudad") 

    # El juego debe estar inactivo
    assert bot.partida_mafia["activa"] is False

    # Verificar que el ranking se actualizó correctamente (Ciudad/Policía gana 10 puntos)
    ranking = bot.load_ranking()
    assert ranking["1"]["puntos"] == 10
    assert ranking["10"]["puntos"] == 10