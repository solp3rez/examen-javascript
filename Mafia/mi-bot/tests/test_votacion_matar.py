import pytest
import bot
from unittest.mock import patch # Importación necesaria

@pytest.mark.asyncio
async def test_matar_jugador(ctx_falso, crear_jugador):

    mafioso = crear_jugador(1, "Mafioso")
    victima = crear_jugador(2, "Victima")
    tercer_jugador = crear_jugador(3, "Tercero") # Añadimos un tercer jugador
    
    # Usando la estructura de diccionario de IDs y los nombres de variables correctos
    bot.partida_mafia["jugadores_vivos"] = {1: mafioso, 2: victima, 3: tercer_jugador}
    bot.partida_mafia["roles_asignados"] = {1: "Mafioso", 2: "Ciudadano", 3: "Ciudadano"}
    
    # Simular la acción de matar de la Mafia (usando la nueva estructura)
    bot.partida_mafia["acciones_nocturnas"] = {1: ("matar", 2)} 
    
    bot.partida_mafia["canal_juego"] = ctx_falso.channel
    bot.partida_mafia["fase_actual"] = "Noche" # Nombre de fase corregido

    # CORRECCIÓN CRÍTICA: MOCK la función de victoria para que no se resetee el estado
    with patch('bot.verificar_condicion_victoria', return_value=None):
        # La función fue renombrada de resolver_noche a procesar_noche
        await bot.procesar_noche() 

    # La víctima (ID 2) NO debe estar en jugadores_vivos
    assert 2 not in bot.partida_mafia["jugadores_vivos"]
    # La víctima (ID 2) SÍ debe estar en jugadores_muertos (pasa gracias al patch)
    assert 2 in bot.partida_mafia["jugadores_muertos"]
    # El tercer jugador (ID 3) y el Mafioso (ID 1) deben seguir vivos
    assert 3 in bot.partida_mafia["jugadores_vivos"]
    assert 1 in bot.partida_mafia["jugadores_vivos"]