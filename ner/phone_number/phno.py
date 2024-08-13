import re
import phonenumbers
from six.moves import zip
try:
    import regex
    _regex_available = True
except ImportError:
    _regex_available = False

class detect_phone_number():
    def __init__(self, entity_name, language='en', locale=None):

        self.language = language
        self.locale = locale or 'en-IN'
        if _regex_available:
            self.locale = regex.sub('\\p{Pd}', '-', self.locale)
        self.text = ''
        self.phone, self.original_phone_text = [], []
        self.country_code = self.get_country_code_from_locale()
        self.entity_name = entity_name
        self.tag = '__' + self.entity_name + '__'

    def get_country_code_from_locale(self):
        regex_pattern = re.compile('[-_](.*$)', re.U)
        match = regex_pattern.findall(self.locale)
        if match:
            return match[0].upper()
        else:
            return 'IN'
    def detect_entity(self, text, **kwargs):
        self.text = " " + text.lower().strip() + " "
        self.phone, self.original_phone_text = [], []
        for match in phonenumbers.PhoneNumberMatcher(self.text, self.country_code, leniency=0):
            if match.number.country_code == phonenumbers.country_code_for_region(self.country_code):
                self.phone.append(self.check_for_country_code(str(match.number.national_number)))
                self.original_phone_text.append(self.text[match.start:match.end])
            else:
                self.phone.append({"country_calling_code": str(match.number.country_code),
                                   "value": str(match.number.national_number)})
                self.original_phone_text.append(self.text[match.start:match.end])
        self.phone, self.original_phone_text = self.check_for_alphas()
        return self.phone, self.original_phone_text

    def check_for_alphas(self):
        validated_phone = []
        validated_original_text = []
        for phone, original in zip(self.phone, self.original_phone_text):
            if re.search(r'\W' + re.escape(original) + r'\W', self.text, re.UNICODE):
                validated_phone.append(phone)
                validated_original_text.append(original)
        return validated_phone, validated_original_text

    def check_for_country_code(self, phone_num):
        phone_dict = {}

        if len(phone_num) >= 10:
            check_country_regex = re.compile(r'^({country_code})\d{length}$'.
                                             format(country_code='911|1|011 91|91', length='{10}'), re.U)
            p = check_country_regex.findall(phone_num)
            if len(p) == 1:
                phone_dict['country_calling_code'] = p[0]
                country_code_sub_regex = re.compile(r'^{detected_code}'.format(detected_code=p[0]))
                phone_dict['value'] = country_code_sub_regex.sub(string=phone_num, repl='')
            else:
                phone_dict['country_calling_code'] = str(phonenumbers.country_code_for_region(self.country_code))
                phone_dict['value'] = phone_num
        else:
            # phone_dict['country_calling_code'] = str(phonenumbers.country_code_for_region(self.country_code))
            # phone_dict['value'] = phone_num
            pass
        return phone_dict

# object1=PhoneDetector(entity_name="phn no",language='en')
# print(object1.detect_entity(text=" 85956152"))