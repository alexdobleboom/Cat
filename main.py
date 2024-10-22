import os
import re
import logging
from telethon import TelegramClient, events
from telethon.tl.types import InputWebDocument
from PIL import Image

# Configura la logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define tu API_ID, API_HASH y BOT_TOKEN
API_ID = '24288670'
API_HASH = '81c58005802498656d6b689dae1edacc'
BOT_TOKEN = '8034560855:AAEUzD4OgNWd0I6tMJopVdhPNWZVsBR7qXw'

# Crea un cliente de Telethon
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Variables globales para el manejo de archivos
thumbnail_name = None
downloaded_file = None

# Función para cambiar miniatura y nombre de archivo
def change_file(file_path, thumbnail_path, new_name, new_format):
    try:
        new_file_name = f"{new_name}.{new_format}"
        os.rename(file_path, new_file_name)
        os.system(f"ffmpeg -i {new_file_name} -i {thumbnail_path} -map 0 -map 1 -c copy -metadata:s:v:0 title=\"{new_name}\" {new_file_name}")
        return True, f"Archivo renombrado y miniatura actualizada correctamente a: {new_file_name}"
    except Exception as e:
        logger.error(f"Error al renombrar el archivo o actualizar la miniatura: {e}")
        return False, f"Error al renombrar el archivo o actualizar la miniatura: {e}"

# Función para redimensionar la miniatura
def resize_thumbnail(thumbnail_path, max_size=512):
    try:
        img = Image.open(thumbnail_path)
        width, height = img.size
        if width > max_size or height > max_size:
            ratio = min(max_size / width, max_size / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height))
            img.save(thumbnail_path)
            return True, f"Miniatura redimensionada a {new_width}x{new_height}"
        else:
            return True, f"Miniatura ya tiene el tamaño adecuado."
    except Exception as e:
        logger.error(f"Error al redimensionar la miniatura: {e}")
        return False, f"Error al redimensionar la miniatura: {e}"

# Manejador de mensajes de imágenes
@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_thumbnail(event):
    global thumbnail_name
    thumbnail_name = 'thumbnail.jpg'
    await event.download_media(thumbnail_name)
    success, result = resize_thumbnail(thumbnail_name)
    await event.reply(result)
    await event.reply("¡Miniatura recibida!\nAhora, envía el archivo que deseas renombrar y cambiar su miniatura.")

# Manejador de mensajes de archivos
@client.on(events.NewMessage(func=lambda e: e.document))
async def handle_file(event):
    global downloaded_file
    downloaded_file = event.message.file.name
    await event.download_media(downloaded_file)
    await event.reply("¡Archivo recibido!\nAhora, envía el nuevo nombre y formato del archivo (separados por un espacio, por ejemplo: 'NuevoNombre mp4').")

# Manejador de mensajes de texto
@client.on(events.NewMessage(func=lambda e: e.text))
async def handle_rename(event):
    global thumbnail_name, downloaded_file
    try:
        new_name, new_format = event.message.message.split()
        if not re.match(r"^[a-zA-Z0-9_\.\-]+$", new_name):
            await event.reply("El nuevo nombre no es válido. Solo se permiten letras, números, guiones bajos, puntos y guiones.")
            return
        if not re.match(r"^[a-zA-Z0-9]+$", new_format):
            await event.reply("El nuevo formato no es válido. Solo se permiten letras y números.")
            return
        success, result = change_file(downloaded_file, thumbnail_name, new_name, new_format)
        await event.reply(result)
        if success:
            os.remove(downloaded_file)
            os.remove(thumbnail_name)
    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {e}")
        await event.reply(f"Error al procesar la solicitud: {e}")

# Iniciar el bot
client.start()
client.run_until_disconnected()
