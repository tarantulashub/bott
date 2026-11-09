import os
import time
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = os.environ.get('BOT_TOKEN')
# Reemplaza o configura esta variable en Render con el link de tu Mini App (ej. Vercel)
MINI_APP_URL = os.environ.get(
    'MINI_APP_URL', 'https://tu-mini-app-en-vercel.app'
)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Memoria temporal para el control Anti-Spam
# Estructura: {user_id: {"timestamps": [], "ban_until": timestamp, "ban_level": 0}}
user_tracker = {}


def check_spam(user_id):
  now = time.time()
  if user_id not in user_tracker:
    user_tracker[user_id] = {
        'timestamps': [],
        'ban_until': 0,
        'ban_level': 0,
    }

  data = user_tracker[user_id]

  # Verificar si el usuario está actualmente en período de castigo
  if now < data['ban_until']:
    remaining = int(data['ban_until'] - now)
    return (
        True,
        f'🚫 Estás bloqueado temporalmente por spam. Intenta de nuevo en {remaining} segundos.',
    )

  # Limpiar marcas de tiempo antiguas (mantener solo los últimos 5 segundos)
  data['timestamps'] = [t for t in data['timestamps'] if now - t < 5]
  data['timestamps'].append(now)

  # Si envía más de 5 mensajes en menos de 5 segundos
  if len(data['timestamps']) > 5:
    data['ban_level'] += 1
    if data['ban_level'] == 1:
      return (
          True,
          '⚠️ Estás enviando mensajes demasiado rápido. Por favor, baja el ritmo.',
      )
    elif data['ban_level'] == 2:
      data['ban_until'] = now + 60  # Bloqueo de 1 minuto
      return (
          True,
          '🚫 Has sido bloqueado temporalmente durante **1 minuto** por saturar el chat.',
      )
    else:
      data['ban_until'] = now + 86400  # Bloqueo de 24 horas
      return (
          '🚨 Bloqueo severo: Has reincidido en el spam. Estás sancionado durante **24 horas**.',
      )

  return False, ''


@bot.message_handler(commands=['start'])
def send_welcome(message):
  user_id = message.from_user.id
  is_spam, warning_msg = check_spam(user_id)
  if is_spam and 'bloqueado' in warning_msg:
    bot.reply_to(message, warning_msg)
    return

  name = message.from_user.first_name

  # Crear el botón Inline que abre la Mini App
  markup = InlineKeyboardMarkup()
  markup.add(
      InlineKeyboardButton(
          '✨ Abrir Creador de Telegra.ph', web_app={'url': MINI_APP_URL}
      )
  )

  welcome_text = (
      f'¡Hola, {name}! 👋\n\n'
      'Soy un bot minimalista diseñado exclusivamente para conectar con la Mini App y ayudarte a formatear y publicar artículos en **Telegra.ph** de forma limpia y rápida.\n\n'
      '👉 **Toca el botón de abajo** para abrir la interfaz web y empezar a redactar.'
  )
  bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['help'])
def send_help(message):
  user_id = message.from_user.id
  is_spam, warning_msg = check_spam(user_id)
  if is_spam and 'bloqueado' in warning_msg:
    bot.reply_to(message, warning_msg)
    return

  help_text = (
      'ℹ️ **Información sobre este Bot:**\n\n'
      '• **Qué soy:** Un conector directo a la Mini App de Telegra.ph.\n'
      '• **Qué NO hago:** No soy un chatbot conversacional de IA, no respondo preguntas generales ni charlas.\n'
      '• **Multimedia:** No proceso notas de voz ni imágenes directamente en este chat.\n\n'
      'Usa el comando /start en cualquier momento para desplegar el creador.'
  )
  bot.reply_to(message, help_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: True)
def handle_fallback(message):
  user_id = message.from_user.id
  is_spam, warning_msg = check_spam(user_id)
  if is_spam:
    bot.reply_to(message, warning_msg)
    return

  bot.reply_to(
      message,
      'ℹ️ Este chat solo procesa comandos. Usa /start para abrir el creador o'
      ' /help para ver las reglas.',
  )


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
  json_string = request.get_data().decode('utf-8')
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return '!', 200


@app.route('/')
def index():
  return 'Bot Telegra.ph Mini App activo.'


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
