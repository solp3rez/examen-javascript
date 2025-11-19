import pytest
import bot

@pytest.mark.asyncio
async def test_asignacion_roles(crear_jugador, ctx_falso):

    # Crear jugadores (mínimo 4 para asegurar Mafioso y Policía)
    j1 = crear_jugador(1, "Ana")
    j2 = crear_jugador(2, "Luis")
    j3 = crear_jugador(3, "Mia")
    j4 = crear_jugador(4, "Leo")

    bot.partida_mafia["jugadores_vivos"] = {
        1: j1, 2: j2, 3: j3, 4: j4
    }

    bot.asignar_roles()

    assert len(bot.partida_mafia["roles_asignados"]) == 4
    # Debe haber al menos un Mafioso y un Policía/Ciudadano
    roles = bot.partida_mafia["roles_asignados"].values()
    assert any(r == "Mafioso" for r in roles)
    assert sum(1 for r in roles if r == "Policía") <= 1 # Máximo 1 policía en 4 jugadores