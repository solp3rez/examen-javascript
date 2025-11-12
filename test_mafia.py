import pytest
from unittest.mock import AsyncMock, patch
import bot # Importa tu bot.py

# --- Clases de Mock para Simular Discord (Mantenemos estas) ---

class MockMember:
    """Simula un objeto discord.Member."""
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.mention = f"<@{id}>"
        self.display_name = name 
        self.sent_dms = [] 

    async def send(self, content):
        """Simula enviar un DM."""
        self.sent_dms.append(content)
        pass 

class MockContext:
    """Simula un objeto discord.ext.commands.Context."""
    def __init__(self, author_id, channel=None, guild_members=None):
        self._author_id = author_id 
        self.channel = channel if channel else MockChannel()
        self.guild = MockGuild(guild_members)
        self._author = self._find_author(author_id, guild_members) 
        self.valid = True

    def _find_author(self, author_id, guild_members):
        if guild_members:
            return next((m for m in guild_members if m.id == author_id), MockMember(author_id, f"User_{author_id}"))
        return MockMember(author_id, f"User_{author_id}")

    @property
    def author(self):
        return self._author

    @author.setter
    def author(self, member):
        self._author = member

    async def send(self, content):
        """Simula enviar un mensaje al canal del contexto."""
        return self.channel.sent_messages.append(content)

    async def reply(self, content):
        return self.channel.sent_messages.append(f"REPLY: {content}")

class MockChannel:
    """Simula un objeto discord.TextChannel o DMChannel."""
    def __init__(self, guild_members=None):
        self.sent_messages = []
        self._members = guild_members if guild_members is not None else []
        self.name = "mafia-game-channel"

    async def send(self, content):
        """Captura mensajes enviados al canal de juego/DM."""
        self.sent_messages.append(content)
        return AsyncMock()

    @property
    def members(self):
        return self._members

class MockGuild:
    """Simula un objeto discord.Guild."""
    def __init__(self, members=None):
        self.name = "Mafia Test Server"
        self.members = members if members is not None else []
    
    def get_member(self, user_id):
        return next((m for m in self.members if m.id == user_id), None)

# --- Fixture para Limpieza y Mocks Globales (Mantenemos esta) ---

@pytest.fixture
def cleanup_state():
    """Limpia el estado global del bot antes y después de cada test."""
    original_state = {k: v for k, v in bot.partida_mafia.items()}
    original_votos = bot.votos_dia.copy()

    with patch('bot.bot.get_user', side_effect=lambda id: next((m for m in [
        MockMember(10, "Mafia"), MockMember(20, "Citizen"), MockMember(30, "Player3"), 
        MockMember(40, "Player4"), MockMember(50, "ShadowPlayer")
        ] if m.id == id), MockMember(id, f"Player_{id}"))):
        
        yield 

    bot.partida_mafia.update(original_state)
    bot.votos_dia.clear()
    bot.votos_dia.update(original_votos)
    if bot.partida_mafia.get("timer_task"):
        bot.stop_timer()

# --- TESTS ---

# ... Tests 1, 2, 3, 4 (Pasan) ...

@pytest.mark.asyncio
async def test_crear_partida_success(cleanup_state):
    """Verifica que el comando crear_partida inicializa el estado correctamente."""
    ctx = MockContext(author_id=1, channel=MockChannel())
    await bot.crear_partida(ctx, 5)

    assert bot.partida_mafia["activa"] == True
    assert bot.partida_mafia["max_jugadores"] == 5
    assert "Partida de Mafia NORMAL creada" in ctx.channel.sent_messages[0]

@pytest.mark.asyncio
async def test_crear_partida_too_few_players(cleanup_state):
    """Verifica que no se puede crear una partida con menos de 2 jugadores."""
    ctx = MockContext(author_id=1, channel=MockChannel())
    await bot.crear_partida(ctx, 1)

    assert bot.partida_mafia["activa"] == False
    assert "Necesitas al menos 2 jugadores" in ctx.channel.sent_messages[0]

