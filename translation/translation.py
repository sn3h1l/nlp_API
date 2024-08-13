import requests
import json
# from constants.constant import REVERIE_TRANSLATE_URL,REV_API_KEY,REV_APP_ID
class Translate():
    def __init__(self) -> None:
        pass
    def translate(self,text,source_lang,target_lang):
        url = "https://revapi.reverieinc.com/translate"
        payload = json.dumps({
        "data": [text],
        "src": source_lang,
        "tgt": target_lang,
        "NER": False,
        "mask": False,
        "filter_profane": False,
        "domain": 1,
        "logging": True
        })
        headers = {
        'REV-API-KEY': '05c4d964e369f8a6acf34b7dba474c0b23b7670a',
        'REV-APP-ID': 'rev.prod.prabandhak.nmt',
        'REV-APPNAME': 'nmt',
        'Content-Type': 'application/json'
         }
        response = requests.request("POST", url, headers=headers, data=payload)
        resp=response.json()
        return str(resp["result"])
# print(Translate().translate("hi from India","en","hi"))
