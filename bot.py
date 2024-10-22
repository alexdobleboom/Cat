import telebot
from telebot import types
import threading
import http.server
import socketserver
import os
import requests
from urllib.parse import urlparse, parse_qs
from loguru import logger
import sys

# Configurar loguru para mostrar solo advertencias y errores
logger.remove()  # Eliminar manejadores predeterminados
logger.add(sys.stderr, level="WARNING")  # Solo mostrará WARN y ERROR en la consola

bot = telebot.TeleBot('8034560855:AAEUzD4OgNWd0I6tMJopVdhPNWZVsBR7qXw')  # Reemplaza con tu token real

movie_info = {}
serie_info = {}
game_info = {}
admin_chat_id = 7551486576  # Reemplaza con el chat ID del administrador
banned_users = set()
banned_ids = set()
user_ids = set()
user_in_template_process = {}

def is_user_banned(user_id, username):
    return user_id in banned_ids or username in banned_users

def banned_user_handler(message):
    username = message.from_user.username or message.from_user.first_name
    user_id = message.from_user.id
    return is_user_banned(user_id, username)

def check_stop_command(message):
    """Verifica si el mensaje es '⛔STOP' y cancela el proceso si es necesario."""
    if message.text == "⛔STOP":
        cancel_template(message)
        return True
    return False

def send_message_with_rich_logging(chat_id, message, **kwargs):
    if "error" in message.lower():
        logger.warning(f"Enviando mensaje a {chat_id}: {message}")
    bot.send_message(chat_id, message, **kwargs)

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id == admin_chat_id:
        args = message.text.split()
        if len(args) > 1:
            identifier = args[1]
            if identifier.startswith('@'):
                username_to_ban = identifier[1:]
                banned_users.add(username_to_ban)
                send_message_with_rich_logging(message.chat.id, f"Usuario @{username_to_ban} ha sido prohibido.")
            else:
                try:
                    user_id_to_ban = int(identifier)
                    banned_ids.add(user_id_to_ban)
                    send_message_with_rich_logging(message.chat.id, f"Usuario con ID {user_id_to_ban} ha sido prohibido.")
                except ValueError:
                    send_message_with_rich_logging(message.chat.id, "Formato incorrecto. Usa /ban @username o /ban user_id.")
        else:
            send_message_with_rich_logging(message.chat.id, "Por favor, especifica un usuario para prohibir usando la forma: /ban @username o /ban user_id.")
    else:
        send_message_with_rich_logging(message.chat.id, "No tienes permiso para usar este comando.")

