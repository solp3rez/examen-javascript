import pytest
import bot
from unittest.mock import patch

@pytest.mark.asyncio
async def test_procesar_dia_linchamiento_exitoso(ctx_falso, crear_jugador):
    """Verifica que el jugador más votado sea linchado si tiene mayoría (más de la mitad)."""
    
    j1 = crear_jugador(1, "Mafioso")
    j2 = crear_jugador(2, "Votante1")
    j3 = crear_jugador(3, "Votante2")
    j4 = crear_jugador(4, "Votante3")
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["jugadores_vivos"] = {1: j1, 2: j2, 3: j3, 4: j4}
    bot.partida_mafia["roles_asignados"] = {1: "Mafioso", 2: "Ciudadano", 3: "Ciudadano", 4: "Ciudadano"}
    
    bot.partida_mafia["votos_dia"] = {2: 1, 3: 1, 4: 1}
    bot.partida_mafia["fase_actual"] = "Día"
    bot.partida_mafia["canal_juego"] = ctx_falso.channel
    
    # Limpieza de seguridad: Se debe asumir que el conftest lo hace, pero Pytest/Mock a veces falla
    bot.partida_mafia["jugadores_muertos"] = {} 
    
    with patch('bot.verificar_condicion_victoria', return_value=None):
        await bot.procesar_dia() 
    
    assert 1 not in bot.partida_mafia["jugadores_vivos"]
    assert 1 in bot.partida_mafia["jugadores_muertos"]
    
    assert bot.partida_mafia["fase_actual"] == "Noche" 
    assert bot.partida_mafia["votos_dia"] == {}


@pytest.mark.asyncio
async def test_procesar_dia_sin_mayoria(ctx_falso, crear_jugador):
    """Verifica que nadie sea linchado si no hay mayoría de votos."""
    
    j1 = crear_jugador(1, "Candidato")
    j2 = crear_jugador(2, "Votante1")
    j3 = crear_jugador(3, "Votante2")
    j4 = crear_jugador(4, "Votante3")
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["jugadores_vivos"] = {1: j1, 2: j2, 3: j3, 4: j4}
    bot.partida_mafia["roles_asignados"] = {1: "Mafioso", 2: "Ciudadano", 3: "Ciudadano", 4: "Ciudadano"}
    
    bot.partida_mafia["votos_dia"] = {2: 1, 3: 4}
    bot.partida_mafia["fase_actual"] = "Día"
    bot.partida_mafia["canal_juego"] = ctx_falso.channel

    # CORRECCIÓN: Limpiar la lista de muertos heredada del test anterior.
    # El test anterior (test_procesar_dia_linchamiento_exitoso) mató al jugador ID 1,
    # y el reset entre tests falló al limpiar la clave '1' en jugadores_muertos.
    bot.partida_mafia["jugadores_muertos"] = {}
    
    with patch('bot.verificar_condicion_victoria', return_value=None):
        await bot.procesar_dia()
    
    # Nadie debe estar muerto
    assert len(bot.partida_mafia["jugadores_vivos"]) == 4
    assert bot.partida_mafia["jugadores_muertos"] == {} # Ahora pasa la aserción
    
    assert bot.partida_mafia["fase_actual"] == "Noche"
    assert bot.partida_mafia["votos_dia"] == {}