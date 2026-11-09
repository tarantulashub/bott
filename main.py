import os
import time
from collections import defaultdict
from flask import Flask, request
import telebot
from telebot import types

# 1. Credenciales y Configuración de la Mini App
TOKEN = os.environ.get('BOT_TOKEN')

# Reemplaza 'https://tu-url-de-miniapp.com' con el enlace web real de tu Mini App o Telegra.ph
MINI_APP_URL = os.environ.get('MINI_APP_URL', 'https://telegraphplus.netlify.app/')

if not TOKEN:
    raise ValueError("La variable de entorno 'BOT_TOKEN' es obligatoria en Render.")

# Inicializar bot (threaded=False recomendado para Webhooks con Flask)
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# 2. Sistema Anti-Spam Progresivo por user_id
spam_control = defaultdict(lambda: {"last_time": 0.0, "warnings": 0, "ban_until": 0.0, "last_ban_level": 0})

def check_antispam(message):
    user_id = message.from_user.id
    current_time = time.time()
    data = spam_control[user_id]

    if current_time < data["ban_until"]:
        return False

    time_diff = current_time - data["last_time"]

    if time_diff < 1.2:
        if data["warnings"] == 0 and data["last_ban_level"] == 0:
            data["warnings"] = 1
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "⚠️ **Advertencia:** Estás enviando mensajes demasiado rápido. Por favor, baja la velocidad."
            )
            return False
        elif data["warnings"] == 1 and data["last_ban_level"] == 0:
            data["ban_until"] = current_time + 60.0
            data["last_ban_level"] = 2
            data["warnings"] = 0
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "🚫 **Bloqueo temporal:** Has ignorado la advertencia. Estás bloqueado por **1 minuto**."
            )
            return False
        elif data["last_ban_level"] == 2:
            data["ban_until"] = current_time + 86400.0
            data["last_ban_level"] = 3
            data["warnings"] = 0
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "🛑 **Bloqueo severo:** Reincidencia detectada. Acceso restringido por **24 horas**."
            )
            return False
    else:
        if time_diff > 10.0 and data["warnings"] > 0 and data["last_ban_level"] == 0:
            data["warnings"] = 0
        if data["last_ban_level"] > 0 and current_time > data["ban_until"] + 300:
            data["last_ban_level"] = 0
            data["warnings"] = 0

    data["last_time"] = current_time
    return True

# 3. Comando /start con botón en línea para la Mini App
@bot.message_handler(commands=['start'])
def command_start(message):
    if not check_antispam(message):
        return

    user_name = message.from_user.first_name or "Usuario"
    user_id = message.from_user.id

    welcome_text = (
        f"¡Hola, {user_name}!\n\n"
        f"🆔 **Tu ID:** `{user_id}`\n\n"
        "Soy un conector minimalista para nuestra Mini App. "
        "Haz clic en el botón de abajo para abrirla."
    )

    markup = types.InlineKeyboardMarkup()
    web_app_info = types.WebAppInfo(url=MINI_APP_URL)
    btn_mini_app = types.InlineKeyboardButton(text="🚀 Abrir Mini App", web_app=web_app_info)
    markup.add(btn_mini_app)

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# 4. Comando /help y Reglas Claras
@bot.message_handler(commands=['help'])
def command_help(message):
    if not check_antispam(message):
        return

    help_text = (
        "ℹ️ **¿Qué es este bot?**\n"
        "Es exclusivamente un puente técnico hacia nuestra Mini App.\n\n"
        "❌ **Lo que NO hace:**\n"
        "• No es un chatbot de IA.\n"
        "• No responde preguntas generales.\n"
        "• No procesa notas de voz, audios ni imágenes.\n\n"
        "👉 Usa /start para abrir la Mini App."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Manejador de respaldo para mensajes no permitidos
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'voice', 'audio', 'document', 'video', 'sticker'])
def handle_fallback(message):
    if not check_antispam(message):
        return

    bot.send_message(
        message.chat.id, 
        "⚠️ Este bot solo funciona como pasarela hacia la **Mini App**. Usa /start para abrirla.", 
        parse_mode="Markdown"
    )

# 5. Servidor Flask (Webhook)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@app.route('/')
def index():
    return "Bot conector de Mini App activo.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