@pytest.mark.asyncio
async def test_unirse_partida_success(cleanup_state):
    """Verifica que un jugador se puede unir y el contador se actualiza."""
    ctx_crear = MockContext(author_id=1, channel=MockChannel())
    await bot.crear_partida(ctx_crear, 3)

    player_id = 10
    ctx_join = MockContext(author_id=player_id, channel=bot.partida_mafia["canal_juego"]) 
    await bot.unirse_partida(ctx_join)

    assert len(bot.partida_mafia["jugadores_unidos"]) == 1
    assert "se ha unido" in ctx_join.channel.sent_messages[-1]

@pytest.mark.asyncio
async def test_unirse_partida_starts_game_when_full(cleanup_state):
    """Verifica que la partida empieza cuando el último jugador se une."""
    
    ctx_crear = MockContext(author_id=1, channel=MockChannel())
    await bot.crear_partida(ctx_crear, 2) 

    p1 = MockMember(id=10, name="Player1") 
    p2 = MockMember(id=20, name="Player2")

    ctx_join1 = MockContext(author_id=10, channel=bot.partida_mafia["canal_juego"])
    ctx_join1.author = p1 
    await bot.unirse_partida(ctx_join1)

    ctx_join2 = MockContext(author_id=20, channel=bot.partida_mafia["canal_juego"])
    ctx_join2.author = p2 
    await bot.unirse_partida(ctx_join2)

    assert len(bot.partida_mafia["jugadores_unidos"]) == 2
    assert "El grupo está completo" in bot.partida_mafia["canal_juego"].sent_messages[-3]
    assert "La noche cae de nuevo" in bot.partida_mafia["canal_juego"].sent_messages[-1]
    assert bot.partida_mafia["fase"] == "Noche"
    assert len(bot.partida_mafia["roles"]) == 2


@pytest.mark.asyncio
async def test_votar_matar_command_guards(cleanup_state):
    """Verifica las guardas del comando !matar (DM, fase, rol)."""
    
    MAFIA_ID = 10
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Día" 
    bot.partida_mafia["roles"] = {MAFIA_ID: "Mafioso", 20: "Ciudadano"}
    
    ctx_dm_fase = MockContext(author_id=MAFIA_ID, channel=MockChannel())
    ctx_dm_fase.guild = None 
    await bot.votar_matar(ctx_dm_fase, "TargetName")
    assert "solo se usa durante la Fase de Noche" in ctx_dm_fase.channel.sent_messages[-1]

    bot.partida_mafia["fase"] = "Noche"
    ctx_server = MockContext(author_id=MAFIA_ID, channel=MockChannel(), guild_members=[MockMember(MAFIA_ID, "Mafia")])
    await bot.votar_matar(ctx_server, "TargetName")
    assert "solo se puede usar por Mensaje Privado" in ctx_server.channel.sent_messages[-1] 

    bot.partida_mafia["fase"] = "Noche"
    bot.partida_mafia["roles"][MAFIA_ID] = "Ciudadano" 
    ctx_dm_rol = MockContext(author_id=MAFIA_ID, channel=MockChannel())
    ctx_dm_rol.guild = None 
    await bot.votar_matar(ctx_dm_rol, "TargetName")
    assert "no te permite usar el comando" in ctx_dm_rol.channel.sent_messages[-1]


