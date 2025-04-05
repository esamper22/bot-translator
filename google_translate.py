from google import genai
from dotenv import load_dotenv
import os

# Especificando la ruta al archivo .env
dotenv_path = os.path.join('bot-translator', '.env')
load_dotenv(dotenv_path)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def translate_text(text, origin_lang='es', destiny_lang='en'):
    """
    Translates text between English and Spanish only, with Markdown formatting for Telegram.
    :param text: The text to translate.
    :param target_language: The target language ('en' for English, 'es' for Spanish).
    :return: Translated text with Markdown formatting.
    """
    if destiny_lang not in ['en', 'es']:
        raise ValueError("Only 'en' (English) and 'es' (Spanish) are supported.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Only Translate the following text to {destiny_lang}: {text}",
        )
        translated_text = response.text.strip()
        return translated_text
    except Exception as e:
        return f"Error durante la traducción: {e}"

if __name__ == "__main__":
    print(translate_text("Hola me llamo Ernesto!"))
