# bot_discord/bot.py

import discord
from discord.ext import commands
from django.conf import settings
from together import Together

from asgiref.sync import sync_to_async


from bot_discord.models import Mensaje, CanalHabilitado

import logging
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Inicializa la clave API de Together desde las configuraciones
client = Together(api_key=settings.TOGETHERAI_API_KEY)

# Conjunto para almacenar los IDs de los canales habilitados
canales_habilitados = set()

mensaje_bienvenida = (
    "¡Hola! Soy **CuleBot**, tu asistente de inteligencia artificial y aficionado del FC Barcelona. "
    "Estoy aquí para ayudarte y mantener la conversación animada. ¿En qué puedo ayudarte hoy?"
)

# Mensaje de configuración para la IA
mensaje_configuracion = {
    "role": "system",
    "content": (
        "Eres **CuleBot**, un bot de Discord con inteligencia artificial y apasionado seguidor del FC Barcelona. "
        "Tu objetivo es ayudar a los usuarios respondiendo sus preguntas, proporcionando información útil "
        "y manteniendo siempre un tono positivo y entusiasta. Interactúas en un chat de Discord, comprendiendo "
        "los mensajes de los usuarios y respondiendo de manera natural. Puedes utilizar emojis y mencionar a "
        "los usuarios cuando sea apropiado, siempre fomentando un ambiente amigable y respetuoso. Mantente actualizado "
        "con la información más reciente del club, incluyendo resultados, fichajes y noticias relevantes."
    )
}

@bot.event
async def on_ready():
    # Obtén los canales habilitados de forma asíncrona
    canales = await sync_to_async(list)(CanalHabilitado.objects.all())
    for canal in canales:
        canales_habilitados.add(int(canal.canal_id))
    logger.info(f'Bot conectado como {bot.user}')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def habilitar_ia(ctx):
    canal_id = ctx.channel.id
    if canal_id not in canales_habilitados:
        canales_habilitados.add(canal_id)
        await sync_to_async(CanalHabilitado.objects.create)(canal_id=str(canal_id))
        await ctx.send(mensaje_bienvenida)
        logger.info(f'IA habilitada en el canal: {ctx.channel.name} (ID: {canal_id})')
    else:
        await ctx.send('La IA ya está habilitada en este canal.')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def deshabilitar_ia(ctx):
    canal_id = ctx.channel.id
    if canal_id in canales_habilitados:
        canales_habilitados.remove(canal_id)
        await sync_to_async(CanalHabilitado.objects.filter(canal_id=str(canal_id)).delete)()
        await ctx.send(f'IA deshabilitada en el canal: {ctx.channel.name}')
        logger.info(f'IA deshabilitada en el canal: {ctx.channel.name} (ID: {canal_id})')
    else:
        await ctx.send('La IA no estaba habilitada en este canal.')


async def cargar_historial(canal_id, limite=20):
    mensajes = await sync_to_async(list)(
        Mensaje.objects.filter(canal_id=str(canal_id)).order_by('-fecha')[:limite]
    )
    mensajes = mensajes[::-1]  # Invertir el orden para cronología
    historial = [mensaje_configuracion]
    for mensaje in mensajes:
        historial.append(
            {
                "role": "user",
                "content": (
                    f"Usuario: {mensaje.nombre_usuario} (ID: {mensaje.usuario_id}) Nombre Global: {mensaje.nombre_global} "
                    f"Mensaje: {mensaje.contenido_mensaje}"
                ),
            }
        )
        historial.append({"role": "assistant", "content": mensaje.respuesta_modelo})
    return historial

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f"Mensaje de {message.author} en el canal {message.channel}: {message.content}")
    # Procesar comandos
    await bot.process_commands(message)

    print("bien")

    if message.channel.id in canales_habilitados:
        # Historial de mensajes
        historial_mensajes = await cargar_historial(message.channel.id)

        print("bien2")
        # Añade el mensaje del usuario al historial
        historial_mensajes.append(
            {
                "role": "user",
                "content": (
                    f"Usuario: {message.author.name} (ID: {message.author.id}) Nombre Global: {message.author.global_name} "
                    f"Mensaje: {message.content}"
                ),
            }
        )


        print("bien3")
        # Interactúa con Together AI
        try:
            # Llamada al modelo
            stream = client.chat.completions.create(
                model="meta-llama/Llama-Vision-Free",
                messages=historial_mensajes,
                temperature=1.0,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                stop=["<|eot_id|>", "<|eom_id|>"],
                stream=True,
            )

            # Obtén la respuesta del modelo
            respuesta_modelo = ""
            for chunk in stream:
                if (
                    chunk.choices
                    and chunk.choices[0].delta
                    and chunk.choices[0].delta.content
                ):
                    respuesta_modelo += chunk.choices[0].delta.content

            # Verifica que la respuesta no esté vacía
            if not respuesta_modelo.strip():
                respuesta_modelo = "Lo siento, no tengo una respuesta para eso en este momento."

            print("bien4")

            # Envía la respuesta al canal
            await message.channel.send(respuesta_modelo)

            # Añade la respuesta del modelo al historial
            historial_mensajes.append({"role": "assistant", "content": respuesta_modelo})
            
            print(message.content)

            print(message.author.name)

            print(message.author.global_name)
            # Guarda los mensajes en la base de datos de forma asíncrona
            await sync_to_async(Mensaje.objects.create)(
                canal_id=str(message.channel.id),
                usuario_id=str(message.author.id),
                nombre_usuario=str(message.author.name),
                nombre_global=str(message.author.global_name),
                contenido_mensaje=str(message.content),
                respuesta_modelo=respuesta_modelo,
            )

        except Exception as e:
            logger.error(f"Error al procesar el mensaje: {e}")
            await message.channel.send("Lo siento, ocurrió un error al procesar tu solicitud.")