@pytest.mark.asyncio
async def test_matar_command_registers_target_and_advances_day(cleanup_state):
    """
    CORREGIDO: Verifica que el Mafioso puede elegir un objetivo por DM y la fase avanza a Día.
    Usamos 4 jugadores (1M vs 3C iniciales) para asegurar que el juego NO termina (queda 1M vs 2C).
    """
    
    # 1. Configurar estado inicial (4 jugadores: 1 Mafia, 3 Ciudadanos)
    MAFIA_ID = 10
    TARGET_ID_1 = 30 # Victima 1 (el que muere)
    TARGET_ID_2 = 40 
    TARGET_ID_3 = 50 
    TARGET_NAME_1 = "Player3"
    
    # 2. Configurar el juego
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Noche"
    bot.partida_mafia["roles"] = {
        MAFIA_ID: "Mafioso",
        TARGET_ID_1: "Ciudadano",
        TARGET_ID_2: "Ciudadano",
        TARGET_ID_3: "Ciudadano"
    }
    
    # 3. Mocks
    mafioso = MockMember(id=MAFIA_ID, name="Mafia")
    target_member_1 = MockMember(id=TARGET_ID_1, name=TARGET_NAME_1)
    target_member_2 = MockMember(id=TARGET_ID_2, name="Player4")
    target_member_3 = MockMember(id=TARGET_ID_3, name="ShadowPlayer")
    guild_members = [mafioso, target_member_1, target_member_2, target_member_3]
    
    mock_canal_juego = MockChannel(guild_members=guild_members)
    
    bot.partida_mafia["canal_juego"] = mock_canal_juego
    bot.partida_mafia["jugadores_unidos"] = [mafioso, target_member_1, target_member_2, target_member_3]
    
    # Simular el contexto DM
    ctx_dm = MockContext(author_id=MAFIA_ID, channel=MockChannel(), guild_members=guild_members)
    ctx_dm.author = mafioso 
    ctx_dm.guild = None 
    
    # La llamada a votar_matar dispara resolver_noche y start_day_phase
    await bot.votar_matar(ctx_dm, TARGET_NAME_1)
    
    # 4. Aserciones
    
    # A) Mensaje de confirmación en el DM del Mafioso
    assert f"Los mafiosos han elegido a {TARGET_NAME_1}. Se procesará al amanecer." in ctx_dm.channel.sent_messages[0]
    
    # B) La fase debe cambiar a Día (El juego NO terminó: 1M vs 2C)
    assert bot.partida_mafia["fase"] == "Día"
    assert target_member_1 not in bot.partida_mafia["jugadores_unidos"]


@pytest.mark.asyncio
async def test_votar_dia_success(cleanup_state):
    """Verifica que un jugador puede votar correctamente en la fase Día."""
    
    VOTER_ID = 10
    CANDIDATE_ID = 20
    CANDIDATE_NAME = "Citizen"
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Día"
    bot.partida_mafia["roles"] = {VOTER_ID: "Ciudadano", CANDIDATE_ID: "Mafioso"}
    
    voter = MockMember(id=VOTER_ID, name="Player1")
    candidate = MockMember(id=CANDIDATE_ID, name=CANDIDATE_NAME)
    guild_members = [voter, candidate]

    mock_canal_juego = MockChannel(guild_members=guild_members)
    bot.partida_mafia["canal_juego"] = mock_canal_juego
    bot.partida_mafia["jugadores_unidos"] = [voter, candidate]

    ctx = MockContext(author_id=VOTER_ID, channel=mock_canal_juego, guild_members=guild_members)
    ctx.author = voter 
    
    await bot.votar_dia(ctx, CANDIDATE_NAME)
    
    assert VOTER_ID in bot.votos_dia
    assert bot.votos_dia[VOTER_ID] == CANDIDATE_ID
    assert "Voto de Player1 registrado" in ctx.channel.sent_messages[-1]


