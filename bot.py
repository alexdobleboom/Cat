import telebot
from telebot import types
import requests
import time
from urllib.parse import urlparse, parse_qs
from loguru import logger

# Configuración inicial
TOKEN = '8344397573:AAFPe-CE_zNOtMFiAmSPdmkUTDeBva86Es4'
ADMIN_CHAT_ID = 7400531692 # Reemplaza con tu ID
bot = telebot.TeleBot(TOKEN)

# Estados del usuario
USER_STATES = {}
BANNED_USERS = set()
REGISTERED_USERS = set()

# Configurar logger
logger.add("bot.log", rotation="1 MB", retention="3 days", level="INFO")

# ====================== TECLADOS ======================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ["🎬 Película", "📺 Serie", "🎮 Juego", "📸 YouTube", "🆘 Soporte"]
    markup.add(*buttons)
    return markup

def cancel_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Cancelar")
    return markup

# ====================== HANDLERS PRINCIPALES ======================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    if user.id in BANNED_USERS:
        return
    
    REGISTERED_USERS.add(user.id)
    welcome_msg = (
        f"¡Hola {user.first_name}! 👋\n\n"
        "📲 Con este bot puedes:\n"
        "- Crear plantillas multimedia profesionales\n"
        "- Descargar miniaturas de YouTube\n"
        "- Contactar con soporte técnico\n\n"
        "¡Elige una opción del menú!"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "❌ Cancelar")
def cancel_operation(message):
    user_id = message.from_user.id
    USER_STATES.pop(user_id, None)
    bot.send_message(message.chat.id, "Operación cancelada ✅", reply_markup=main_menu())

# ====================== MANEJO DE PLANTILLAS ======================
@bot.message_handler(func=lambda m: m.text in ["🎬 Película", "📺 Serie", "🎮 Juego"])
def handle_template_selection(message):
    media_type = message.text
    USER_STATES[message.from_user.id] = {
        'type': media_type,
        'step': 0,
        'data': {}
    }
    msg = bot.send_message(message.chat.id, "📤 Envía la imagen principal:", reply_markup=cancel_menu())
    bot.register_next_step_handler(msg, process_media_step)

def process_media_step(message):
    if message.text == "❌ Cancelar":
        return cancel_operation(message)
    
    user_id = message.from_user.id
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "⚠️ Formato incorrecto. Envía una imagen válida:", reply_markup=cancel_menu())
        bot.register_next_step_handler(msg, process_media_step)
        return
    
    USER_STATES[user_id]['data']['photo'] = message.photo[-1].file_id
    ask_next_field(message)

def ask_next_field(message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)
    
    if not state:
        return cancel_operation(message)
    
    fields_config = {
        "🎬 Película": ['Título', 'Género', 'Año', 'Duración', 'Calidad', 'Sinopsis'],
        "📺 Serie": ['Título', 'Género', 'Temporadas', 'Episodios', 'Calidad', 'Sinopsis'],
        "🎮 Juego": ['Nombre', 'Género', 'Plataforma', 'Tamaño', 'Versión', 'Descripción']
    }
    
    fields = fields_config[state['type']]
    
    if state['step'] < len(fields):
        field = fields[state['step']]
        state['step'] += 1
        msg = bot.send_message(message.chat.id, f"✏️ {field}:", reply_markup=cancel_menu())
        bot.register_next_step_handler(msg, process_text_step)
    else:
        generate_template(message)

def process_text_step(message):
    if message.text == "❌ Cancelar":
        return cancel_operation(message)
    
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)
    
    if not state:
        return cancel_operation(message)
    
    fields_mapping = {
        "🎬 Película": ['title', 'genre', 'year', 'duration', 'quality', 'description'],
        "📺 Serie": ['title', 'genre', 'seasons', 'episodes', 'quality', 'description'],
        "🎮 Juego": ['name', 'genre', 'platform', 'size', 'version', 'description']
    }
    
    current_step = state['step'] - 1
    field_name = fields_mapping[state['type']][current_step]
    state['data'][field_name] = message.text
    
    ask_next_field(message)