@bot.message_handler(commands=['send'])
def send_message_to_all(message):
    if message.from_user.id == admin_chat_id:
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            text_message = args[1]
            success_count = 0
            for user_id in user_ids:
                try:
                    bot.send_message(user_id, text_message, parse_mode='MarkdownV2')
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Error al enviar mensaje a {user_id}: {e}")
            if success_count > 0:
                send_message_with_rich_logging(message.chat.id, f"Mensaje enviado a {success_count} usuarios.")
        else:
            send_message_with_rich_logging(message.chat.id, "Por favor, especifica el mensaje que deseas enviar.")
    else:
        send_message_with_rich_logging(message.chat.id, "No tienes permiso para usar este comando.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if banned_user_handler(message):
        return

    user_ids.add(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("PELICULA🎬", "SERIE📺", "GAME🎮", "Soporte📱", "DL_YOUTUBE")
    send_message_with_rich_logging(message.chat.id, f"¡Hola {username}! con este bot puedes crear tus plantillas más fáciles \n\n¡También puedes descargar las miniaturas de Youtube!\n\nChannel: @hc_free:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Soporte📱")
def support_command(message):
    if banned_user_handler(message):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⛔STOP")
    send_message_with_rich_logging(message.chat.id, "Escribe tu mensaje y lo enviaré al administrador:", reply_markup=markup)
    bot.register_next_step_handler(message, receive_support_message)

def receive_support_message(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    username = message.from_user.username or message.from_user.first_name
    user_id = message.from_user.id
    support_message = message.text
    message_text = f"(@{username})\n(ID: {user_id})\nMensaje: {support_message}"
    
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Responder", callback_data=f"reply_{user_id}")
    markup.add(button)

    send_message_with_rich_logging(admin_chat_id, message_text, reply_markup=markup)
    send_message_with_rich_logging(message.chat.id, "¡Mensaje enviado con éxito!")

    main_menu(message)

@bot.message_handler(func=lambda message: message.text == "DL_YOUTUBE")
def photo_command(message):
    if banned_user_handler(message):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⛔STOP")
    send_message_with_rich_logging(message.chat.id, "🔗 Introduce la URL del vídeo de YouTube:", reply_markup=markup)
    bot.register_next_step_handler(message, process_youtube_url)

def process_youtube_url(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    url = message.text
    video_id = obtener_id_video(url)
    
    if video_id:
        descargar_miniatura(video_id, message.chat.id)
    else:
        send_message_with_rich_logging(message.chat.id, '⭕ URL no válida ⭕.')

    main_menu(message)

@bot.message_handler(func=lambda message: message.text == "PELICULA🎬")
def start_movie_template(message):
    if banned_user_handler(message):
        return

    user_in_template_process[message.from_user.id] = 'movie'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⛔STOP")
    send_message_with_rich_logging(message.chat.id, "Envía una foto de la película:", reply_markup=markup)
    bot.register_next_step_handler(message, get_movie_photo)

def get_movie_photo(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    if message.photo:
        movie_info['foto'] = message.photo[-1].file_id
        send_message_with_rich_logging(message.chat.id, "📝 Envía el nombre:")
        bot.register_next_step_handler(message, get_movie_name)
    else:
        bot.reply_to(message, "Envía una foto válida.")
        bot.register_next_step_handler(message, get_movie_photo)

def get_movie_name(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['nombre'] = message.text
    send_message_with_rich_logging(message.chat.id, "🔰 Envía género:")
    bot.register_next_step_handler(message, get_movie_genre)

def get_movie_genre(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['genero'] = message.text
    send_message_with_rich_logging(message.chat.id, "📅 Envía año:")
    bot.register_next_step_handler(message, get_movie_year)

def get_movie_year(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['año'] = message.text
    send_message_with_rich_logging(message.chat.id, "💾 Cuánto pesa:")
    bot.register_next_step_handler(message, get_movie_size)

def get_movie_size(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['tamaño'] = message.text
    send_message_with_rich_logging(message.chat.id, "⚙ Método de descarga:")
    bot.register_next_step_handler(message, get_movie_method)

def get_movie_method(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['metodo'] = message.text
    send_message_with_rich_logging(message.chat.id, "🎬 Envía la sinopsis:")
    bot.register_next_step_handler(message, save_movie_info)

def save_movie_info(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    movie_info['sinopsis'] = message.text

    movie_template = f"📋Nombre: {movie_info['nombre']}\n🎬Género: {movie_info['genero']}\n📆Año: {movie_info['año']}\n💾Tamaño: {movie_info['tamaño']}\n☁Método de descarga: {movie_info['metodo']}\n🗒Sinopsis: {movie_info['sinopsis']}"
    bot.send_photo(message.chat.id, movie_info['foto'], caption=movie_template)
    movie_info.clear()
    user_in_template_process.pop(message.from_user.id, None)

    main_menu(message)

@bot.message_handler(func=lambda message: message.text == "SERIE📺")
def start_serie_template(message):
    if banned_user_handler(message):
        return

    user_in_template_process[message.from_user.id] = 'serie'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⛔STOP")
    send_message_with_rich_logging(message.chat.id, "Envía una foto de la serie:", reply_markup=markup)
    bot.register_next_step_handler(message, get_serie_photo)

def get_serie_photo(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    if message.photo:
        serie_info['foto'] = message.photo[-1].file_id
        send_message_with_rich_logging(message.chat.id, "✏ Envía el nombre:")
        bot.register_next_step_handler(message, get_serie_name)
    else:
        bot.reply_to(message, "Envía una foto válida.")
        bot.register_next_step_handler(message, get_serie_photo)

def get_serie_name(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['nombre'] = message.text
    send_message_with_rich_logging(message.chat.id, "⚜ Envía género:")
    bot.register_next_step_handler(message, get_serie_genre)

def get_serie_genre(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['genero'] = message.text
    send_message_with_rich_logging(message.chat.id, "#⃣ Envía el # de capítulos:")
    bot.register_next_step_handler(message, get_serie_num_caps)

def get_serie_num_caps(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['num_caps'] = message.text
    send_message_with_rich_logging(message.chat.id, "🆕 Envía el # de temporada:")
    bot.register_next_step_handler(message, get_serie_num_seasons)

def get_serie_num_seasons(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['num_seasons'] = message.text
    send_message_with_rich_logging(message.chat.id, "💾 Envía el tamaño:")
    bot.register_next_step_handler(message, get_serie_size)

def get_serie_size(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['tamaño'] = message.text
    send_message_with_rich_logging(message.chat.id, "☁ Método de descarga:")
    bot.register_next_step_handler(message, get_serie_method)

def get_serie_method(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['metodo'] = message.text
    send_message_with_rich_logging(message.chat.id, "📑 Envía la sinopsis:")
    bot.register_next_step_handler(message, save_serie_info)

def save_serie_info(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    serie_info['sinopsis'] = message.text

    serie_template = f"📋Nombre: {serie_info['nombre']}\n🎬Género: {serie_info['genero']}\n⏸# de Cap: {serie_info['num_caps']}\n▶# de Temp: {serie_info['num_seasons']}\n💾Tamaño: {serie_info['tamaño']}\n☁Método de descarga: {serie_info['metodo']}\n🗒Sinopsis: {serie_info['sinopsis']}"
    bot.send_photo(message.chat.id, serie_info['foto'], caption=serie_template)
    serie_info.clear()
    user_in_template_process.pop(message.from_user.id, None)

    main_menu(message)

@bot.message_handler(func=lambda message: message.text == "GAME🎮")
def start_game_template(message):
    if banned_user_handler(message):
        return

    user_in_template_process[message.from_user.id] = 'game'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⛔STOP")
    send_message_with_rich_logging(message.chat.id, "Envía una foto del juego:", reply_markup=markup)
    bot.register_next_step_handler(message, get_game_photo)

def get_game_photo(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    if message.photo:
        game_info['foto'] = message.photo[-1].file_id
        send_message_with_rich_logging(message.chat.id, "🛠 Envía el nombre:")
        bot.register_next_step_handler(message, get_game_name)
    else:
        bot.reply_to(message, "Envía una foto válida.")
        bot.register_next_step_handler(message, get_game_photo)

def get_game_name(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['nombre'] = message.text
    send_message_with_rich_logging(message.chat.id, "🔰 Ingresa el género:")
    bot.register_next_step_handler(message, get_game_genre)

def get_game_genre(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['genero'] = message.text
    send_message_with_rich_logging(message.chat.id, "🔓 Envía info del mod:")
    bot.register_next_step_handler(message, get_game_platform)

def get_game_platform(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['plataforma'] = message.text
    send_message_with_rich_logging(message.chat.id, "💾 Envía el tamaño:")
    bot.register_next_step_handler(message, get_game_size)

def get_game_size(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['tamaño'] = message.text
    send_message_with_rich_logging(message.chat.id, "💠 Envía el método de descarga:")
    bot.register_next_step_handler(message, get_game_method)

def get_game_method(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['metodo'] = message.text
    send_message_with_rich_logging(message.chat.id, "💬 De qué se trata:")
    bot.register_next_step_handler(message, save_game_info)

def save_game_info(message):
    if banned_user_handler(message):
        return

    if check_stop_command(message):
        return

    game_info['sinopsis'] = message.text

    game_template = f"🕹Nombre: {game_info['nombre']}\n🎬Género: {game_info['genero']}\n😈Info Mod: {game_info['plataforma']}\n💾Tamaño: {game_info['tamaño']}\n☁Método de descarga: {game_info['metodo']}\n🗒Sinopsis: {game_info['sinopsis']}"
    bot.send_photo(message.chat.id, game_info['foto'], caption=game_template)
    game_info.clear()
    user_in_template_process.pop(message.from_user.id, None)

    main_menu(message)

def cancel_template(message):
    user_id = message.from_user.id
    user_in_template_process.pop(user_id, None)
    main_menu(message)

def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("PELICULA🎬", "SERIE📺", "GAME🎮", "Soporte📱", "DL_YOUTUBE")
    send_message_with_rich_logging(message.chat.id, "¡Elige una opción:", reply_markup=markup)

def obtener_id_video(url):
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        if 'v=' in parsed_url.query:
            return parse_qs(parsed_url.query)['v'][0]
    elif 'youtu.be' in parsed_url.netloc:
        return parsed_url.path[1:]
    return None

def descargar_miniatura(video_id, chat_id):
    url_miniatura = f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
    
    send_message_with_rich_logging(chat_id, "🔄 Descargando la miniatura..espera 5 segundos")
    
    response = requests.get(url_miniatura)

    if response.status_code == 200:
        carpeta = 'miniaturas_youtube'
        os.makedirs(carpeta, exist_ok=True)

        ruta_archivo = os.path.join(carpeta, f'{video_id}.jpg')
        with open(ruta_archivo, 'wb') as file:
            file.write(response.content)
        
        bot.send_photo(chat_id, open(ruta_archivo, 'rb'), caption='⚡ Miniatura descargada 💾')
    else:
        send_message_with_rich_logging(chat_id, '🧐Error al descargar, contacte a @Creazy_Call🧐')

def run_server():
    PORT = 9000
    with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

def run_bot():
    bot.polling()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    run_bot()
