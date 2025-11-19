import pytest
import bot

@pytest.mark.asyncio
async def test_transicion_noche_a_dia(ctx_falso, crear_jugador):

    j1 = crear_jugador(1, "Ana")
    j2 = crear_jugador(2, "Luis")
    j3 = crear_jugador(3, "Mia")
    j4 = crear_jugador(4, "Leo")


    bot.partida_mafia["jugadores_vivos"] = {1: j1, 2: j2, 3: j3, 4: j4}
    bot.partida_mafia["roles_asignados"] = {1: "Mafioso", 2: "Policía", 3: "Ciudadano", 4: "Ciudadano"}
    
    # Iniciar la fase Noche
    bot.partida_mafia["fase_actual"] = "Noche"
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["canal_juego"] = ctx_falso.channel
    
    # Asignar una víctima para evitar el "Nadie ha muerto"
    bot.partida_mafia["acciones_nocturnas"] = {1: ("matar", 4)} 

    # Llamar al procesador de la fase Noche
    await bot.procesar_noche()

    # Verificar la transición automática de fase
    assert bot.partida_mafia["fase_actual"] == "Día"
    # Verificar que el loop se inicia para el día
    assert bot.partida_loop.is_running()