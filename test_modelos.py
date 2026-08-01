import google.generativeai as genai
from src.config import API_KEY

genai.configure(api_key=API_KEY)

print("--- MODELOS GEMINI FLASH DISPONIBLES ---")
for m in genai.list_models():
    if (
        "generateContent" in m.supported_generation_methods
        and "flash" in m.name.lower()
    ):
        print(m.name)