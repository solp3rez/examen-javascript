import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_asignacion_roles():
    """Verifica que los roles se asignen correctamente cuando comienza la partida."""
    ctx = MagicMock()
    ctx.author.id = 1
    ctx.channel = MagicMock()
    
    # Simulación de la creación de partida y asignación de roles
    await bot.crear_partida(ctx, 3)
    await bot.asignar_roles()
    
    # Verificar si se asignaron roles correctamente
    assert len(bot.partida_mafia["roles"]) == 3
    assert "Mafioso" in bot.partida_mafia["roles"].values()
    assert "Ciudadano" in bot.partida_mafia["roles"].values()
