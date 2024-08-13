import re
import os
import pandas as pd
import collections
from fuzzywuzzy import fuzz
from revcode import revcode_conversion as rc
import collections
from six.moves import zip
import logging

from ner.numeral.constant import NUMBER_NUMERAL_FILE_VARIANTS_COLUMN_NAME, \
    NUMBER_NUMERAL_FILE_VALUE_COLUMN_NAME, NUMBER_NUMERAL_FILE_TYPE_COLUMN_NAME, NUMBER_TYPE_UNIT, \
    NUMBER_NUMERAL_CONSTANT_FILE_NAME, NUMBER_DETECTION_RETURN_DICT_VALUE, NUMBER_DETECTION_RETURN_DICT_SPAN, \
    NUMBER_DETECTION_RETURN_DICT_UNIT, NUMBER_UNITS_FILE_NAME, NUMBER_DATA_FILE_UNIT_VARIANTS_COLUMN_NAME, \
    NUMBER_DATA_FILE_UNIT_VALUE_COLUMN_NAME, NUMBER_TYPE_SCALE, NUMBER_DATA_FILE_UNIT_TYPE_COLUMN_NAME, \
    NUMBER_NUMERAL_FILE_NUMBER_COLUMN_NAME

NumberVariant = collections.namedtuple('NumberVariant', ['scale', 'increment'])
NumberUnit = collections.namedtuple('NumberUnit', ['value', 'type'])