def generate_template(message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id)
    
    if not state:
        return cancel_operation(message)
    
    template = ""
    if state['type'] == "🎬 Película":
        template = (
            "🎬 *PLANTILLA DE PELÍCULA* 🎬\n\n"
            f"🏷 Título: {state['data'].get('title', 'N/A')}\n"
            f"🎭 Género: {state['data'].get('genre', 'N/A')}\n"
            f"📅 Año: {state['data'].get('year', 'N/A')}\n"
            f"⏱ Duración: {state['data'].get('duration', 'N/A')}\n"
            f"📦 Calidad: {state['data'].get('quality', 'N/A')}\n"
            f"📝 Sinopsis: {state['data'].get('description', 'N/A')}"
        )
    elif state['type'] == "📺 Serie":
        template = (
            "📺 *PLANTILLA DE SERIE* 📺\n\n"
            f"🏷 Título: {state['data'].get('title', 'N/A')}\n"
            f"🎭 Género: {state['data'].get('genre', 'N/A')}\n"
            f"📑 Temporadas: {state['data'].get('seasons', 'N/A')}\n"
            f"📚 Episodios: {state['data'].get('episodes', 'N/A')}\n"
            f"📦 Calidad: {state['data'].get('quality', 'N/A')}\n"
            f"📝 Sinopsis: {state['data'].get('description', 'N/A')}"
        )
    elif state['type'] == "🎮 Juego":
        template = (
            "🎮 *PLANTILLA DE JUEGO* 🎮\n\n"
            f"🕹 Nombre: {state['data'].get('name', 'N/A')}\n"
            f"🎭 Género: {state['data'].get('genre', 'N/A')}\n"
            f"📱 Plataforma: {state['data'].get('platform', 'N/A')}\n"
            f"💾 Tamaño: {state['data'].get('size', 'N/A')}\n"
            f"🆕 Versión: {state['data'].get('version', 'N/A')}\n"
            f"📄 Descripción: {state['data'].get('description', 'N/A')}"
        )
    
    bot.send_photo(
        message.chat.id,
        state['data']['photo'],
        caption=template,
        reply_markup=main_menu()
    )
    USER_STATES.pop(user_id, None)

# ====================== YOUTUBE DOWNLOADER ======================
@bot.message_handler(func=lambda m: m.text == "📸 YouTube")
def handle_youtube(message):
    msg = bot.send_message(message.chat.id, "🔗 Envía la URL del video de YouTube:", reply_markup=cancel_menu())
    bot.register_next_step_handler(msg, process_youtube_url)

def process_youtube_url(message):
    if message.text == "❌ Cancelar":
        return cancel_operation(message)
    
    video_id = extract_video_id(message.text)
    if not video_id:
        return bot.send_message(message.chat.id, "❌ URL inválida", reply_markup=main_menu())
    
    try:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        bot.send_photo(
            message.chat.id,
            thumbnail_url,
            caption="✅ Miniatura descargada correctamente",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Error YouTube: {e}")
        bot.send_message(message.chat.id, "❌ Error al descargar la miniatura", reply_markup=main_menu())

def extract_video_id(url):
    try:
        query = urlparse(url)
        if query.hostname in ('youtube.com', 'www.youtube.com'):
            if query.path == '/watch':
                return parse_qs(query.query).get('v', [None])[0]
            elif query.path.startswith('/embed/'):
                return query.path.split('/')[2]
        elif query.hostname == 'youtu.be':
            return query.path[1:]
    except:
        return None

# ====================== SISTEMA DE SOPORTE ======================
@bot.message_handler(func=lambda m: m.text == "🆘 Soporte")
def handle_support(message):
    msg = bot.send_message(message.chat.id, "✉️ Escribe tu mensaje para soporte:", reply_markup=cancel_menu())
    bot.register_next_step_handler(msg, forward_to_support)

def forward_to_support(message):
    if message.text == "❌ Cancelar":
        return cancel_operation(message)
    
    user = message.from_user
    report = (
        f"🆘 Nuevo reporte de @{user.username}\n"
        f"ID: {user.id}\n"
        f"Mensaje: {message.text}"
    )
    
    bot.send_message(ADMIN_CHAT_ID, report)
    bot.send_message(message.chat.id, "✅ Mensaje enviado a soporte", reply_markup=main_menu())

# ====================== ADMINISTRACIÓN ======================
@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if message.from_user.id != ADMIN_CHAT_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        return bot.send_message(message.chat.id, "Uso: /ban [user_id/@username]")
    
    target = args[1]
    BANNED_USERS.add(target.lower())
    bot.send_message(message.chat.id, f"✅ Usuario {target} baneado")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_CHAT_ID:
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.send_message(message.chat.id, "Uso: /broadcast [mensaje]")
    
    text = args[1]
    results = {'success': 0, 'failed': 0}
    
    for user_id in REGISTERED_USERS:
        try:
            if str(user_id) not in BANNED_USERS:
                bot.send_message(user_id, text)
                results['success'] += 1
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error en broadcast: {e}")
            results['failed'] += 1
    
    report = (
        "📊 Resultado del broadcast:\n"
        f"✅ Enviados: {results['success']}\n"
        f"❌ Fallidos: {results['failed']}"
    )
    bot.send_message(message.chat.id, report)

if __name__ == '__main__':
    logger.info("Bot iniciado correctamente")
    bot.infinity_polling()
