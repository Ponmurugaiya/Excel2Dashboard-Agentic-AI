"""
Gemini API test — uses google-generativeai (installed in .venv).
Run with:
    .venv\Scripts\python gemini_test.py
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load GEMINI_API_KEY and GEMINI_MODEL from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env file: GEMINI_API_KEY=AIza..."
    )

model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Configure the SDK
genai.configure(api_key=api_key)

# Build the model
model = genai.GenerativeModel(
    model_name=model_name,
    generation_config=genai.GenerationConfig(
        temperature=0.2,
        max_output_tokens=256,
    ),
)

print(f"Model  : {model_name}")
print(f"Prompt : Explain how AI works in a few words")
print("-" * 40)

response = model.generate_content("Explain how AI works in a few words")

print(response.text)
