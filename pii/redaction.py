import json
import requests
from ner.entities import Detector
from constants.constant import INDOCORD_NER_URL
class PII_Redactor:
    def __init__(self) -> None:
        pass
    def hide_details(self, text, redact_pii_types='hash'):
        entities_found = self.get_from_indocord_ner(text)
        redaction_results = []
        
        for ent in entities_found:
            if redact_pii_types == 'entity_names':
                replacement = f"[{ent[1][0:3]}]"
            else: 
                replacement = "#" * len(ent[0])
            
            text = text.replace(ent[0], replacement)
            redaction_results.append({
                'pii_type': ent[1][0:3],
                'text': ent[0],
                'confidence': ent[1].split('_')[1]
            })
        
        return text, redaction_results

    def get_from_indocord_ner(self,text):
        url = INDOCORD_NER_URL
        payload = json.dumps({
            "text": text
        })
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        resp = response.json()
        entities = []
        for ent in resp["entities"]:
            x = list(ent.items())
            if len(x) > 0:
                for item in x:
                    word = item[0]
                    score = "_".join([str(c) for c in item[1]])
                    entities.append((word, score))
        return entities
    
object1=PII_Redactor()
print(object1.hide_details(text="Hello my name is Snehil and I live in Bengaluru and I work at Reverie"))