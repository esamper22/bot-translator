import os
import json
import asyncio
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from google_translate import translate_text  # Se asume que esta función es asíncrona

load_dotenv()

# Variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN')  # Token para proteger la ruta del webhook
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Inicializamos el bot y la app Flask
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

LANG_FILE = "user_languages.json"

def load_languages():
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as file:
            data = file.read()
            return json.loads(data) if data.strip() else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_languages(data):
    with open(LANG_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Cargamos los idiomas de los usuarios
user_lang = load_languages()

# Mensajes de configuración
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

# Opciones de idioma para botones
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

# --- Handlers del bot ---

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
        print(f"Usuario {user_id} necesita configuración")
        request_configuration(user_id, chat_id, preferred)
        return

    sender_native = user_lang[user_id].get("native", "en")
    sender_destiny = user_lang[user_id].get("destiny", "en")
    translated_messages = []

    print(f"Traduciendo mensaje de {sender_native} a {sender_destiny}")

    try:
        if sender_native != sender_destiny:
            # Se ejecuta la función asíncrona en un contexto síncrono
            translation = asyncio.run(translate_text(message.text, origin_lang=sender_native, destiny_lang=sender_destiny))
            print(f"Traducción exitosa a {sender_destiny}: {translation}")
            translated_messages.append(f"{message.from_user.first_name} ({sender_destiny}): {translation}")
        else:
            print("El idioma nativo y de destino son iguales; no se realiza traducción.")
    except Exception as e:
        print(f"Error de traducción: {e}")

    if translated_messages:
        print(f"Mensajes traducidos: {translated_messages}")
        bot.send_message(chat_id, "\n".join(translated_messages))
    else:
        print("No se pudieron generar traducciones")

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

@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, MESSAGES["bot_status"][get_preferred_lang(message)])

# --- Fin de Handlers ---

# --- Rutas de Flask ---

@app.route("/webhook/<token>", methods=["POST"])
def webhook(token):
    """
    Endpoint para recibir actualizaciones de Telegram.
    Se incluye el token en la URL para mayor seguridad.
    """
    if token != WEBHOOK_TOKEN:
        abort(403, description="Token inválido")
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data)
    bot.process_new_updates([update])
    return jsonify({"status": "ok"})

@app.route("/status", methods=["GET"])
def status():
    """Endpoint para comprobar que la aplicación está en línea."""
    return jsonify({"status": "Bot is online!"})

# --- Fin de Rutas ---

if __name__ == "__main__":
    # En PythonAnywhere, asegúrate de que el puerto esté configurado correctamente.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
