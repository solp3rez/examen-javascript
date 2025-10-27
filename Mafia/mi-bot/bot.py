import discord
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Token del bot
TOKEN = 'TU_TOKEN_AQUI'  # Sustituye con tu token real

# Crear cliente
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event 
async def on_ready():
    print(f'✅ Bot conectado como {client.user}')

@client.event 
async def on_message(message):
    if message.author == client.user:
        return    

    # Responde a un saludo
    if message.content.lower() == 'hola':
        await message.channel.send('¡Hola! Soy un bot hecho en Python. 🤖')

    # Asigna un rol a quien use el comando 'asignar rol'
    if message.content.lower() == 'asignar rol':
        # Obtén el rol llamado "Administrador" o el que desees
        role = discord.utils.get(message.guild.roles, name="Administrador")  # Aquí puedes cambiar el nombre del rol

        # Si el rol existe, asignarlo al usuario
        if role:
            await message.author.add_roles(role)
            await message.channel.send(f"Te asigné el rol {role.name}. 🎉")
        else:
            await message.channel.send("No encontré el rol 'Administrador' en este servidor. ❌")

# Ejecuta el bot
client.run(TOKEN)
