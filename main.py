import os
import time
from collections import defaultdict
from flask import Flask, request
import telebot
from telebot import types

# 2. Configuración de credenciales y entorno
TOKEN = os.environ.get('BOT_TOKEN')
MINI_APP_URL = os.environ.get('MINI_APP_URL')

if not TOKEN:
    raise ValueError("La variable de entorno 'BOT_TOKEN' es obligatoria.")
if not MINI_APP_URL:
    raise ValueError("La variable de entorno 'MINI_APP_URL' es obligatoria.")

# Inicializar bot (threaded=False recomendado en entornos de Webhook con Flask)
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# 5. Sistema Anti-Spam Progresivo por user_id
# Estructura: {user_id: {"last_time": float, "warnings": int, "ban_until": float, "last_ban_level": int}}
spam_control = defaultdict(lambda: {"last_time": 0.0, "warnings": 0, "ban_until": 0.0, "last_ban_level": 0})

def check_antispam(message):
    """
    Controla la frecuencia de mensajes por usuario:
    - Nivel 1: Advertencia formal.
    - Nivel 2: Bloqueo temporal de 1 minuto.
    - Nivel 3: Bloqueo severo de 24 horas por reincidencia inmediata tras el castigo anterior.
    """
    user_id = message.from_user.id
    current_time = time.time()
    data = spam_control[user_id]

    # Verificar si el usuario se encuentra actualmente bajo un bloqueo activo
    if current_time < data["ban_until"]:
        return False

    time_diff = current_time - data["last_time"]

    # Umbral de tiempo considerado spam (mensajes con menos de 1.2 segundos de diferencia)
    if time_diff < 1.2:
        if data["warnings"] == 0 and data["last_ban_level"] == 0:
            # Nivel 1: Advertencia formal
            data["warnings"] = 1
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "⚠️ **Advertencia formal:** Estás enviando mensajes de forma excesivamente rápida. "
                "Este bot es un conector minimalista y no procesa spam. Por favor, baja la velocidad."
            )
            return False
        elif data["warnings"] == 1 and data["last_ban_level"] == 0:
            # Nivel 2: Bloqueo temporal de 1 minuto
            data["ban_until"] = current_time + 60.0
            data["last_ban_level"] = 2
            data["warnings"] = 0
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "🚫 **Bloqueo temporal:** Has ignorado la advertencia. "
                "Has sido bloqueado temporalmente durante **1 minuto**."
            )
            return False
        elif data["last_ban_level"] == 2:
            # Nivel 3: Bloqueo severo de 24 horas por reincidencia inmediata tras el castigo
            data["ban_until"] = current_time + 86400.0
            data["last_ban_level"] = 3
            data["warnings"] = 0
            data["last_time"] = current_time
            bot.reply_to(
                message, 
                "🛑 **Bloqueo severo:** Has reincidido inmediatamente tras cumplirse tu sanción anterior. "
                "Tu acceso ha sido restringido por **24 horas**."
            )
            return False
    else:
        # Restablecimiento progresivo tras periodos de calma prolongados
        if time_diff > 10.0 and data["warnings"] > 0 and data["last_ban_level"] == 0:
            data["warnings"] = 0
        if data["last_ban_level"] > 0 and current_time > data["ban_until"] + 300:
            data["last_ban_level"] = 0
            data["warnings"] = 0

    data["last_time"] = current_time
    return True

# 3. Comando /start
@bot.message_handler(commands=['start'])
def command_start(message):
    if not check_antispam(message):
        return

    user_name = message.from_user.first_name or "Usuario"
    user_id = message.from_user.id

    welcome_text = (
        f"¡Hola, {user_name}!\n\n"
        f"🆔 **Tu ID de usuario:** `{user_id}`\n\n"
        "Soy un conector minimalista diseñado para enlazar de manera directa y fluida con nuestra Mini App.\n\n"
        "Haz clic en el botón inferior para abrir la aplicación."
    )

    # Botón interactivo Inline para abrir la Mini App
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
        "Este bot funciona estrictamente como un puente o conector técnico hacia nuestra Mini App.\n\n"
        "❌ **Lo que NO hace este bot:**\n"
        "• No es un chatbot de Inteligencia Artificial.\n"
        "• No responde preguntas generales ni consultas de soporte técnico en este chat.\n"
        "• No procesa notas de voz, audios, imágenes, documentos ni archivos multimedia.\n\n"
        "👉 Usa /start para acceder a la Mini App."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Manejador general para cualquier otro mensaje de texto o multimedia entrante
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'voice', 'audio', 'document', 'video', 'sticker'])
def handle_fallback(message):
    if not check_antispam(message):
        return

    response_text = (
        "⚠️ Este bot opera exclusivamente como pasarela hacia la **Mini App**.\n\n"
        "No interpreto mensajes directos ni archivos. Utiliza /start para abrir la aplicación o /help para conocer las reglas."
    )
    bot.send_message(message.chat.id, response_text, parse_mode="Markdown")

# 6. Estructura del Servidor Flask (Webhook)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

# Ruta raíz de comprobación de estado (Health Check)
@app.route('/')
def index():
    return "Bot conector de Mini App activo y funcionando en Webhook.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