@pytest.mark.asyncio
async def test_votar_dia_city_victory(cleanup_state):
    """
    CORREGIDO: Verifica que linchar al único Mafioso (1M vs 2C) causa la victoria de la Ciudad.
    Este escenario debe terminar el juego.
    """
    
    # 1. Configurar estado (3 jugadores: Ciudadano A, Ciudadano B, Mafioso)
    VOTER_A_ID = 10
    VOTER_B_ID = 30
    MAFIA_ID = 20 # Mafioso, que es linchado
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Día"
    bot.partida_mafia["roles"] = {
        VOTER_A_ID: "Ciudadano", 
        VOTER_B_ID: "Ciudadano", 
        MAFIA_ID: "Mafioso"
    } 
    
    voter_a = MockMember(id=VOTER_A_ID, name="VoterA")
    voter_b = MockMember(id=VOTER_B_ID, name="VoterB")
    mafia = MockMember(id=MAFIA_ID, name="Mafia")
    guild_members = [voter_a, voter_b, mafia]

    mock_canal_juego = MockChannel(guild_members=guild_members)
    bot.partida_mafia["canal_juego"] = mock_canal_juego
    bot.partida_mafia["jugadores_unidos"] = [voter_a, voter_b, mafia]

    # 2. Simular voto unánime para el Mafioso
    bot.votos_dia = {VOTER_A_ID: MAFIA_ID, VOTER_B_ID: MAFIA_ID} 
    
    # Resolver día (debe terminar el juego)
    await bot.terminar_dia(mock_canal_juego)
    
    # 3. Aserciones
    assert bot.partida_mafia["activa"] == False
    assert MAFIA_ID not in bot.partida_mafia["roles"]
    assert "FIN DEL JUEGO" in mock_canal_juego.sent_messages[-3]
    assert "Los **Ciudad** ganan. La Mafia fue linchada!" in mock_canal_juego.sent_messages[-3]


@pytest.mark.asyncio
async def test_mafia_victory_condition_after_kill(cleanup_state):
    """Verifica que la Mafia gana si la proporción de roles es 1M vs 1C (o mejor)."""
    
    MAFIA_ID = 10
    CITIZEN_ID = 20
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Noche"
    bot.partida_mafia["roles"] = {MAFIA_ID: "Mafioso", CITIZEN_ID: "Ciudadano"}
    
    mafioso = MockMember(id=MAFIA_ID, name="Mafia")
    citizen = MockMember(id=CITIZEN_ID, name="Citizen")
    guild_members = [mafioso, citizen]
    
    mock_canal_juego = MockChannel(guild_members=guild_members)
    bot.partida_mafia["canal_juego"] = mock_canal_juego
    bot.partida_mafia["jugadores_unidos"] = [mafioso, citizen]
    
    # Mafioso mata al Ciudadano
    bot.partida_mafia["victima_noche_id"] = CITIZEN_ID 
    await bot.resolver_noche(mock_canal_juego)         
    
    # Aserciones
    assert bot.partida_mafia["activa"] == False
    assert "FIN DEL JUEGO" in mock_canal_juego.sent_messages[-3]
    assert "Los **Mafia** ganan. La Mafia ha ganado!" in mock_canal_juego.sent_messages[-3]


@pytest.mark.asyncio
async def test_city_victory_condition_after_lynch(cleanup_state):
    """Verifica que la Ciudad gana si todos los mafiosos son eliminados (e.g., 0 vs 1)."""
    
    MAFIA_ID = 10
    CITIZEN_ID = 20
    
    bot.partida_mafia["activa"] = True
    bot.partida_mafia["fase"] = "Día"
    bot.partida_mafia["roles"] = {MAFIA_ID: "Mafioso", CITIZEN_ID: "Ciudadano"}
    
    mafioso = MockMember(id=MAFIA_ID, name="Mafia")
    citizen = MockMember(id=CITIZEN_ID, name="Citizen")
    guild_members = [mafioso, citizen]
    
    mock_canal_juego = MockChannel(guild_members=guild_members)
    bot.partida_mafia["canal_juego"] = mock_canal_juego
    bot.partida_mafia["jugadores_unidos"] = [mafioso, citizen]
    
    # Voto unánime para linchar al Mafioso
    bot.votos_dia = {CITIZEN_ID: MAFIA_ID}
    
    # Resolver el día
    await bot.terminar_dia(mock_canal_juego)
    
    # Aserciones
    assert bot.partida_mafia["activa"] == False
    assert "FIN DEL JUEGO" in mock_canal_juego.sent_messages[-3]
    assert "Los **Ciudad** ganan. La Mafia fue linchada!" in mock_canal_juego.sent_messages[-3]