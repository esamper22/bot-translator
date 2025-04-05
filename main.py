import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google_translate import translate_text
import logging

logging.basicConfig(level=logging.DEBUG)

# Especificando la ruta al archivo .env
dotenv_path = os.path.join('bot-translator', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
LANG_FILE = "bot-translator/user_languages.json"

# Inicializamos el bot y la app Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)
app = Flask(__name__)

# Configurar URL del webhook
webhook_url = 'https://sampere0111.pythonanywhere.com/webhook'
bot.remove_webhook()
bot.set_webhook(url=webhook_url)


def load_languages():
    try:
        with open(LANG_FILE, "r") as file:
            data = file.read()
            return json.loads(data) if data.strip() else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_languages(data):
    with open(LANG_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Cargamos los idiomas de los usuarios desde el archivo JSON
user_lang = load_languages()

# Mensajes de configuración según idioma
MESSAGES = {
    "set_native": {"en": "Select your native language:", "es": "Selecciona tu idioma nativo:"},
    "set_destiny": {"en": "Select the language you want to receive messages in:", "es": "Selecciona el idioma en el que deseas recibir los mensajes:"},
    "lang_configured": {"en": "Configuration completed.\nNative: {native}\nDestination: {destiny}",
                        "es": "Configuración completada.\nNativo: {native}\nDestino: {destiny}"},
    "config_error": {"en": "Please complete your language configuration.",
                     "es": "Por favor, completa la configuración de tu idioma."},
    "person_limit": {"en": "This bot is designed for group conversations.",
                    "es": "Este bot está diseñado para conversaciones en grupo."},
    "bot_status": {"en": "Bot is online!", "es": "¡El bot está en línea!"}
}

# Opciones de idioma para botones según preferencia
LANGUAGE_OPTIONS = {
    "en": [("English", "en"), ("Spanish", "es")],
    "es": [("Inglés", "en"), ("Español", "es")]
}

def get_preferred_lang(message):
    """Retorna 'es' si el language_code de Telegram empieza con 'es', sino 'en'."""
    lang = message.from_user.language_code if message.from_user.language_code else "en"
    return "es" if lang.startswith("es") else "en"

def request_configuration(user_id, chat_id, preferred):
    """Envía botones para que el usuario configure su idioma."""
    markup = InlineKeyboardMarkup()
    for lang_name, lang_code in LANGUAGE_OPTIONS[preferred]:
        markup.add(InlineKeyboardButton(lang_name, callback_data=f"native_{lang_code}"))
    bot.send_message(chat_id, MESSAGES["set_native"][preferred], reply_markup=markup)

@bot.message_handler(func=lambda message: message.text and message.text.strip(), content_types=['text'])
def handle_message(message):
    global user_lang
    user_lang = load_languages()
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    preferred = get_preferred_lang(message)

    print(f"Mensaje recibido de {user_id}: {message.text}")
    print(f"Configuración de idiomas: {user_lang}")

    bot.send_chat_action(chat_id, 'typing')

    if user_id not in user_lang or "native" not in user_lang[user_id]:
        request_configuration(user_id, chat_id, preferred)
        return

    sender_native = user_lang[user_id].get("native", "en")
    sender_destiny = user_lang[user_id].get("destiny", "en")
    translated_messages = []

    # Traducir mensaje para el remitente
    try:
        if sender_native != sender_destiny:  # Solo traducir si los idiomas son diferentes
            translation = translate_text(message.text, origin_lang=sender_native, destiny_lang=sender_destiny)
            translated_messages.append(f"{message.from_user.first_name} ({sender_destiny}): {translation}")
        else:
            bot.send_message(chat_id,"El idioma nativo y de destino son iguales; no se realiza traducción.")

    except Exception as e:
        bot.send_message(chat_id,f"Error")

    if translated_messages:
        bot.send_message(chat_id, "\n".join(translated_messages))
    else:
        bot.send_message(chat_id, f"Error.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("native_"))
def handle_native(call):
    native_lang = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    if user_id not in user_lang:
        user_lang[user_id] = {}
    user_lang[user_id]["native"] = native_lang
    save_languages(user_lang)

    preferred = "es" if native_lang == "es" else "en"
    markup = InlineKeyboardMarkup()
    for lang_name, lang_code in LANGUAGE_OPTIONS[preferred]:
        if lang_code != native_lang:
            markup.add(InlineKeyboardButton(lang_name, callback_data=f"destiny_{lang_code}"))
    bot.send_message(call.message.chat.id, MESSAGES["set_destiny"][preferred], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("destiny_"))
def handle_destiny(call):
    destiny_lang = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    if user_id not in user_lang:
        user_lang[user_id] = {}
    user_lang[user_id]["destiny"] = destiny_lang
    save_languages(user_lang)
    preferred = "es" if user_lang[user_id].get("native", "en") == "es" else "en"
    msg = MESSAGES["lang_configured"][preferred].format(native=user_lang[user_id]["native"], destiny=destiny_lang)
    bot.send_message(call.message.chat.id, msg)

# Envía un mensaje al grupo indicando que el bot está en línea
@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, MESSAGES["bot_status"][get_preferred_lang(message)])

# --- Fin de Handlers ---

# --- Rutas de Flask ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('Content-Type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
        bot.process_new_updates([update])
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'error': 'Tipo de contenido no válido'}), 400

@app.route("/", methods=["GET"])
def status():
    """Endpoint para comprobar que la aplicación está en línea."""
    return jsonify({"status": "Bot is online!"})

# --- Fin de Rutas ---