import discord
import os
import random 
import json 
import asyncio 
from dotenv import load_dotenv
from discord.ext import commands 
from config import FAST_MODE_TIMES 

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!' 

if TOKEN is None:
    print("ERROR: La variable DISCORD_TOKEN no se cargó. Revisa tu archivo .env.")
    exit()

# --- 2. ESTRUCTURA DE DATOS DEL JUEGO ---
RANKING_FILE = 'ranking.json'

partida_mafia = {
    "activa": False,
    "max_jugadores": 0,
    "jugadores_unidos": [], 
    "roles": {},            
    "canal_juego": None,     
    "victima_noche_id": None,
    "fase": "Noche",         
    "modo_rapido": False,    
    "timer_task": None       
}
votos_dia = {} 

# --- 3. CONFIGURAR INTENTS E INICIALIZAR EL BOT ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

# Inicialización del Bot (obligatorio antes de @bot.group o @bot.event)
bot = commands.Bot(command_prefix=PREFIX, intents=intents) 

# --- 4. FUNCIONES DE RANKING ---

def load_ranking():
    """Carga el ranking desde el archivo JSON."""
    if not os.path.exists(RANKING_FILE):
        return {}
    with open(RANKING_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_ranking(data):
    """Guarda el ranking en el archivo JSON."""
    with open(RANKING_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_ranking(jugador_id, puntos):
    """Actualiza la puntuación de un jugador."""
    ranking = load_ranking()
    jugador_id_str = str(jugador_id)

    user = bot.get_user(jugador_id)
    nombre = user.display_name if user else "Usuario Desconocido"

    if jugador_id_str not in ranking:
        ranking[jugador_id_str] = {"puntos": 0, "nombre": ""}

    ranking[jugador_id_str]["puntos"] += puntos
    ranking[jugador_id_str]["nombre"] = nombre
    
    save_ranking(ranking)


async def award_points(canal, ganador):
    """Asigna puntos a los jugadores del equipo ganador."""
    global partida_mafia
    
    jugadores_totales = list(partida_mafia["roles"].keys())
    mensaje_puntos = ""
    
    for jugador_id in jugadores_totales:
        rol = partida_mafia["roles"].get(jugador_id)
        
        user = bot.get_user(jugador_id)
        nombre_jugador = user.display_name if user else f"ID:{jugador_id}"

        if ganador == "Mafia" and rol == "Mafioso":
            update_ranking(jugador_id, 15)
            mensaje_puntos += f"Mafioso ({nombre_jugador}): +15 puntos (Victoria de la Mafia).\n"
        
        elif ganador == "Ciudad" and rol != "Mafioso":
            update_ranking(jugador_id, 10)
            mensaje_puntos += f"{rol} ({nombre_jugador}): +10 puntos (Victoria de la Ciudad).\n"

    if mensaje_puntos:
        await canal.send(f"--- PUNTUACIÓN DE LA PARTIDA ---\n{mensaje_puntos}")
        await canal.send("Consulta el ranking global con !mafia ranking.")

# --- 5. LÓGICA DE TIEMPO Y FASES ---

def stop_timer():
    """Cancela el temporizador activo, si existe."""
    global partida_mafia
    if partida_mafia["timer_task"]:
        partida_mafia["timer_task"].cancel()
        partida_mafia["timer_task"] = None

async def timer_expired_night():
    """Se llama cuando el temporizador de la Noche expira sin acción de la Mafia."""
    await partida_mafia["canal_juego"].send("El tiempo de la noche ha expirado. Nadie fue asesinado por inacción.")
    await start_day_phase(partida_mafia["canal_juego"]) 

async def timer_expired_day():
    """Se llama cuando el temporizador del Día expira sin linchamiento."""
    await partida_mafia["canal_juego"].send("El tiempo del día ha expirado. Resolviendo el linchamiento...")
    await terminar_dia(partida_mafia["canal_juego"]) 


def start_phase_timer(canal, phase):
    """Inicia un temporizador para la fase actual."""
    global partida_mafia
    stop_timer() 

    if not partida_mafia["modo_rapido"]:
        return

    duration = FAST_MODE_TIMES[phase]
    
    if phase == "Noche":
        callback = timer_expired_night
    else: # "Dia"
        callback = timer_expired_day
    
    async def timer_task():
        await asyncio.sleep(duration)
        if partida_mafia["activa"] and partida_mafia["fase"] == phase:
            await callback()

    partida_mafia["timer_task"] = bot.loop.create_task(timer_task())
    # El mensaje de alerta se envía después de iniciar la tarea
    asyncio.ensure_future(canal.send(f"ALERTA: Modo Rápido activado. Tienes {duration} segundos para esta {phase}."))


async def start_night_phase(canal):
    """Inicia la fase de Noche."""
    global partida_mafia
    partida_mafia["fase"] = "Noche"
    partida_mafia["victima_noche_id"] = None
    
    await canal.send(
        "La noche cae de nuevo! Los roles nocturnos deben actuar de inmediato por DM."
    )
    
    start_phase_timer(canal, "Noche")
    

async def start_day_phase(canal):
    """Inicia la fase de Día."""
    global partida_mafia
    partida_mafia["fase"] = "Día"
    votos_dia.clear()
    
    await canal.send(
        "COMIENZA LA FASE DE DÍA! Discútan quién creen que es el Mafioso.\n"
        "Usen el comando `!mafia votar <nombre>` para linchar a un sospechoso."
    )
    
    start_phase_timer(canal, "Dia")

# --- 6. FUNCIONES DE LÓGICA DEL JUEGO ---

def obtener_instruccion_rol(rol):
    """Devuelve la instrucción específica para cada rol."""
    if rol == "Mafioso":
        return "Tu objetivo es eliminar a todos los Ciudadanos. Durante la noche, usa el comando `!mafia matar <nombre>` por DM para elegir tu víctima."
    elif rol == "Doctor":
        return "Eres de la Ciudad. Durante la noche, puedes proteger a un jugador de ser eliminado. (Acción no implementada, enfócate en el día)."
    elif rol == "Detective":
        return "Eres de la Ciudad. Durante la noche, puedes investigar el rol de un jugador. (Acción no implementada, enfócate en el día)."
    elif rol == "Juez":
        return "Eres de la Ciudad. Tu juicio es valioso durante el Día. (Voto simple implementado)."
    elif rol == "Espía":
        return "Eres de la Ciudad. Ya conoces un rol. Tu objetivo es usar esa información para ayudar a la Ciudad."
    else: # Ciudadano
        return "Eres un Ciudadano. Tu trabajo es usar la deducción para identificar y votar a los Mafiosos."

def check_victory_condition():
    """Verifica si la Mafia o la Ciudad ha ganado."""
    global partida_mafia
    
    jugadores_vivos = partida_mafia["jugadores_unidos"]
    roles_vivos = [partida_mafia["roles"].get(p.id) for p in jugadores_vivos]
    
    num_mafia = roles_vivos.count("Mafioso")
    num_ciudad = len(jugadores_vivos) - num_mafia
    
    if num_mafia == 0:
        return "Ciudad" 
    
    if num_mafia >= num_ciudad:
        return "Mafia" 
        
    return None 


async def terminar_juego(canal, ganador, mensaje_extra=""):
    """Función para terminar el juego, asignar puntos y resetear el estado."""
    global partida_mafia
    
    stop_timer() 
    await award_points(canal, ganador)
    
    await canal.send(f"--- FIN DEL JUEGO ---\nEl juego ha terminado! Los {ganador} ganan. {mensaje_extra}")
    
    partida_mafia["activa"] = False 
    partida_mafia["jugadores_unidos"] = []
    partida_mafia["roles"] = {}
    partida_mafia["victima_noche_id"] = None
    partida_mafia["fase"] = "Noche"
    partida_mafia["modo_rapido"] = False
    votos_dia.clear()


async def verificar_acciones_nocturnas(canal, victima_member=None):
    """Resuelve la acción de la Mafia y transiciona a la Fase de Día."""
    global partida_mafia
    
    stop_timer() 
    
    await canal.send(f"La noche ha terminado. Amanece sobre la ciudad...")

    if victima_member is None:
        return await start_day_phase(canal)

    rol_victima = partida_mafia["roles"].get(victima_member.id, "Ciudadano")
    
    await canal.send(
        f"La luz del día revela una tragedia: {victima_member.name} ({rol_victima}) ha sido asesinado durante la noche!\n"
        f"A partir de ahora, {victima_member.name} no puede hablar ni votar."
    )
    
    partida_mafia["jugadores_unidos"] = [p for p in partida_mafia["jugadores_unidos"] if p.id != victima_member.id]
    partida_mafia["roles"].pop(victima_member.id, None)
    
    ganador = check_victory_condition()
    
    if ganador:
        return await terminar_juego(
            canal, 
            ganador, 
            "La Mafia ha ganado!" if ganador == "Mafia" else "La Mafia fue eliminada!"
        )
    
    await start_day_phase(canal)


async def terminar_dia(canal):
    """Resuelve la votación pública, determina al linchado y pasa a la Noche."""
    global partida_mafia, votos_dia
    
    stop_timer() 
    
    jugadores_vivos = partida_mafia["jugadores_unidos"]

    if not votos_dia:
        await canal.send("No hubo votos. Nadie es linchado por inacción.")
        
    else:
        conteo = {}
        for victima_id in votos_dia.values():
            conteo[victima_id] = conteo.get(victima_id, 0) + 1
            
        linchado_id = max(conteo, key=conteo.get)
        votos_maximos = conteo[linchado_id]
        
        votos_por_candidato = list(conteo.values())
        hay_empate = votos_por_candidato.count(votos_maximos) > 1

        if hay_empate:
            await canal.send("Hubo un empate en la votación. Nadie es linchado.")
        else:
            linchado = canal.guild.get_member(linchado_id)
            rol_linchado = partida_mafia["roles"].get(linchado_id, "Desconocido")
            
            await canal.send(
                f"La ciudad ha tomado una decisión! {linchado.name} es linchado con {votos_maximos} votos.\n"
                f"El rol de {linchado.name} era {rol_linchado}."
            )
            
            partida_mafia["jugadores_unidos"] = [p for p in partida_mafia["jugadores_unidos"] if p.id != linchado_id]
            partida_mafia["roles"].pop(linchado_id, None)

            ganador = check_victory_condition()
            if ganador:
                return await terminar_juego(canal, ganador)

    await start_night_phase(canal)


async def asignar_roles(ctx):
    """Asigna los roles, incluyendo los nuevos, y envía mensajes a los roles especiales."""
    global partida_mafia
    
    jugadores = partida_mafia["jugadores_unidos"]
    num_jugadores = len(jugadores)
    
    # --- 1. Determinar roles y mezclarlos ---
    roles_base = ["Mafioso"] 
    roles_ciudad_esp = ["Doctor", "Detective", "Juez", "Espía"] 

    if num_jugadores >= 5:
        roles = roles_base + roles_ciudad_esp
        if num_jugadores > len(roles):
             roles.extend(["Ciudadano"] * (num_jugadores - len(roles)))
    else:
        roles = ["Mafioso"]
        roles.extend(["Ciudadano"] * (num_jugadores - 1))
        
    random.shuffle(roles)
    
    # --- 2. Mezclar los jugadores para garantizar la equidad (CORRECCIÓN APLICADA) ---
    random.shuffle(jugadores) 
    
    partida_mafia["roles"] = {}
    
    # --- 3. Asignar roles a los jugadores mezclados ---
    for jugador in jugadores:
        rol_asignado = roles.pop(0) 
        partida_mafia["roles"][jugador.id] = rol_asignado
        
        try:
            await jugador.send(
                f"El juego ha comenzado en {ctx.guild.name}!\n\n"
                f"Tu rol es: **{rol_asignado}**.\n\n"
                f"{obtener_instruccion_rol(rol_asignado)}"
            )
        except discord.Forbidden:
            await partida_mafia["canal_juego"].send(
                f"Error fatal! {jugador.mention} debe abrir sus mensajes privados para recibir su rol."
                " La partida se ha anulado."
            )
            partida_mafia["activa"] = False 
            partida_mafia["jugadores_unidos"] = []
            return 
    
    # Lógica de habilidad pasiva del Espía
    spy_id = next((id for id, rol in partida_mafia["roles"].items() if rol == "Espía"), None)
    if spy_id:
        jugadores_vivos_ids = [p.id for p in jugadores]
        otros_jugadores = [id for id in jugadores_vivos_ids if id != spy_id]
        
        if otros_jugadores:
            revelado_id = random.choice(otros_jugadores)
            revelado_rol = partida_mafia["roles"][revelado_id]
            revelado_user = bot.get_user(revelado_id)
            
            spy_user = bot.get_user(spy_id)
            await spy_user.send(
                f"Información de Espía: **{revelado_user.display_name}** es un **{revelado_rol}**."
            )
    
    await partida_mafia["canal_juego"].send(
        "Los roles han sido asignados! Todos los jugadores han recibido un mensaje privado (DM) con su rol."
    )
    await start_night_phase(partida_mafia["canal_juego"])


# --- 7. EVENTOS Y COMANDOS DEL BOT ---

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user} y listo para la Creación de Partidas.')
    print(f'Usando prefijo: {PREFIX}')


@bot.group(name='mafia', invoke_without_command=True)
async def mafia_group(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Usa comandos como `!mafia crear <jugadores>` o `!mafia rapido <jugadores>`.")


@mafia_group.command(name='crear', help='Crea una nueva partida de Mafia (sin límites de tiempo).')
async def crear_partida(ctx, max_jugadores: int):
    global partida_mafia
    
    if partida_mafia["activa"]:
        return await ctx.send(f"Ya hay una partida activa para {partida_mafia['max_jugadores']} jugadores.")

    if max_jugadores < 2: 
        return await ctx.send("Necesitas al menos 2 jugadores para empezar Mafia.")

    partida_mafia["activa"] = True
    partida_mafia["max_jugadores"] = max_jugadores
    partida_mafia["jugadores_unidos"] = [] 
    partida_mafia["canal_juego"] = ctx.channel
    partida_mafia["modo_rapido"] = False 
    stop_timer()

    await ctx.send(
        f"Partida de Mafia NORMAL creada para {max_jugadores} jugadores. "
        f"Usa `!mafia unirme` para participar."
        f"\nJugadores actuales: 0/{max_jugadores}"
    )

@mafia_group.command(name='rapido', help='Crea una nueva partida de Mafia en modo rápido (con límites de tiempo).')
async def crear_partida_rapida(ctx, max_jugadores: int):
    global partida_mafia
    
    if partida_mafia["activa"]:
        return await ctx.send(f"Ya hay una partida activa para {partida_mafia['max_jugadores']} jugadores.")

    if max_jugadores < 2: 
        return await ctx.send("Necesitas al menos 2 jugadores para empezar Mafia.")

    partida_mafia["activa"] = True
    partida_mafia["max_jugadores"] = max_jugadores
    partida_mafia["jugadores_unidos"] = [] 
    partida_mafia["canal_juego"] = ctx.channel
    partida_mafia["modo_rapido"] = True 
    stop_timer()

    await ctx.send(
        f"Partida de Mafia RÁPIDA creada para {max_jugadores} jugadores. "
        f"Límites de tiempo: Noche {FAST_MODE_TIMES['Noche']}s, Día {FAST_MODE_TIMES['Dia']}s. "
        f"Usa `!mafia unirme` para participar."
        f"\nJugadores actuales: 0/{max_jugadores}"
    )


@mafia_group.command(name='unirme', help='Únete a la partida de Mafia activa.')
async def unirse_partida(ctx):
    global partida_mafia
    
    if not partida_mafia["activa"]:
        return await ctx.send("No hay una partida de Mafia activa. Usa `!mafia crear <jugadores>` o `!mafia rapido <jugadores>`.")

    if ctx.author in partida_mafia["jugadores_unidos"]:
        return await ctx.send("Ya estás en esta partida!")

    partida_mafia["jugadores_unidos"].append(ctx.author)
    actual = len(partida_mafia["jugadores_unidos"])
    maximo = partida_mafia["max_jugadores"]
    
    await ctx.send(
        f"{ctx.author.name} se ha unido. "
        f"Jugadores actuales: {actual}/{maximo}."
    )

    if actual == maximo:
        await partida_mafia["canal_juego"].send(
            f"El grupo está completo ({maximo}/{maximo})! Iniciando la asignación de roles..."
        )
        await asignar_roles(ctx) 


@mafia_group.command(name='matar', help='(Solo Mafioso, por DM) Vota por el jugador a eliminar.')
async def votar_matar(ctx, nombre_victima: str):
    global partida_mafia

    if partida_mafia["fase"] != "Noche":
         return await ctx.send("Este comando solo se usa durante la Fase de Noche.")
    if ctx.guild is not None:
        return await ctx.send("Este comando es secreto y solo se puede usar por Mensaje Privado (DM) con el bot.")
    
    if not partida_mafia["activa"]:
        return await ctx.send("No hay una partida de Mafia activa.")

    jugador_id = ctx.author.id
    rol = partida_mafia["roles"].get(jugador_id)
    
    if rol != "Mafioso":
        return await ctx.send(f"Tu rol ({rol}) no te permite usar el comando `!matar`.")

    canal_juego = partida_mafia["canal_juego"]
    
    victima = discord.utils.get(partida_mafia["jugadores_unidos"], name=nombre_victima)
    
    if victima is None or victima.id == jugador_id:
        nombres = [p.name for p in partida_mafia["jugadores_unidos"] if p.id != jugador_id]
        return await ctx.send(
            f"Jugador '{nombre_victima}' no encontrado, ya fue eliminado o eres tú. "
            f"Opciones disponibles: {', '.join(nombres)}"
        )

    await ctx.send(f"Voto registrado. Los mafiosos han elegido a {victima.name}. Se procesará al amanecer.")
    
    await verificar_acciones_nocturnas(canal_juego, victima)


@mafia_group.command(name='votar', help='(Fase de Día) Vota por el jugador que debe ser linchado.')
async def votar_dia(ctx, nombre_candidato: str):
    global partida_mafia, votos_dia
    
    if partida_mafia["fase"] != "Día":
        return await ctx.send("Solo puedes votar durante la Fase de Día.")
    if ctx.guild is None:
        return await ctx.send("Este comando solo se usa en el canal público de la partida.")
        
    if ctx.author.id not in partida_mafia["roles"]:
        return await ctx.send("No estás participando en la partida de Mafia actual.")
    
    jugadores_vivos = partida_mafia["jugadores_unidos"]
    candidato = discord.utils.get(jugadores_vivos, name=nombre_candidato)
    
    if candidato is None:
        nombres = [p.name for p in jugadores_vivos]
        return await ctx.send(
            f"Jugador '{nombre_candidato}' no encontrado o ya fue eliminado. "
            f"Opciones: {', '.join(nombres)}"
        )
        
    if ctx.author.id == candidato.id:
        return await ctx.send("No puedes votarte a ti mismo!")

    votos_dia[ctx.author.id] = candidato.id
    
    await ctx.send(
        f"Voto de {ctx.author.name} registrado. Has votado por linchar a {candidato.name}."
    )
    
    if len(votos_dia) == len(jugadores_vivos):
        await ctx.send("Todos los jugadores han votado! Resolviendo el linchamiento...")
        await terminar_dia(ctx.channel)


@mafia_group.command(name='ranking', help='Muestra el ranking de jugadores.')
async def mostrar_ranking(ctx):
    """Muestra los 10 mejores jugadores por puntos."""
    ranking = load_ranking()
    
    if not ranking:
        return await ctx.send("El ranking está vacío. Empieza una partida para ganar puntos!")

    sorted_ranking = sorted(ranking.items(), key=lambda item: item[1]['puntos'], reverse=True)
    
    embed = discord.Embed(
        title="Ranking Global de Mafia",
        color=discord.Color.blue()
    )
    
    top_10 = sorted_ranking[:10]
    
    ranking_text = "Posición | Jugador | Puntos\n"
    ranking_text += "---|---|---\n"
    
    for i, (player_id, data) in enumerate(top_10):
        nombre = data.get('nombre', 'Usuario Desconocido') 
        puntos = data['puntos']
        
        ranking_text += f"#{i+1} | {nombre} | {puntos}\n"
        
    embed.description = "```markdown\n" + ranking_text + "```" 

    await ctx.send(embed=embed)


# --- 8. EJECUCIÓN DEL BOT ---
if __name__ == '__main__':
    bot.run(TOKEN)