from textblob import TextBlob
from deep_translator import GoogleTranslator
from langdetect import detect
import re

# Detect only English or Urdu (no Roman Urdu)
def detect_language(text):
    try:
        lang = detect(text)
        if lang == 'en':
            return "english"
        elif lang == 'ur':
            return "urdu"
        else:
            # Extra fallback based on Unicode ranges for Urdu script
            if re.search(r'[\u0600-\u06FF]', text):
                return "urdu"
            else:
                return "english"
    except:
        return "english"


# Translate Urdu → English (for model input)
def translate_urdu_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text

# Translate English → Urdu (for response)
def translate_to_urdu(text):
    try:
        return GoogleTranslator(source='en', target='ur').translate(text)
    except:
        return text
