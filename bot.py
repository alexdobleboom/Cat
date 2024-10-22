import os
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    PeerFloodError,
    UserPrivacyRestrictedError,
    ChatAdminRequired,
    UserNotParticipant,
    ChatWriteForbidden,
    ChatInvalid,
    PeerIdInvalid,
    BadRequest,
)
from PIL import Image

# Configura la logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Define tus credenciales de Telegram
API_ID = "24288670" # Reemplaza con tu API_ID
API_HASH = "81c58005802498656d6b689dae1edacc" # Reemplaza con tu API_HASH
BOT_TOKEN = "8034560855:AAEUzD4OgNWd0I6tMJopVdhPNWZVsBR7qXw" # Reemplaza con tu BOT_TOKEN

# Crea un cliente de Pyrogram
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Variables globales para el manejo de archivos
thumbnail_name = None
downloaded_file = None

# Función para cambiar miniatura y nombre de archivo
def change_file(file_path, thumbnail_path, new_name, new_format):
    try:
        # Genera el nuevo nombre de archivo
        new_file_name = f"{new_name}.{new_format}"
        os.rename(file_path, new_file_name)

        # Establece la miniatura del archivo
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
            # Calcula el nuevo tamaño
            new_size = max_size
            ratio = min(new_size / width, new_size / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)

            # Redimensiona la imagen
            img = img.resize((new_width, new_height))
            img.save(thumbnail_path)

            return True, f"Miniatura redimensionada a {new_width}x{new_height}"
        else:
            return True, f"Miniatura ya tiene el tamaño adecuado."
    except Exception as e:
        logger.error(f"Error al redimensionar la miniatura: {e}")
        return False, f"Error al redimensionar la miniatura: {e}"

# Función para enviar un mensaje de confirmación con botones
async def send_confirmation_message(client, message, new_name, new_format):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Confirmar", callback_data=f"confirm_{new_name}_{new_format}"
                ),
                InlineKeyboardButton(
                    "Cancelar", callback_data=f"cancel"
                ),
            ]
        ]
    )
    await message.reply(
        f"¿Deseas renombrar el archivo a '{new_name}.{new_format}' con esta miniatura?",
        reply_markup=keyboard,
    )

# Función para manejar las respuestas de los botones
@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    global thumbnail_name, downloaded_file
    try:
        data = callback_query.data
        if data.startswith("confirm_"):
            new_name, new_format = data.split("_")[1:]
            success, result = change_file(
                downloaded_file, thumbnail_name, new_name, new_format
            )
            if success:
                await callback_query.message.reply(result)
            else:
                await callback_query.message.reply(result)
            await callback_query.message.edit_reply_markup(None)
            os.remove(downloaded_file)
            os.remove(thumbnail_name)
        elif data == "cancel":
            await callback_query.message.reply(
                "Operación cancelada.", reply_markup=None
            )
            os.remove(downloaded_file)
            os.remove(thumbnail_name)
        else:
            await callback_query.message.reply("Opción inválida.")
    except Exception as e:
        logger.error(f"Error al manejar la respuesta del botón: {e}")
        await callback_query.message.reply(
            f"Error al procesar la solicitud: {e}", reply_markup=None
        )

# Manejador de mensajes de imágenes
@app.on_message(filters.photo)
async def handle_thumbnail(client: Client, message: Message):
    global thumbnail_name
    try:
        # Descarga la miniatura
        thumbnail_id = message.photo.file_id
        thumbnail_name = f"thumbnail_{message.photo.file_unique_id}.jpg"
        downloaded_thumbnail = await client.download_media(message, file_name=thumbnail_name)

        # Redimensiona la miniatura
        success, result = resize_thumbnail(thumbnail_name)
        await message.reply(result)

        # Envía un mensaje solicitando el archivo
        await message.reply(
            "¡Miniatura recibida!\nAhora, envía el archivo que deseas renombrar y cambiar su miniatura."
        )

    except Exception as e:
        logger.error(f"Error al recibir la miniatura: {e}")
        await message.reply(f"Error al recibir la miniatura: {e}")

# Manejador de mensajes de archivos
@app.on_message(filters.document)
async def handle_file(client: Client, message: Message):
    global downloaded_file
    try:
        # Descarga el archivo
        file_id = message.document.file_id
        file_name = message.document.file_name
        downloaded_file = await client.download_media(message, file_name=file_name)

        # Envía un mensaje solicitando el nuevo nombre y formato
        await message.reply(
            "¡Archivo recibido!\nAhora, envía el nuevo nombre y formato del archivo (separados por un espacio, por ejemplo: 'NuevoNombre mp4')."
        )

    except Exception as e:
        logger.error(f"Error al recibir el archivo: {e}")
        await message.reply(f"Error al recibir el archivo: {e}")

# Manejador de mensajes de texto
@app.on_message(filters.text)
async def handle_rename(client: Client, message: Message):
    global thumbnail_name, downloaded_file
    try:
        # Obtiene el nuevo nombre y formato del archivo
        new_name, new_format = message.text.split()

        # Valida el nuevo nombre y formato
        if not re.match(r"^[a-zA-Z0-9_\.\-]+$", new_name):
            await message.reply(
                "El nuevo nombre no es válido. Solo se permiten letras, números, guiones bajos, puntos y guiones."
            )
            return

        if not re.match(r"^[a-zA-Z0-9]+$", new_format):
            await message.reply(
                "El nuevo formato no es válido. Solo se permiten letras y números."
            )
            return

        # Envía un mensaje de confirmación con botones
        await send_confirmation_message(client, message, new_name, new_format)

    except BadRequest as e:
        logger.error(f"Error de formato: {e}")
        await message.reply(f"Error de formato: {e}")
    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {e}")
        await message.reply(f"Error al procesar la solicitud: {e}")

# Iniciar el bot
app.run()
