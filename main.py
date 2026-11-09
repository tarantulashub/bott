import os
from flask import Flask, request
import telebot

# Recupera el token de forma segura desde las variables de entorno de Render
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# Configura la respuesta al comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
  bot.reply_to(
      message,
      '¡Hola! Bienvenido a mi bot. Gracias por iniciar esta conversación.',
  )


# Ruta que escucha los mensajes que envía Telegram (Webhook)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
  json_string = request.get_data().decode('utf-8')
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return '!', 200


# Ruta de comprobación para saber que el servidor está activo
@app.route('/')
def index():
  op = 'El bot de Telegram está funcionando correctamente.'
  return op


if __name__ == '__main__':
  # Render asigna dinámicamente un puerto mediante la variable PORT
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