class detect_number():
    SPAN_BOUNDARY_TEMPLATE = r'(?:^|(?<=[\s\"\'\,\-\?])){}(?=[\s\!\"\%\'\,\?\.\-]|$)'
    def __init__(self, entity_name, language, unit_type=None):
        self.text = ''
        self.tagged_text = ''
        self.processed_text = ''
        self.entity_name = entity_name
        self.tag = '__' + entity_name + '__'
        self.base_numbers_map = {}
        self.numbers_word_map = {}
        self.scale_map = {}
        self.units_map = {}
        self.language=language
        self.unit_type = unit_type
        self.init_regex_and_parser(language)
        sorted_len_units_keys = sorted(list(self.units_map.keys()), key=len, reverse=True)
        self.unit_choices = "|".join([re.escape(x) for x in sorted_len_units_keys])
        sorted_len_scale_map = sorted(list(self.scale_map.keys()), key=len, reverse=True)
        self.scale_map_choices = "|".join([re.escape(x) for x in sorted_len_scale_map])
        self.detector_preferences = [self._detect_number_from_digit,
                                     self._detect_number_from_words]
        
    def init_regex_and_parser(self,language):
        data_directory_path=os.path.join("ner","numeral",self.language,"data")
        numeral_df = pd.read_csv(os.path.join(data_directory_path, NUMBER_NUMERAL_CONSTANT_FILE_NAME))
        for _, row in numeral_df.iterrows():
            name_variants = self.get_list_from_pipe_sep_string(row[NUMBER_NUMERAL_FILE_VARIANTS_COLUMN_NAME])
            value = row[NUMBER_NUMERAL_FILE_VALUE_COLUMN_NAME]
            if float(value).is_integer():
                value = int(row[NUMBER_NUMERAL_FILE_VALUE_COLUMN_NAME])
            number_type = row[NUMBER_NUMERAL_FILE_TYPE_COLUMN_NAME]

            if number_type == NUMBER_TYPE_UNIT:
                for numeral in name_variants:
                    self.numbers_word_map[numeral] = NumberVariant(scale=1, increment=value)
                    self.base_numbers_map[numeral] = value

            elif number_type == NUMBER_TYPE_SCALE:
                for numeral in name_variants:
                    self.numbers_word_map[numeral] = NumberVariant(scale=value, increment=0)
                    self.scale_map[numeral] = value
                    self.base_numbers_map[numeral] = value

            number_text = row[NUMBER_NUMERAL_FILE_NUMBER_COLUMN_NAME]
            self.base_numbers_map[number_text] = value


        unit_file_path = os.path.join(data_directory_path, NUMBER_UNITS_FILE_NAME)
        if os.path.exists(unit_file_path):
            units_df = pd.read_csv(unit_file_path)
            if self.unit_type:
                units_df = units_df[units_df[NUMBER_DATA_FILE_UNIT_TYPE_COLUMN_NAME] == self.unit_type]
            for index, row in units_df.iterrows():
                unit_variants = self.get_list_from_pipe_sep_string(row[NUMBER_DATA_FILE_UNIT_VARIANTS_COLUMN_NAME])
                unit_value = row[NUMBER_DATA_FILE_UNIT_VALUE_COLUMN_NAME]
                unit_type = row[NUMBER_DATA_FILE_UNIT_TYPE_COLUMN_NAME]
                for unit in unit_variants:
                    self.units_map[unit] = NumberUnit(value=unit_value, type=unit_type) 

    def _detect_number_from_words(self, number_list=None, original_list=None):
        number_list = number_list or []
        original_list = original_list or []
        end_span = -1
        spans = []
        spanned_text = self.text
        numeral_text_list = re.split(r'[\-\:]', self.processed_text)
        for numeral_text in numeral_text_list:
            numbers, original_texts = self.get_number_from_number_word(numeral_text, self.numbers_word_map)
            for original in original_texts:
                span = re.search(original, spanned_text).span()
                start_span = end_span + span[0]
                end_span += span[1]
                spanned_text = spanned_text[span[1]:]
                spans.append((start_span, end_span))
            full_list = list(zip(numbers, original_texts, spans))
            sorted_full_list = sorted(full_list, key=lambda kv: len(kv[2]), reverse=False)
            for number, original_text, span in sorted_full_list:
                unit = None
                if self.unit_type:
                    unit, original_text = self._get_unit_from_text(original_text, numeral_text)
                _pattern = re.compile(self.SPAN_BOUNDARY_TEMPLATE.format(re.escape(original_text)))
                if _pattern.search(numeral_text):
                    numeral_text = _pattern.sub(self.tag, numeral_text, 1)
                    number_list.append({
                        NUMBER_DETECTION_RETURN_DICT_VALUE: str(number),
                        NUMBER_DETECTION_RETURN_DICT_UNIT: unit,
                        NUMBER_DETECTION_RETURN_DICT_SPAN: span
                    })
                    original_list.append(original_text)
        return number_list, original_list
    
    def _get_unit_from_text(self, detected_original, processed_text):
        unit = None
        original_text = detected_original

        if not self.units_map:
            return unit, original_text

        processed_text = " " + processed_text.strip() + " "
        detected_original = re.escape(detected_original)
        found=False
        key_to_be_replaced=""
        token_to_rollback=""
        if self.language != 'en': 
            for token in processed_text.split():
                for key in self.units_map.keys():
                    if fuzz.ratio(rc.to_revcode(token,self.language).lower(),rc.to_revcode(key,self.language).lower()) >=80:
                        processed_text=re.sub(token,key,processed_text)
                        token_to_rollback=token
                        key_to_be_replaced=key
                        found=True
                    if found:
                        break
                if found:
                    break
        
        unit_matches = re.search(r'\W+((' + self.unit_choices + r')[.,\s]*' + detected_original + r')\W+|\W+(' +
                                 detected_original + r'\s*(' +
                                 self.unit_choices + r'))\W+',
                                 processed_text,
                                 re.UNICODE)
        if unit_matches:
            original_text_prefix, unit_prefix, original_text_suffix, unit_suffix = unit_matches.groups()
            if unit_suffix:
                unit = self.units_map[unit_suffix.strip()].value
                original_text = original_text_suffix.strip()
                original_text=re.sub(key_to_be_replaced,token_to_rollback,original_text_suffix)
            elif unit_prefix:
                unit = self.units_map[unit_prefix.strip()].value
                original_text = original_text_prefix.strip()
                original_text=re.sub(key_to_be_replaced,token_to_rollback,original_text_prefix)

        return unit, original_text


    def get_number_from_number_word(self,text, number_word_dict):
        detected_number_list = []
        detected_original_text_list = []

        number_word_dict = {word: number_map for word, number_map in number_word_dict.items()
                            if (len(word) > 1 and number_map.increment == 0) or number_map.scale == 1}
        text = text.strip()
        if not text:
            return detected_number_list, detected_original_text_list

        whitespace_pattern = re.compile(r'(\s+)', re.UNICODE)
        parts = []
        _parts = whitespace_pattern.split(u' ' + text)
        for i in range(2, len(_parts), 2):
            parts.append(_parts[i - 1] + _parts[i])

        current = result = 0
        current_text, result_text = '', ''
        on_number = False
        prev_digit_len = 0
        prev_scale = 0
        is_double_or_triple = False

        for part in parts:
            word = part.strip()

            if word not in number_word_dict:
                if on_number:
                    result_text += current_text
                    original = result_text.strip()
                    number_detected = result + current
                    if float(number_detected).is_integer():
                        number_detected = int(number_detected)
                    detected_number_list.append(number_detected)
                    detected_original_text_list.append(original)

                result = current = 0
                result_text, current_text = '', ''
                on_number = False
            else:
                scale, increment = number_word_dict[word].scale, number_word_dict[word].increment
                if scale % 100 == 11:
                    is_double_or_triple = True
                    prev_scale = scale
                    continue
                if prev_scale > 1 and not prev_scale < scale:
                    result += current
                    result_text += current_text
                    current = 0
                    current_text = ''

                digit_len = max(len(str(int(increment))), len(str(scale)))

                if digit_len == prev_digit_len:
                    if on_number:
                        result_text += current_text
                        original = result_text.strip()
                        number_detected = result + current
                        if float(number_detected).is_integer():
                            number_detected = int(number_detected)
                        detected_number_list.append(number_detected)
                        detected_original_text_list.append(original)

                    result = current = 0
                    result_text, current_text = '', ''

                if digit_len > prev_digit_len:
                    if on_number and prev_scale == scale:
                        current = current * (10 ** digit_len)

                if is_double_or_triple:
                    scale = prev_scale
                    current = increment
                    increment = 0
                    is_double_or_triple = False
                current = 1 if (scale > 1 and current == 0 and increment == 0) else current
                current = current * scale + increment
                current_text += part
                if scale > 1:
                    result += current
                    result_text += current_text
                    current = 0
                    current_text = ''
                on_number = True
                prev_digit_len = digit_len
                prev_scale = scale

        if on_number:
            result_text += current_text
            original = result_text.strip()
            number_detected = result + current
            if float(number_detected).is_integer():
                number_detected = int(number_detected)
            detected_number_list.append(number_detected)
            detected_original_text_list.append(original)

        return detected_number_list, detected_original_text_list

    def get_list_from_pipe_sep_string(self,text_string):
        text_list = text_string.split("|")
        return [x.lower().strip() for x in text_list if x.strip()]


    def _detect_number_from_digit(self, number_list=None, original_list=None):
        
        number_list = number_list or []
        original_list = original_list or []
        processed_text = self.processed_text
        start_span = 0
        end_span = -1
        spanned_text = self.processed_text
        regex_numeric_patterns = re.compile(r'(([\d,]+\.?[\d]*)\s?(' + self.scale_map_choices + r'))[\s\-\:]' +
                                            r'|([\d,]+\.?[\d]*)', re.UNICODE)
        patterns = regex_numeric_patterns.findall(processed_text)
        for pattern in patterns:
            number, scale, original_text = None, None, None
            if pattern[1] and pattern[1].replace(',', '').replace('.', '').isdigit():
                number = pattern[1].replace(',', '')
                original_text = pattern[0].strip().strip(',.').strip()
                scale = self.scale_map[pattern[2].strip()]
                span = re.search(original_text, spanned_text).span()
                start_span = end_span + span[0]
                end_span += span[1]
                spanned_text = spanned_text[span[1]:]

            elif pattern[3] and pattern[3].replace(',', '').replace('.', '').isdigit():
                number = pattern[3].replace(',', '')
                original_text = pattern[3].strip().strip(',.').strip()
                scale = 1
                span = re.search(original_text, spanned_text).span()
                start_span = end_span + span[0]
                end_span += span[1]
                spanned_text = spanned_text[span[1]:]

            if number:
                if '.' not in number:
                    number = int(number) * scale
                else:
                    number = float(number) * scale
                    # FIXME: this conversion from float -> int is lossy, consider using Decimal class
                    number = int(number) if number.is_integer() else number
                unit = None
                if self.unit_type:
                    unit, original_text = self._get_unit_from_text(original_text, processed_text)
                _pattern = re.compile(self.SPAN_BOUNDARY_TEMPLATE.format(re.escape(original_text)))
                if _pattern.search(processed_text):
                    processed_text = _pattern.sub(self.tag, processed_text, 1)
                    number_list.append({
                        NUMBER_DETECTION_RETURN_DICT_VALUE: str(number),
                        NUMBER_DETECTION_RETURN_DICT_UNIT: unit,
                        NUMBER_DETECTION_RETURN_DICT_SPAN: (start_span, end_span)
                    })
                    original_list.append(original_text)

        return number_list, original_list
    
    def _update_processed_text(self, original_number_list):
        for detected_text in original_number_list:
            _pattern = re.compile(self.SPAN_BOUNDARY_TEMPLATE.format(re.escape(detected_text)))
            self.tagged_text = _pattern.sub(self.tag, self.tagged_text, 1)
            self.processed_text = _pattern.sub('', self.processed_text, 1)

    def detect_number(self, text):
        def _pop_key_from_dict(xdict, key_name):
            temp_dict = xdict.copy()
            temp_dict.pop(key_name, None)
            return temp_dict
        self.text = text
        self.processed_text = text
        self.tagged_text = text

        number_list, original_list = None, None
        for detector in self.detector_preferences:
            number_list, original_list = detector(number_list, original_list)
            self._update_processed_text(original_list)
        sorted_number_list = [_pop_key_from_dict(num_dict, NUMBER_DETECTION_RETURN_DICT_SPAN) for num_dict in
                              sorted(number_list,
                                     key=lambda n: n[NUMBER_DETECTION_RETURN_DICT_SPAN],
                                     reverse=False)]
        sorted_original_list = [x for _, x in sorted(zip(number_list, original_list),
                                                     key=lambda num: num[0][NUMBER_DETECTION_RETURN_DICT_SPAN],
                                                     reverse=False)]
        return sorted_number_list, sorted_original_list

# object1=detect_number(entity_name="number",language="en",unit_type=None)
# print(object1.detect_number("Hello my number is 1000"))