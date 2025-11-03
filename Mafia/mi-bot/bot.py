import discord
import os
import random 
from dotenv import load_dotenv
from discord.ext import commands 

# --- 1. Configuración de Seguridad y Carga de Token ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!' 

if TOKEN is None:
    print("❌ ERROR: La variable DISCORD_TOKEN no se cargó. Revisa tu archivo .env.")
    exit()

# --- 2. Estructura de Datos del Juego ---
partida_mafia = {
    "activa": False,
    "max_jugadores": 0,
    "jugadores_unidos": [], # Lista de objetos Member
    "roles": {},            # {ID_Jugador: "Rol Asignado", ...}
    "canal_juego": None,     
    "victima_noche_id": None # Nuevo campo para guardar el objetivo de la Mafia
}

# --- 3. Configurar Intents y Bot ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# --- Evento de Conexión ---
@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user} y listo para la Creación de Partidas.')
    print(f'Usando prefijo: {PREFIX}')


# --- FUNCIONES DE LÓGICA DEL JUEGO ---

def obtener_instruccion_rol(rol):
    """Devuelve la instrucción específica para cada rol."""
    if rol == "Mafioso":
        return "🔪 Durante la noche, usa el comando `!mafia matar <nombre>` por DM para eliminar a alguien."
    elif rol == "Doctor":
        return "💉 Durante la noche, puedes proteger a un jugador de ser eliminado."
    elif rol == "Detective":
        return "🔍 Durante la noche, puedes investigar el rol de un jugador."
    else: # Ciudadano
        return "😴 Eres un **Ciudadano**. Tu trabajo es usar la deducción para identificar y votar a los Mafiosos."

async def terminar_juego(canal, mensaje):
    """Función para terminar el juego y resetear el estado."""
    global partida_mafia
    
    await canal.send(f"--- 📣 **FIN DEL JUEGO** 📣 ---\n{mensaje}")
    
    # Reseteamos el estado del juego
    partida_mafia["activa"] = False 
    partida_mafia["jugadores_unidos"] = []
    partida_mafia["roles"] = {}
    partida_mafia["victima_noche_id"] = None


async def verificar_acciones_nocturnas(canal, victima_member):
    """Verifica si todos los Mafiosos han votado y resuelve la noche."""
    
    # 1. Anunciar que la noche ha terminado (Amanece)
    await canal.send(f"🔪 **La noche ha terminado.** Amanece sobre la ciudad...")
    
    # 2. Resolución de la noche (En el juego de 2, la Mafia gana inmediatamente)
    
    # Buscamos quién fue el Mafioso (el que votó) para el mensaje final
    mafioso_id = [uid for uid, rol in partida_mafia["roles"].items() if rol == "Mafioso"][0]
    mafioso = canal.guild.get_member(mafioso_id)
        
    await terminar_juego(
        canal,
        f"☀️ La luz del día revela una tragedia: ¡**{victima_member.name}** ha sido asesinado!\n"
        f"👑 ¡La **Mafia** ha ganado! {mafioso.mention} era el Mafioso y ha tomado el control de la ciudad."
    )
        

async def asignar_roles(ctx):
    global partida_mafia
    
    jugadores = partida_mafia["jugadores_unidos"]
    num_jugadores = len(jugadores)
    
    # --- LÓGICA DE ASIGNACIÓN ---
    if num_jugadores <= 3:
        num_mafiosos = 1
        roles = ["Mafioso"] * num_mafiosos
        roles.extend(["Ciudadano"] * (num_jugadores - num_mafiosos))
    else:
        num_mafiosos = 1
        roles = ["Mafioso"] * num_mafiosos + ["Doctor", "Detective"]
        
        if num_jugadores > len(roles):
             roles.extend(["Ciudadano"] * (num_jugadores - len(roles)))

    random.shuffle(roles)
    partida_mafia["roles"] = {}
    
    for i, jugador in enumerate(jugadores):
        rol_asignado = roles[i]
        partida_mafia["roles"][jugador.id] = rol_asignado
        
        # Enviar Mensaje Privado (DM) con su rol
        try:
            await jugador.send(
                f"🎉 **¡El juego ha comenzado en {ctx.guild.name}!**\n\n"
                f"👑 Tu rol es: **{rol_asignado}**.\n\n"
                f"{obtener_instruccion_rol(rol_asignado)}"
            )
        except discord.Forbidden:
            await partida_mafia["canal_juego"].send(
                f"⚠️ ¡Error fatal! {jugador.mention} debe abrir sus mensajes privados para recibir su rol."
                " La partida se ha anulado."
            )
            partida_mafia["activa"] = False 
            partida_mafia["jugadores_unidos"] = []
            return 
    
    # Anuncio de inicio en el canal público
    await partida_mafia["canal_juego"].send(
        "🔮 **¡Los roles han sido asignados!** Todos los jugadores han recibido un mensaje privado (DM) con su rol."
        "\n🌙 **Comienza la Fase de Noche.** El bot moderará las acciones secretas."
    )


