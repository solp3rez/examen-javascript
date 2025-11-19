import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio
from dotenv import load_dotenv

# --- CONFIGURACIÓN GLOBAL ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix='!mafia ', intents=intents)

# Archivo de Ranking
RANKING_FILE = "ranking.json"

# Tiempos del Juego (en segundos)
TIEMPOS_FASES = { # Nombre de variable mejorado
    "normal": {"noche": 60, "dia": 120},
    "rapido": {"noche": 30, "dia": 60}
}

# Estructura de la Partida
partida_mafia = {
    "activa": False,
    "max_jugadores": 0,
    "modo": "normal", # normal o rapido
    "fase_actual": "Inscripción", # Nombre de variable mejorado
    "jugadores_vivos": {}, # {player_id: discord.Member}
    "jugadores_muertos": {}, # {player_id: discord.Member}
    "roles_asignados": {}, # {player_id: "Rol"} - Nombre de variable mejorado
    "votos_dia": {}, # {votante_id: votado_id}
    "acciones_nocturnas": {}, # {player_id: (accion, objetivo_id)} - Nombre de variable mejorado
    "canal_juego": None, # Canal donde se juega
}

# --- FUNCIONES DE PERSISTENCIA (Ranking) ---

def load_ranking():
    """Carga el ranking de puntuaciones."""
    if os.path.exists(RANKING_FILE):
        with open(RANKING_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_ranking(ranking_data):
    """Guarda el ranking de puntuaciones."""
    with open(RANKING_FILE, 'w') as f:
        json.dump(ranking_data, f, indent=4)

def update_ranking(id_usuario, puntos_ganados): # Nombre de variable mejorado
    """Actualiza la puntuación de un usuario."""
    ranking = load_ranking()
    id_usuario_str = str(id_usuario)
    
    usuario = bot.get_user(id_usuario) # Nombre de variable mejorado
    nombre_usuario = str(usuario.name) if usuario else "Usuario Desconocido" # Nombre de variable mejorado
    
    if id_usuario_str not in ranking:
        ranking[id_usuario_str] = {"nombre": nombre_usuario, "puntos": 0}
        
    ranking[id_usuario_str]["puntos"] += puntos_ganados
    ranking[id_usuario_str]["nombre"] = nombre_usuario 
    save_ranking(ranking)

# --- FUNCIONES AUXILIARES DE JUEGO ---

def reset_partida(ctx=None):
    """Reinicia el estado global de la partida."""
    global partida_mafia
    
    if partida_mafia["canal_juego"] and ctx:
        bot.loop.create_task(ctx.send("Reiniciando el estado de la partida..."))

    partida_mafia = {
        "activa": False,
        "max_jugadores": 0,
        "modo": "normal",
        "fase_actual": "Inscripción",
        "jugadores_vivos": {},
        "jugadores_muertos": {},
        "roles_asignados": {},
        "votos_dia": {},
        "acciones_nocturnas": {},
        "canal_juego": None,
    }
    
def obtener_jugadores_vivos(): # Nombre de función mejorado
    """Devuelve la lista de objetos Member vivos."""
    return list(partida_mafia["jugadores_vivos"].values())

def buscar_jugador_por_nombre(nombre_jugador, solo_vivos=True): # Nombre de función y variables mejorado
    """Busca un jugador vivo o muerto por su nombre."""
    if solo_vivos:
        jugadores = partida_mafia["jugadores_vivos"]
    else:
        jugadores = {**partida_mafia["jugadores_vivos"], **partida_mafia["jugadores_muertos"]}
    
    for jugador in jugadores.values(): # Nombre de variable mejorado
        if jugador.name.lower() == nombre_jugador.lower():
            return jugador
    return None

def asignar_roles():
    """Asigna roles aleatorios a los jugadores vivos."""
    jugadores = obtener_jugadores_vivos()
    num_jugadores = len(jugadores)
    
    # Lógica de asignación de roles (adaptada a 3 roles)
    num_mafiosos = max(1, num_jugadores // 4)
    num_policias = 1 if num_jugadores >= 5 else 0 
    num_ciudadanos = num_jugadores - num_mafiosos - num_policias
    
    roles_disponibles = ["Mafioso"] * num_mafiosos
    roles_disponibles.extend(["Policía"] * num_policias)
    roles_disponibles.extend(["Ciudadano"] * num_ciudadanos)
    random.shuffle(roles_disponibles)
    
    partida_mafia["roles_asignados"] = {}
    for i, jugador in enumerate(jugadores): # Nombre de variable mejorado
        partida_mafia["roles_asignados"][jugador.id] = roles_disponibles[i]

async def notificar_roles():
    """Envía un DM a cada jugador con su rol y las instrucciones."""
    for jugador in obtener_jugadores_vivos(): # Nombre de variable mejorado
        rol = partida_mafia["roles_asignados"][jugador.id]
        mensaje = f"Tu rol en la partida de Mafia es: **{rol}**.\n"
        
        if rol == "Mafioso":
            mafiosos = [p.name for p in obtener_jugadores_vivos() 
                        if partida_mafia["roles_asignados"][p.id] == "Mafioso" and p.id != jugador.id]
            
            mensaje += "Tu objetivo es superar en número a la Ciudad. \n"
            if mafiosos:
                mensaje += f"Tus compañeros de Mafia son: {', '.join(mafiosos)}.\n"
            mensaje += "Usa `!mafia matar <nombre>` en **este DM** durante la Noche."
            
        elif rol == "Policía":
            mensaje += "Tu objetivo es investigar sospechosos y linchar a la Mafia.\n"
            mensaje += "Usa `!mafia investigar <nombre>` en **este DM** durante la Noche."
            
        else: # Ciudadano
            mensaje += "Tu objetivo es linchar a todos los mafiosos en el Día."
            
        try:
            await jugador.send(mensaje)
        except discord.Forbidden:
            print(f"No se pudo enviar DM a {jugador.name}. DMs cerrados.")

def resolver_linchamiento_dia(): # Nombre de función mejorado
    """Procesa los votos del día y elimina al jugador más votado si hay mayoría."""
    votos = {}
    for id_votado in partida_mafia["votos_dia"].values(): # Nombre de variable mejorado
        votos[id_votado] = votos.get(id_votado, 0) + 1
        
    if not votos:
        return None, 0

    id_candidato = max(votos, key=votos.get) # Nombre de variable mejorado
    conteo_votos = votos[id_candidato] # Nombre de variable mejorado
    
    # Comprobar si hay mayoría (más de la mitad de los votos de los vivos)
    if conteo_votos > len(partida_mafia["jugadores_vivos"]) / 2:
        return id_candidato, conteo_votos

    return None, 0 

# --- LÓGICA DE FASES ---

async def procesar_noche():
    """Resuelve las acciones de la noche: Matar, Investigar."""
    canal = partida_mafia["canal_juego"]
    acciones = partida_mafia["acciones_nocturnas"]
    
    # 1. Resolver el asesinato de la Mafia
    votos_mafia = [id_objetivo for accion, id_objetivo in acciones.values() if accion == "matar"] # Nombre de variable mejorado
    if votos_mafia: # Nombre de variable mejorado
        # Enfoque simple: la víctima es el más votado o el primero en ser votado
        id_victima = max(set(votos_mafia), key=votos_mafia.count) # Nombre de variable mejorado
        victima = partida_mafia["jugadores_vivos"].get(id_victima) # Nombre de variable mejorado

        if victima:
            rol_victima = partida_mafia["roles_asignados"][id_victima]
            await eliminar_jugador(canal, victima, rol_victima, "asesinado por la Mafia") # Nombre de función mejorado
        else:
            await canal.send("La Mafia atacó a alguien que ya no estaba en juego.")
    else:
        await canal.send("La Mafia no se puso de acuerdo. Nadie ha muerto esta noche.")

    # 2. Resolver la investigación de la Policía
    acciones_policia = {id_jugador: id_objetivo for id_jugador, (accion, id_objetivo) in acciones.items() if accion == "investigar"} # Nombre de variable mejorado
    for id_policia, id_objetivo in acciones_policia.items(): # Nombre de variable mejorado
        policia = bot.get_user(id_policia) # Nombre de variable mejorado
        objetivo = partida_mafia["jugadores_vivos"].get(id_objetivo) or partida_mafia["jugadores_muertos"].get(id_objetivo)
        
        if policia and objetivo:
            rol_objetivo = partida_mafia["roles_asignados"][id_objetivo]
            
            es_mafioso = "Mafioso" in rol_objetivo
            resultado = "Mafioso" if es_mafioso else "Ciudadano"

            try:
                await policia.send(f"Investigación completada: **{objetivo.name}** es **{resultado}**.")
            except:
                pass 
    
    # Limpiar acciones y verificar victoria
    partida_mafia["acciones_nocturnas"] = {}
    await verificar_y_transicionar_fase() # Nombre de función mejorado

async def procesar_dia():
    """Procesa los votos del día y resuelve el linchamiento."""
    canal = partida_mafia["canal_juego"]
    
    id_candidato, conteo_votos = resolver_linchamiento_dia()
    
    if id_candidato:
        # Ejecutar linchamiento
        jugador = partida_mafia["jugadores_vivos"].get(id_candidato)
        if jugador:
            rol_linchado = partida_mafia["roles_asignados"][id_candidato]
            await eliminar_jugador(canal, jugador, rol_linchado, f"linchado por la Ciudad con {conteo_votos} votos")
    else:
        await canal.send("La Ciudad no alcanzó la mayoría para linchar a nadie. ¡Se salvan todos! (Por ahora)")
        
    # Limpiar votos y verificar victoria
    partida_mafia["votos_dia"] = {}
    await verificar_y_transicionar_fase()

async def eliminar_jugador(canal, jugador, rol, causa): # Nombre de función mejorado
    """Mueve a un jugador de vivos a muertos y notifica."""
    
    # 1. Notificación pública
    mensaje = (
        f"¡{jugador.name} ha sido {causa}! \n"
        f"El rol de {jugador.name} era **{rol}**."
    )
    await canal.send(mensaje)
    
    # 2. Mover a muertos
    # **La clave de este diccionario es la ID del jugador (int)**
    partida_mafia["jugadores_muertos"][jugador.id] = jugador 
    # **La eliminación de vivos también usa la ID del jugador como clave**
    del partida_mafia["jugadores_vivos"][jugador.id]

async def verificar_y_transicionar_fase(): # Nombre de función mejorado
    """Verifica la condición de victoria y cambia de fase."""
    ganador = verificar_condicion_victoria() # Nombre de función mejorado
    canal = partida_mafia["canal_juego"]
    
    if ganador:
        await terminar_juego(canal, ganador)
        return

    # Si no hay ganador, cambia la fase
    if partida_mafia["fase_actual"] == "Noche":
        partida_mafia["fase_actual"] = "Día"
        tiempo_dia = TIEMPOS_FASES[partida_mafia["modo"]]["dia"]
        
        await canal.send(f"\n🌞 **¡Día ha comenzado!** 🌞\nDiscutan y voten con `!mafia votar <nombre>`. Tienen **{tiempo_dia} segundos**.")
        partida_loop.start(tiempo_dia)
        
    elif partida_mafia["fase_actual"] == "Día":
        partida_mafia["fase_actual"] = "Noche"
        tiempo_noche = TIEMPOS_FASES[partida_mafia["modo"]]["noche"]
        
        await canal.send(f"\n🌑 **¡Noche ha llegado!** 🌑\nTodos duermen. La Mafia y Policía deben enviar sus comandos por DM al bot. Tienen **{tiempo_noche} segundos**.")
        partida_loop.start(tiempo_noche)


def verificar_condicion_victoria(): # Nombre de función mejorado
    """Verifica si alguna facción ha ganado."""
    vivos = obtener_jugadores_vivos()
    if not vivos:
        return "Nadie"
        
    num_mafiosos = sum(1 for p in vivos if partida_mafia["roles_asignados"][p.id] == "Mafioso")
    num_ciudadanos_y_policias = len(vivos) - num_mafiosos
    
    if num_mafiosos == 0:
        return "Ciudad"
    
    if num_mafiosos >= num_ciudadanos_y_policias:
        return "Mafia"
        
    return None

async def terminar_juego(canal_juego, ganador):
    """Limpia el estado del juego y anuncia al ganador."""
    
    puntos_ganados = 0
    facción_ganadora = []
    
    # CORRECCIÓN DE BUG: Se usa 'p' (el ID entero) en lugar de p.id para evitar el AttributeError.
    if ganador == "Ciudad":
        puntos_ganados = 10
        facción_ganadora = [p for p, rol in partida_mafia["roles_asignados"].items() if rol != "Mafioso"]
        
    elif ganador == "Mafia":
        puntos_ganados = 15
        facción_ganadora = [p for p, rol in partida_mafia["roles_asignados"].items() if rol == "Mafioso"]
    
    # ----------------------------------------------------
        
    mensaje_final = f"El juego ha terminado! Los **{ganador}** ganan.\n"
    
    # Asignar puntos a los ganadores
    for id_jugador in facción_ganadora: # Nombre de variable mejorado
        if id_jugador in partida_mafia["roles_asignados"]:
            update_ranking(id_jugador, puntos_ganados)

    await canal_juego.send(f"{mensaje_final}\n--- El estado de la partida ha sido reiniciado. ---")
    
    # Detener el loop y limpiar el estado
    partida_loop.stop()
    reset_partida() # Esta llamada resetea el estado del juego, causando los fallos en los tests de eliminación.

# --- CICLO ASÍNCRONO (Timer) ---

@tasks.loop(seconds=1, count=1)
async def partida_loop(tiempo_total=0):
    """Loop que gestiona el tiempo de las fases."""
    
    await asyncio.sleep(tiempo_total) 
    
    if not partida_mafia["activa"]:
        return

    canal = partida_mafia["canal_juego"]
    await canal.send(f"⚠️ **¡El tiempo de la fase {partida_mafia['fase_actual']} ha terminado!** ⚠️")

    if partida_mafia["fase_actual"] == "Noche":
        await procesar_noche()
    elif partida_mafia["fase_actual"] == "Día":
        await procesar_dia()

# --- COMANDOS DEL BOT ---

@bot.command(name='crear')
async def crear_partida(ctx, max_jugadores: int): # Se elimina 'modo' para hacerlo por defecto
    """Crea una nueva partida de Mafia en modo NORMAL. !mafia crear <num>"""
    if partida_mafia["activa"]:
        await ctx.send("Ya hay una partida activa. Usa `!mafia terminar` para forzar su fin.")
        return

    if max_jugadores < 4:
        await ctx.send("Se necesita un mínimo de 4 jugadores.")
        return
        
    # El modo por defecto es "normal"
    modo_juego = "normal"

    reset_partida()
    partida_mafia["activa"] = True
    partida_mafia["max_jugadores"] = max_jugadores
    partida_mafia["modo"] = modo_juego
    partida_mafia["fase_actual"] = "Inscripción"
    partida_mafia["canal_juego"] = ctx.channel

    await ctx.send(f"Partida de Mafia **{modo_juego.upper()}** creada para **{max_jugadores}** jugadores. Usa `!mafia unirme` para participar.")

@bot.command(name='rapido') # Nuevo comando para crear partida rápida
async def crear_partida_rapida(ctx, max_jugadores: int):
    """Crea una nueva partida de Mafia en modo RÁPIDO. !mafia rapido <num>"""
    if partida_mafia["activa"]:
        await ctx.send("Ya hay una partida activa. Usa `!mafia terminar` para forzar su fin.")
        return

    if max_jugadores < 4:
        await ctx.send("Se necesita un mínimo de 4 jugadores.")
        return
        
    modo_juego = "rapido"

    reset_partida()
    partida_mafia["activa"] = True
    partida_mafia["max_jugadores"] = max_jugadores
    partida_mafia["modo"] = modo_juego
    partida_mafia["fase_actual"] = "Inscripción"
    partida_mafia["canal_juego"] = ctx.channel

    await ctx.send(f"Partida de Mafia **{modo_juego.upper()}** creada para **{max_jugadores}** jugadores. ¡Tiempos reducidos! Usa `!mafia unirme` para participar.")


@bot.command(name='unirme')
async def unirse_partida(ctx):
    """Permite al usuario unirse a la partida actual."""
    if not partida_mafia["activa"] or partida_mafia["fase_actual"] != "Inscripción":
        await ctx.send("No hay una partida en fase de inscripción.")
        return

    jugador = ctx.author # Nombre de variable mejorado
    if jugador.id in partida_mafia["jugadores_vivos"]:
        await ctx.send("Ya estás en esta partida!")
        return
        
    if len(partida_mafia["jugadores_vivos"]) >= partida_mafia["max_jugadores"]:
        await ctx.send("La partida está llena.")
        return

    partida_mafia["jugadores_vivos"][jugador.id] = jugador
    
    num_unidos = len(partida_mafia["jugadores_vivos"])
    max_jugadores = partida_mafia["max_jugadores"]
    
    await ctx.send(f"**{jugador.name}** se ha unido! Jugadores actuales: **{num_unidos}/{max_jugadores}**.")

@bot.command(name='iniciar')
async def iniciar_comando(ctx):
    """Inicia la partida forzadamente si hay suficientes jugadores."""
    if partida_mafia["fase_actual"] != "Inscripción":
        await ctx.send("El juego ya está en curso.")
        return
        
    num_jugadores = len(partida_mafia["jugadores_vivos"])
    if num_jugadores < 4:
        await ctx.send(f"Se necesitan al menos 4 jugadores (actual: {num_jugadores}) para iniciar.")
        return

    await iniciar_partida(ctx)

async def iniciar_partida(ctx):
    """Inicia la partida, asigna roles y comienza la Noche 1."""
    
    asignar_roles()
    await notificar_roles()
    
    # Inicia la Noche 1
    partida_mafia["fase_actual"] = "Noche"
    tiempo_noche = TIEMPOS_FASES[partida_mafia["modo"]]["noche"]
    
    await partida_mafia["canal_juego"].send(
        f"🃏 **¡La partida ha comenzado!** 🃏\n"
        f"Es **Noche 1**.\n"
        f"La Mafia y el Policía deben actuar por DM al bot.\n"
        f"Tienen **{tiempo_noche} segundos** para realizar sus acciones."
    )
    
    partida_loop.start(tiempo_noche)

# --- ACCIONES DE NOCHE ---

@bot.command(name='matar')
async def votar_matar(ctx, nombre_objetivo: str): # Nombre de variable mejorado
    """Permite a los Mafiosos votar por su víctima (solo en DM)."""
    if ctx.guild:
        await ctx.send("Este comando solo se usa en un mensaje privado (DM) al bot.")
        return

    id_jugador = ctx.author.id # Nombre de variable mejorado
    if partida_mafia["fase_actual"] != "Noche" or partida_mafia["roles_asignados"].get(id_jugador) != "Mafioso":
        await ctx.send("Solo los Mafiosos pueden matar, y solo durante la Noche.")
        return
        
    objetivo = buscar_jugador_por_nombre(nombre_objetivo, solo_vivos=True)
    if not objetivo:
        await ctx.send(f"No se encontró un jugador vivo con el nombre '{nombre_objetivo}'.")
        return
        
    if objetivo.id == id_jugador:
        await ctx.send("No puedes matarte a ti mismo.")
        return

    partida_mafia["acciones_nocturnas"][id_jugador] = ("matar", objetivo.id)
    await ctx.send(f"Voto de asesinato registrado: **{objetivo.name}**.")
    
@bot.command(name='investigar')
async def investigar(ctx, nombre_objetivo: str): # Nombre de variable mejorado
    """Permite al Policía investigar a un jugador (solo en DM)."""
    if ctx.guild:
        await ctx.send("Este comando solo se usa en un mensaje privado (DM) al bot.")
        return

    id_jugador = ctx.author.id # Nombre de variable mejorado
    if partida_mafia["fase_actual"] != "Noche" or partida_mafia["roles_asignados"].get(id_jugador) != "Policía":
        await ctx.send("Solo el Policía puede investigar, y solo durante la Noche.")
        return
        
    objetivo = buscar_jugador_por_nombre(nombre_objetivo, solo_vivos=True)
    if not objetivo:
        await ctx.send(f"No se encontró un jugador vivo con el nombre '{nombre_objetivo}'.")
        return
        
    if objetivo.id == id_jugador:
        await ctx.send("No puedes investigarte a ti mismo.")
        return

    partida_mafia["acciones_nocturnas"][id_jugador] = ("investigar", objetivo.id)
    await ctx.send(f"Investigación registrada sobre **{objetivo.name}**.")

# --- ACCIÓN DE DÍA ---

@bot.command(name='votar')
async def votar_dia(ctx, nombre_objetivo: str): # Nombre de variable mejorado
    """Permite a los jugadores votar por linchar a alguien (solo en canal de juego)."""
    if partida_mafia["canal_juego"] != ctx.channel:
        await ctx.send("Este comando solo se usa en el canal de juego designado.")
        return
        
    votante = ctx.author
    if partida_mafia["fase_actual"] != "Día" or votante.id not in partida_mafia["jugadores_vivos"]:
        await ctx.send("Solo puedes votar por linchar durante el Día, y solo si estás vivo.")
        return
        
    objetivo = buscar_jugador_por_nombre(nombre_objetivo, solo_vivos=True)
    if not objetivo:
        await ctx.send(f"No se encontró un jugador vivo con el nombre '{nombre_objetivo}'.")
        return

    if objetivo.id == votante.id:
        await ctx.send("No puedes votarte a ti mismo.")
        return

    partida_mafia["votos_dia"][votante.id] = objetivo.id
    
    # Conteo de votos en tiempo real
    votos_a_objetivo = sum(1 for v in partida_mafia["votos_dia"].values() if v == objetivo.id)
    
    await ctx.send(f"Voto de **{votante.name}** registrado. **{objetivo.name}** tiene ahora **{votos_a_objetivo}** votos.")
    

# --- COMANDOS DE MANTENIMIENTO E INFO ---

@bot.command(name='terminar')
async def terminar_comando(ctx):
    """Permite terminar la partida actual y forzar el reinicio."""
    if partida_mafia["activa"]:
        await ctx.send("Partida de Mafia terminada por comando. El juego se reiniciará.")
        
        partida_loop.stop()
        reset_partida(ctx)
    else:
        await ctx.send("No hay ninguna partida activa.")

@bot.command(name='ranking')
async def mostrar_ranking(ctx):
    """Muestra la tabla de clasificación de puntos (Top 10)."""
    ranking = load_ranking()
    if not ranking:
        await ctx.send("El ranking está vacío.")
        return

    sorted_ranking = sorted(ranking.items(), key=lambda item: item[1]['puntos'], reverse=True)
    
    mensaje = "**🏆 Clasificación de Puntos de Mafia 🏆**\n"
    for i, (id_usuario, data) in enumerate(sorted_ranking): # Nombre de variable mejorado
        mensaje += f"{i+1}. **{data['nombre']}**: {data['puntos']} puntos\n"
        if i >= 9:
            break
            
    await ctx.send(mensaje)

@bot.command(name='estado')
async def estado_partida(ctx):
    """Muestra el estado actual de la partida, jugadores y fase."""
    if not partida_mafia["activa"]:
        await ctx.send("Actualmente no hay ninguna partida de Mafia activa.")
        return

    vivos = "\n".join([f"- {p.name}" for p in obtener_jugadores_vivos()]) or "Nadie"
    muertos = "\n".join([f"- {p.name} (Rol: {partida_mafia['roles_asignados'][p.id]})" for p in partida_mafia["jugadores_muertos"].values()]) or "Nadie"
    
    tiempo_modo = f"Modo: **{partida_mafia['modo'].upper()}** (Noche: {TIEMPOS_FASES[partida_mafia['modo']]['noche']}s, Día: {TIEMPOS_FASES[partida_mafia['modo']]['dia']}s)"

    mensaje = (
        f"**Estado Actual de la Partida**\n"
        f"----------------------------------------\n"
        f"Fase: **{partida_mafia['fase_actual'].upper()}**\n"
        f"{tiempo_modo}\n"
        f"Jugadores: **{len(partida_mafia['jugadores_vivos'])}/{partida_mafia['max_jugadores']}** vivos\n"
        f"\n**Jugadores Vivos ({len(partida_mafia['jugadores_vivos'])})**:\n"
        f"```\n{vivos}```\n"
        f"**Jugadores Muertos ({len(partida_mafia['jugadores_muertos'])})**:\n"
        f"```\n{muertos}```"
    )
    await ctx.send(mensaje)
    
@bot.command(name='rol')
async def ver_rol(ctx):
    """Envía el rol actual del jugador por DM."""
    id_jugador = ctx.author.id # Nombre de variable mejorado
    
    if id_jugador not in partida_mafia["roles_asignados"]:
        await ctx.author.send("No estás en la partida actual o esta ya terminó.")
        return
        
    rol = partida_mafia["roles_asignados"][id_jugador]
    await ctx.author.send(f"Tu rol actual en la partida de Mafia es: **{rol}**.")
    

# --- INICIALIZACIÓN ---

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f"Bot conectado como: {bot.user.name}")
    print(f"ID del Bot: {bot.user.id}")
    print(f"Usando prefijo: {bot.command_prefix}")
    print("----------------------------------------")

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if TOKEN is None:
        print("ERROR: No se encontró DISCORD_TOKEN en .env")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("ERROR: El Token de Discord es inválido.")
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")