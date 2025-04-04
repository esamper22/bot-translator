from google import genai
from dotenv import load_dotenv
import os
import asyncio
from typing import Literal

# Carga variables de entorno
load_dotenv()

# Configuración de API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Aunque no se use, se mantiene por si se necesita

async def translate_text(text: str, origin_lang: Literal['es', 'en'] = 'es', destiny_lang: Literal['en', 'es'] = 'en') -> str:
    """
    Traduce texto entre inglés y español, con formato Markdown para Telegram.
    
    :param text: El texto a traducir.
    :param origin_lang: El idioma original ('es' para español, 'en' para inglés).
    :param destiny_lang: El idioma destino ('en' para inglés, 'es' para español).
    :return: Texto traducido con formato Markdown.
    """
    
    # Validación de idiomas soportados
    if destiny_lang not in ['en', 'es']:
        raise ValueError("Solo se admite 'en' (inglés) y 'es' (español)")
    
    # Configuración del cliente Gemini
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        # Ejecución asíncrona usando run_in_executor para evitar bloqueos
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.generate_content(
                f"Traduce este texto al {destiny_lang}: {text}",
                model="gemini-2.0-flash"
            )
        )
        
        # Procesamiento del texto traducido
        translated_text = response.text.strip()
        return translated_text
    
    except Exception as e:
        # Manejo de errores generales
        return f"Error durante la traducción: {e}"

# Ejemplo de uso
async def main():
    text_to_translate = "Hola, ¿cómo estás?"
    translated = await translate_text(text_to_translate)
    print(f"Texto traducido: {translated}")

# Ejecución del programa principal
if __name__ == "__main__":
    asyncio.run(main())