# --- COMANDOS ---

@bot.group(name='mafia', invoke_without_command=True)
async def mafia_group(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Usa comandos como `!mafia crear <jugadores>` o `!mafia unirme`.")


@mafia_group.command(name='crear', help='Crea una nueva partida de Mafia.')
async def crear_partida(ctx, max_jugadores: int):
    global partida_mafia
    
    if partida_mafia["activa"]:
        return await ctx.send(f"❌ Ya hay una partida activa para {partida_mafia['max_jugadores']} jugadores.")

    # Mínimo de 2 Jugadores
    if max_jugadores < 2: 
        return await ctx.send("❌ Necesitas al menos 2 jugadores para empezar Mafia.")

    partida_mafia["activa"] = True
    partida_mafia["max_jugadores"] = max_jugadores
    partida_mafia["jugadores_unidos"] = [] 
    partida_mafia["canal_juego"] = ctx.channel

    await ctx.send(
        f"✅ **Partida de Mafia creada** para **{max_jugadores}** jugadores. "
        f"Usa `!mafia unirme` para participar."
        f"\nJugadores actuales: 0/{max_jugadores}"
    )


@mafia_group.command(name='unirme', help='Únete a la partida de Mafia activa.')
async def unirse_partida(ctx):
    global partida_mafia
    
    if not partida_mafia["activa"]:
        return await ctx.send("❌ No hay una partida de Mafia activa. Usa `!mafia crear <jugadores>`.")

    if ctx.author in partida_mafia["jugadores_unidos"]:
        return await ctx.send("❌ ¡Ya estás en esta partida!")

    # Unir al jugador
    partida_mafia["jugadores_unidos"].append(ctx.author)
    actual = len(partida_mafia["jugadores_unidos"])
    maximo = partida_mafia["max_jugadores"]
    
    await ctx.send(
        f"✅ **{ctx.author.name}** se ha unido. "
        f"Jugadores actuales: **{actual}/{maximo}**."
    )

    # Llama a la función de asignación de roles cuando el cupo esté completo
    if actual == maximo:
        await partida_mafia["canal_juego"].send(
            f"🎉 **¡El grupo está completo ({maximo}/{maximo})!** Iniciando la asignación de roles..."
        )
        await asignar_roles(ctx) 


@mafia_group.command(name='matar', help='(Solo Mafioso, por DM) Vota por el jugador a eliminar.')
async def votar_matar(ctx, nombre_victima: str):
    global partida_mafia

    # 1. Verificar que el comando se use en DM (es un voto secreto)
    if ctx.guild is not None:
        return await ctx.send("❌ Este comando es secreto y solo se puede usar por **Mensaje Privado (DM)** con el bot.")
    
    # 2. Verificar que haya partida activa
    if not partida_mafia["activa"]:
        return await ctx.send("❌ No hay una partida de Mafia activa.")

    jugador_id = ctx.author.id
    rol = partida_mafia["roles"].get(jugador_id)
    
    # 3. Verificar que el usuario sea Mafioso
    if rol != "Mafioso":
        return await ctx.send(f"❌ Tu rol ({rol}) no te permite usar el comando `!matar`.")

    # 4. Encontrar a la víctima
    # Necesitamos acceder al servidor para buscar por nombre (solo es posible si el bot está en el servidor)
    canal_juego = partida_mafia["canal_juego"]
    servidor = canal_juego.guild
    
    # Buscamos a la víctima entre los jugadores de la partida (excluyendo al Mafioso)
    jugadores_disponibles = [p for p in partida_mafia["jugadores_unidos"] if p.id != jugador_id]

    victima = discord.utils.get(jugadores_disponibles, name=nombre_victima)
    
    if victima is None:
        nombres = [p.name for p in jugadores_disponibles]
        return await ctx.send(
            f"❌ Jugador '{nombre_victima}' no encontrado. "
            f"Opciones disponibles: {', '.join(nombres)}"
        )

    # 5. Notificar al Mafioso y ANUNCIAR el procesamiento (cumpliendo el caso de uso)
    await ctx.send(f"✅ Voto registrado. Los mafiosos han elegido a **{victima.name}**. Se procesará al amanecer.")
    
    # 6. Resolver la noche inmediatamente para la prueba de 2 jugadores
    await verificar_acciones_nocturnas(canal_juego, victima)


# --- 5. Ejecutar el Bot ---
bot.run(TOKEN)