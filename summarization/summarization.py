import json
import ollama
import requests

class Text_Summarizer():
    def __init__(self) -> None:
        pass
    def summarize(self,text, lang, model,summary_type):
        indian_languages = {
        "hi": "Hindi",
        "en": "English",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "ml": "Malayalam",
        "kn": "Kannada",
        "gu": "Gujarati",
        "mr": "Marathi",
        "or": "Odia",
        "pa": "Punjabi",
        "as": "Assamese",
        "ur": "Urdu",
        "sd": "Sindhi",
        "sa": "Sanskrit",
        }
        print(f"Summarizing")
        response = ollama.chat(model=model, 
        messages=[
             {
            'role': 'system',
            'content': f'Your goal is to summarize the text given to you in roughly 10 words. Basically I need a {summary_type} type of summary. In {indian_languages[lang]} language.'
            },
             {
            'role': 'user',
            'content': text,
            },
        ]) 
        return response['message']['content']
    
# object1=Text_Summarizer()
# print(object1.summarize("Hello my name is Snehil and this is me testing my new venv file that should prolly work now as i have fixed the new env and downloaded the new requirements","en","gemma2:2b","headline"))
