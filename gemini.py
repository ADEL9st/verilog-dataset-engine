import os
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") 
client = genai.Client(api_key=API_KEY)

print("Sadece (veya öncelikli) Metin İşleyen Modeller:\n" + "-"*50)

for m in client.models.list():
    # 1. Metin üretme yeteneği var mı?
    # 2. Desteklediği MIME tiplerinde 'image/png' veya 'image/jpeg' YOK MU?
    
    supports_text = "generateContent" in m.supported_actions
    supports_image = any("image" in mime for mime in getattr(m, 'supported_input_mime_types', []))

    if supports_text and not supports_image:
        print(f"Saf Metin Modeli: {m.name}")
    elif supports_text:
        # Bunlar hem metin hem görsel işleyebilen (Gemini 1.5 gibi) modellerdir
        print(f"Karma (Metin+Görsel) Model: {m.name}")