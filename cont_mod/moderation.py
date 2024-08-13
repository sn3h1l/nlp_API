import os
import re
import sys
import os
import os
from pathlib import Path
from constants.constant import DIRECTORY_MODERATION,LANGUAGE_DIRECTORY_MODERATION
class Text_Moderator():
    def __init__(self):
        pass
    

    def read_language_file(self,directory,language_code):
        lines = []
        file_pattern = f"bad_word.{language_code}"
        # Look for the file in the directory
        for filename in os.listdir(directory):
            if filename == file_pattern:
                file_path = Path(directory) / filename
                try:
                    with open(file_path, 'r') as file:
                        lines = file.read().splitlines()
                    break 
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")
    
        return lines

    def moderate_text(self,lang_input,text):
        moderation_results = []
        directory = "cont_mod/bad_word"
        bad_words_list = self.read_language_file(directory,lang_input)
        replacement_text = text
        for string_token in replacement_text.split():
            if string_token in bad_words_list:
                replacement_text = replacement_text.replace(string_token, '*' * len(string_token))
                moderation_results.append({"moderation_type": "abuse",
                    "text": string_token,
                    "confidence": 1.00})
        return replacement_text,moderation_results
