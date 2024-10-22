import telebot
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import re
from datetime import datetime, timedelta
import sqlite3
import asyncio

# Reemplaza esto con tu token de bot de Telegram
BOT_TOKEN = "8034560855:AAEUzD4OgNWd0I6tMJopVdhPNWZVsBR7qXw"
bot = telebot.TeleBot(BOT_TOKEN)

# Almacena el estado del usuario
user_data = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "Hola! Soy tu bot para cambiar miniaturas. Envía una imagen primero y luego un archivo.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_data[message.chat.id] = {}  # Inicializa el estado del usuario
    user_data[message.chat.id]['photo'] = message.photo[-1].file_id
    bot.send_message(message.chat.id, "Ahora envía el archivo que deseas actualizar.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    if user_id not in user_data or 'photo' not in user_data[user_id]:
        bot.send_message(user_id, "Primero debes enviar una imagen antes de enviar un documento.")
        return
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    # Pide un nuevo nombre para el archivo
    bot.send_message(user_id, "Por favor, envía el nuevo nombre para el archivo (incluyendo la extensión, por ejemplo, 'nuevo_nombre.pdf').")
    user_data[user_id]['file_to_rename'] = downloaded_file  # Guarda el archivo para renombrar
    user_data[user_id]['file_extension'] = message.document.file_name.split('.')[-1]  # Guarda la extensión del archivo
    bot.register_next_step_handler(message, rename_file)

def rename_file(message):
    user_id = message.chat.id
    if user_id not in user_data or 'file_to_rename' not in user_data[user_id]:
        bot.send_message(user_id, "No se ha recibido un archivo para renombrar.")
        return
    new_file_name = message.text
    file_to_rename = user_data[user_id]['file_to_rename']
    file_extension = user_data[user_id]['file_extension']
    try:
        # Primero, descarga la foto que se guardó
        photo_info = bot.get_file(user_data[user_id]['photo'])
        downloaded_photo = bot.download_file(photo_info.file_path)
        # Carga la imagen para la miniatura
        image = Image.open(BytesIO(downloaded_photo))
        # Redimensiona la imagen a un tamaño de miniatura (opcional)
        image.thumbnail((100, 100))  # Ejemplo: 100x100 píxeles
        # Guarda la imagen en un buffer
        thumb_io = BytesIO()
        image.save(thumb_io, "JPEG")
        thumb_io.seek(0)
        # Crea un buffer para el archivo original
        updated_file_io = BytesIO(file_to_rename)
        updated_file_io.seek(0)  # Asegúrate de que el puntero esté en la posición correcta
        # Envía el archivo actualizado con el nuevo nombre
        bot.send_document(
            user_id,
            document=updated_file_io,
            thumb=thumb_io,
            caption=f"Archivo enviado con el nuevo nombre: {new_file_name}"  # Ahora añadimos el nuevo nombre en el caption
        )
    except UnidentifiedImageError:
        bot.send_message(
            user_id,
            "No se pudo identificar la imagen. Asegúrate de enviar una imagen válida.",
        )
    except Exception as e:
        bot.send_message(user_id, f"Ocurrió un error inesperado: {str(e)}")

# Iniciar el bot
bot.polling()
