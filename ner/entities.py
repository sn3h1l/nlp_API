
import os
import sys
from ner.date.date import detect_date
from ner.numeral.number import detect_number
from ner.Time.indic_time import detect_indic_time
from ner.Time.english_time import detect_english_time
from ner.phone_number.phno import detect_phone_number
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Detector():
    def __init__(self,text,language):
        self.text=text
        self.language=language
        if language == 'en':
             self.time_detector = detect_english_time(entity_name="time")
        else:   
            self.time_detector=detect_indic_time(entity_name="time",language=language)

        self.date_detector=detect_date(entity_name="date",language=language)
        self.number_detector=detect_number(entity_name="'Number",language=language,unit_type=None)
        self.amount_detector=detect_number(entity_name="Amount",language=language,unit_type="currency")
        self.phn_detector=detect_phone_number(entity_name="Phone_Number",language=language)

    def detect(self):
        result={}
        time_list=self.time_detector.detect_time(self.text)
        number_list=self.number_detector.detect_number(self.text)
        date_list=self.date_detector.detect_date(self.text)
        amount_list=self.amount_detector.detect_number(self.text)
        phone_list=self.phn_detector.detect_entity(self.text)
        result["time"]=time_list
        result["number"]=number_list
        result["date"]=date_list
        result["amount"]=amount_list
        result["phone_number"]=phone_list
        return result

# obj1=Detector(text="गौरव कल सुबह 10 बजे ऑफिस के लिए निकलेगा और उसके पास 1000 रुपये हैं",language='hi')
# print(obj1.detect())
