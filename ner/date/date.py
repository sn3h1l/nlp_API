from __future__ import absolute_import
import datetime
import re
from dateutil.relativedelta import relativedelta
import logging
from fuzzywuzzy import fuzz
from revcode import revcode_conversion as rc
import os
from ner.date.utils import next_weekday, nth_weekday, get_tuple_dict, get_timezone
from ner.date.constant import (DATE_CONSTANT_FILE, DATETIME_CONSTANT_FILE,
                                                RELATIVE_DATE, DATE_LITERAL_TYPE, MONTH_LITERAL_TYPE, WEEKDAY_TYPE,
                                                MONTH_TYPE, ADD_DIFF_DATETIME_TYPE, MONTH_DATE_REF_TYPE,
                                                NUMERALS_CONSTANT_FILE, TYPE_EXACT)
class detect_date(object):
    
    def __init__(self, entity_name,language, locale=None, timezone='UTC', past_date_referenced=False):
        logging.basicConfig(filename="final_test.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
        # print(f" in{os.getcwd()}")
        self.logger= logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.info(f"main class init")
        # print(f"cwd --> {os.getcwd()}")
        self.text = ''
        self.tagged_text = ''
        self.processed_text = ''
        self.date = []
        self.original_date_text = []
        self.entity_name = entity_name
        self.tag = '__' + entity_name + '__'
        self.timezone = get_timezone(timezone)
        self.language=language
        self.now_date = datetime.datetime.now(tz=self.timezone)
        self.bot_message = None

        self.past_date_referenced = past_date_referenced

        # dict to store words for date, numerals and words which comes in reference to some date
        self.date_constant_dict = {}
        self.datetime_constant_dict = {}
        self.numerals_constant_dict = {}

        # define dynamic created standard regex from language data files
        self.regex_relative_date = None
        self.regex_day_diff = None
        self.regex_date_month = None
        self.regex_date_ref_month_1 = None
        self.regex_date_ref_month_2 = None
        self.regex_date_ref_month_3 = None
        self.regex_after_days_ref = None
        self.regex_weekday_month_1 = None
        self.regex_weekday_month_2 = None
        self.regex_weekday_diff = None
        self.regex_weekday = None
        # Method to initialise value in regex
        self.init_regex_and_parser()
        self.detector_preferences = [self._gregorian_day_month_year_format,
                                     self._detect_relative_date,
                                     self._detect_date_month,
                                     self._detect_date_ref_month_1,
                                     self._detect_date_ref_month_2,
                                     self._detect_date_ref_month_3,
                                     self._detect_date_diff,
                                     self._detect_after_days,
                                     self._detect_weekday_ref_month_1,
                                     self._detect_weekday_ref_month_2,
                                     self._detect_weekday_diff,
                                     self._detect_weekday
                                     ]
    
    def init_regex_and_parser(self):
        data_directory_path=os.path.join("ner","date",self.language,"data")
        self.date_constant_dict = get_tuple_dict(data_directory_path.rstrip('/') + '/' + DATE_CONSTANT_FILE)
        self.datetime_constant_dict = get_tuple_dict(data_directory_path.rstrip('/') + '/' + DATETIME_CONSTANT_FILE)
        self.numerals_constant_dict = get_tuple_dict(data_directory_path.rstrip('/') + '/' + NUMERALS_CONSTANT_FILE)

        relative_date_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == RELATIVE_DATE])) + ")"
        self.logger.info(f"relative_date_choices --> {relative_date_choices}")

        date_literal_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == DATE_LITERAL_TYPE])) + ")"
        self.logger.info(f"date_literal_choices --> {date_literal_choices}")
        
        month_ref_date_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == MONTH_DATE_REF_TYPE])) + ")"
        self.logger.info(f"month_ref_date_choices --> {month_ref_date_choices}")

        month_literal_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == MONTH_LITERAL_TYPE])) + ")"
        self.logger.info(f"month_literal_choices --> {month_literal_choices}")
        
        weekday_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == WEEKDAY_TYPE])) + ")"
        self.logger.info(f"weekday_choices --> {weekday_choices}")

        month_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.date_constant_dict if x.strip() != "" and
             self.date_constant_dict[x][1] == MONTH_TYPE])) + ")"
        self.logger.info(f"month_choices --> {month_choices}")
        
        datetime_diff_choices = "(" + "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.datetime_constant_dict if x.strip() != "" and
             self.datetime_constant_dict[x][2] == ADD_DIFF_DATETIME_TYPE])) + ")"
        self.logger.info(f"datetime_diff_choices --> {datetime_diff_choices}")
        
        numeral_variants = "|".join(self._sort_choices_on_word_counts(
            [x.lower() for x in self.numerals_constant_dict if x.strip() != ""]))
        self.logger.info(f"numeral_variants --> {numeral_variants}")

        # Date detector Regex
        self.regex_relative_date = re.compile((r'(' + relative_date_choices + r')'), flags=re.UNICODE)

        self.regex_day_diff = re.compile(r'(' + datetime_diff_choices + r'\s*' + date_literal_choices + r')',
                                         flags=re.UNICODE)

        self.regex_date_month = re.compile(r'((\d+|' + numeral_variants + r')\s*(st|nd|th|rd|)\s*' +
                                           month_choices + r')', flags=re.UNICODE)

        self.regex_date_ref_month_1 = \
            re.compile(r'((\d+|' + numeral_variants + r')\s*' + month_ref_date_choices + '\\s*' +
                       datetime_diff_choices + r'\s*' + month_literal_choices + r')', flags=re.UNICODE)

        self.regex_date_ref_month_2 = \
            re.compile(r'(' + datetime_diff_choices + r'\s*' + month_literal_choices + r'\s*[a-z]*\s*(\d+|' +
                       numeral_variants + r')\s+' + month_ref_date_choices + r')', flags=re.UNICODE)

        self.regex_date_ref_month_3 = \
            re.compile(r'((\d+|' + numeral_variants + r')\s*' + month_ref_date_choices + r')', flags=re.UNICODE)

        self.regex_after_days_ref = re.compile(r'((\d+|' + numeral_variants + r')\s*' + date_literal_choices + r'\s+' +
                                               datetime_diff_choices + r')', flags=re.UNICODE)

        self.regex_weekday_month_1 = re.compile(r'((\d+|' + numeral_variants + ')\s*' + weekday_choices + '\\s*' +
                                                datetime_diff_choices + r'\s+' + month_literal_choices + r')',
                                                flags=re.UNICODE)

        self.regex_weekday_month_2 = re.compile(r'(' + datetime_diff_choices + r'\s+' + month_literal_choices +
                                                r'\s*[a-z]*\s*(\d+|' + numeral_variants + ')\s+' +
                                                weekday_choices + r')', flags=re.UNICODE)

        self.regex_weekday_diff = re.compile(r'(' + datetime_diff_choices + r'\s+' + weekday_choices + r')',
                                             flags=re.UNICODE)

        self.regex_weekday = re.compile(r'(' + weekday_choices + r')', flags=re.UNICODE)
    
    @staticmethod
    def _sort_choices_on_word_counts(choices_list):
        choices_list.sort(key=lambda s: len(s.split()), reverse=True)
        return choices_list

    def detect_date(self, text):
        self.logger.info(f"detect_date function")
        self.text = text
        self.processed_text = text
        self.tagged_text = text

        date_list, original_list = None, None
        for detector in self.detector_preferences:
            date_list, original_list = detector(date_list, original_list)
            self._update_processed_text(original_list)
        self.logger.info(f"Returning from detect_date function -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list
    
    def _update_processed_text(self, original_date_list):
        self.logger.info(f"_update_processed text")
        for detected_text in original_date_list:
            self.tagged_text = self.tagged_text.replace(detected_text, self.tag)
            self.processed_text = self.processed_text.replace(detected_text, '')
        self.logger.info(f"_update_processed_text tagged text --> {self.tagged_text} processed textr --> {self.processed_text}")
    
    def _gregorian_day_month_year_format(self, date_list=None, original_list=None):
        if original_list is None:
            original_list = []
        if date_list is None:
            date_list = []
        regex_pattern = re.compile(r'[^/\-\.\w](([12][0-9]|3[01]|0?[1-9])\s?[/\-\.]\s?(1[0-2]|0?[1-9])'
                                   r'(?:\s?[/\-\.]\s?((?:20|19)?[0-9]{2}))?)\W')
        translate_number = self.convert_numbers(self.processed_text.lower())
        patterns = regex_pattern.findall(translate_number)
        for pattern in patterns:
            original = pattern[0]
            dd = int(pattern[1])
            mm = int(pattern[2])
            yy = int(self.normalize_year(pattern[3])) if pattern[3] else self.now_date.year
            try:
                if not pattern[3] and self.timezone.localize(datetime.datetime(year=yy, month=mm, day=dd)) \
                        < self.now_date:
                    yy += 1
            except Exception:
                return date_list, original_list

            date = {
                'dd': int(dd),
                'mm': int(mm),
                'yy': int(yy),
                'type': TYPE_EXACT
            }
            date_list.append(date)
            if translate_number != self.processed_text.lower():
                match = re.search(original, translate_number)
                original_list.append(self.processed_text[(match.span()[0]):(match.span()[1])])
            else:
                original_list.append(original)
        self.logger.info(f"Returning from _gregorian_day_month_year_format function -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list
    
    def _detect_relative_date(self, date_list=None, original_list=None):
        self.logger.info(f"_detect_relative_date")
        relative_date_keys = [key for key, value in self.date_constant_dict.items() if value[1] == 'relative_date']
        fuzz_matched_tokens=[]
        original_tokens_in_string=[]
        for token in self.processed_text.split():
            for keys in relative_date_keys:
                if token not in relative_date_keys and fuzz.ratio(rc.to_revcode(token,self.language).lower(),rc.to_revcode(keys,self.language).lower()) >=80 :
                        self.processed_text=re.sub(token,keys,self.processed_text)
                        fuzz_matched_tokens.append(keys)
                        self.logger.info(f"Matching key {keys}")
                        self.logger.info(f"matching text in the string {token}")
                        self.logger.info(f"edited the string to after matching tokens--> {self.processed_text}")
                        break
                
        self.logger.info(f"after switching all the available tokens---> {self.processed_text}")
        date_rel_match = self.regex_relative_date.findall(self.processed_text)
        for date_match in date_rel_match:
            original = date_match[0]
            if not self.past_date_referenced:
                req_date = self.now_date + datetime.timedelta(days=self.date_constant_dict[date_match[1]][0])
            else:
                req_date = self.now_date - datetime.timedelta(days=self.date_constant_dict[date_match[1]][0])

            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_relative_date function -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_date_month(self, date_list, original_list):
        self.logger.info(f"detect date month")
        date_list = date_list or []
        original_list = original_list or []
        fuzz_matched__month_tokens=[]
        original_month_tokens=[]
        month_keys_list = [key for key, value in self.date_constant_dict.items() if value[1] == 'month']
        for token in self.processed_text.split():
            self.logger.info(f"Token processed for detecting month from string-> {token}")
            for keys in month_keys_list:
                if token not in month_keys_list and token !=keys and fuzz.ratio(rc.to_revcode(token,self.language).lower(),rc.to_revcode(keys,self.language).lower()) >=80 :
                        self.processed_text=re.sub(token,keys,self.processed_text)
                        fuzz_matched__month_tokens.append(keys)
                        original_month_tokens.append(token)
                        self.logger.info(f"Replaced token -> {token} with the key -> {keys}")
                        break
        self.logger.info(f"final edited month_string is --> {self.processed_text}")

        date_month_match = self.regex_date_month.findall(self.processed_text)
        
        for date_match in date_month_match:
            original = date_match[0]
            self.logger.info(f"original match found {original}")
            dd = self._get_int_from_numeral(date_match[1])
            self.logger.info("Error check for month")
            mm = self.date_constant_dict[date_match[3]][0]
            today_mmdd = "%d%02d" % (self.now_date.month, self.now_date.day)
            today_yymmdd = "%d%02d%02d" % (self.now_date.year, self.now_date.month, self.now_date.day)
            mmdd = "%02d%02d" % (mm, dd)

            if int(today_mmdd) < int(mmdd):
                yymmdd = str(self.now_date.year) + mmdd
                yy = self.now_date.year
            else:
                yymmdd = str(self.now_date.year + 1) + mmdd
                yy = self.now_date.year + 1

            if self.past_date_referenced:
                if int(today_yymmdd) < int(yymmdd):
                    yy -= 1
            date = {
                'dd': int(dd),
                'mm': int(mm),
                'yy': int(yy),
                'type': TYPE_EXACT 
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_date_month function -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list
    
    def _detect_date_ref_month_1(self, date_list, original_list):
        self.logger.info(f"_detect_date_ref_month_1")
        date_list = date_list or []
        original_list = original_list or []

        date_ref_month_match = self.regex_date_ref_month_1.findall(self.processed_text)

        for date_match in date_ref_month_match:
            original = date_match[0]
            dd = self._get_int_from_numeral(date_match[1])
            if date_match[3] and date_match[4]:
                req_date = self.now_date + \
                           relativedelta(months=self.datetime_constant_dict[date_match[3]][1])
                mm = req_date.month
                yy = req_date.year
            else:
                mm = self.now_date.month
                yy = self.now_date.year

            date = {
                'dd': int(dd),
                'mm': int(mm),
                'yy': int(yy),
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_date_ref_month_1 -> date list : {date_list} and original list : {original_list}")     
        return date_list, original_list

    def _detect_date_ref_month_2(self, date_list, original_list):
        self.logger.info(f"_detect_date_ref_month_2")
        date_list = date_list or []
        original_list = original_list or []

        date_ref_month_match = self.regex_date_ref_month_2.findall(self.processed_text)
        for date_match in date_ref_month_match:
            original = date_match[0]
            dd = self._get_int_from_numeral(date_match[3])
            if date_match[1] and date_match[2]:
                req_date = self.now_date + \
                           relativedelta(months=self.datetime_constant_dict[date_match[1]][1])
                mm = req_date.month
                yy = req_date.year
            else:
                mm = self.now_date.month
                yy = self.now_date.year

            date = {
                'dd': int(dd),
                'mm': int(mm),
                'yy': int(yy),
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_date_ref_month_2 -> date list : {date_list} and original list : {original_list}")    
        return date_list, original_list

    def _detect_date_ref_month_3(self, date_list, original_list):
        self.logger.info(f"_detect_date_ref_month_3")
        date_list = date_list or []
        original_list = original_list or []

        date_ref_month_match = self.regex_date_ref_month_3.findall(self.processed_text)
        for date_match in date_ref_month_match:
            original = date_match[0]
            dd = self._get_int_from_numeral(date_match[1])
            if (self.now_date.day > dd and self.past_date_referenced) or \
                    (self.now_date.day <= dd and not self.past_date_referenced):
                mm = self.now_date.month
                yy = self.now_date.year
            elif self.now_date.day <= dd and self.past_date_referenced:
                req_date = self.now_date - relativedelta(months=1)
                mm = req_date.month
                yy = req_date.year
            else:
                req_date = self.now_date + relativedelta(months=1)
                mm = req_date.month
                yy = req_date.year
            date = {
                'dd': int(dd),
                'mm': int(mm),
                'yy': int(yy),
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_date_ref_month_3 -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list
    
    def _detect_date_diff(self, date_list, original_list):
        self.logger.info(f"_detect_date_diff")
        date_list = date_list or []
        original_list = original_list or []

        diff_day_match = self.regex_day_diff.findall(self.processed_text)
        for date_match in diff_day_match:
            original = date_match[0]
            req_date = self.now_date + datetime.timedelta(days=self.datetime_constant_dict[date_match[1]][1])
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_date_diff -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_after_days(self, date_list, original_list):
        self.logger.info(f"_detect_after_days")
        date_list = date_list or []
        original_list = original_list or []

        after_days_match = self.regex_after_days_ref.findall(self.processed_text)
        for date_match in after_days_match:
            original = date_match[0]
            day_diff = self._get_int_from_numeral(date_match[1])
            req_date = self.now_date + relativedelta(days=day_diff * self.datetime_constant_dict[date_match[3]][1])
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_after_days -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_weekday_ref_month_1(self, date_list, original_list):
        self.logger.info(f"_detect_weekday_ref_month_1")
        
        date_list = date_list or []
        original_list = original_list or []

        weekday_month_match = self.regex_weekday_month_1.findall(self.processed_text)
        for date_match in weekday_month_match:
            original = date_match[0]
            n_weekday = self._get_int_from_numeral(date_match[1])
            weekday = self.date_constant_dict[date_match[2]][0]
            ref_date = self.now_date + relativedelta(months=self.datetime_constant_dict[date_match[3]][1])
            req_date = nth_weekday(n_weekday, weekday, ref_date)
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_weekday_ref_month_1 -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_weekday_ref_month_2(self, date_list, original_list):
        self.logger.info(f"_detect_weekday_ref_month_2")
        date_list = date_list or []
        original_list = original_list or []

        weekday_month_match = self.regex_weekday_month_2.findall(self.processed_text)
        for date_match in weekday_month_match:
            original = date_match[0]
            n_weekday = self._get_int_from_numeral(date_match[3])
            weekday = self.date_constant_dict[date_match[4]][0]
            ref_date = self.now_date + relativedelta(months=self.datetime_constant_dict[date_match[1]][1])
            req_date = nth_weekday(weekday, n_weekday, ref_date)
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_weekday_ref_month_2 -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_weekday_diff(self, date_list, original_list):
        self.logger.info(f"_detect_weekday_diff")
        date_list = date_list or []
        original_list = original_list or []

        weekday_ref_match = self.regex_weekday_diff.findall(self.processed_text)
        for date_match in weekday_ref_match:
            original = date_match[0]
            n = self.datetime_constant_dict[date_match[1]][1]
            weekday = self.date_constant_dict[date_match[2]][0]
            req_date = next_weekday(current_date=self.now_date, n=n, weekday=weekday)
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_weekday_diff -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    def _detect_weekday(self, date_list, original_list):
        self.logger.info(f"_detect_weekday")
        date_list = date_list or []
        original_list = original_list or []
        weekday_ref_match = self.regex_weekday.findall(self.processed_text)
        for date_match in weekday_ref_match:
            original = date_match[0]
            weekday = self.date_constant_dict[date_match[1]][0]
            req_date = next_weekday(current_date=self.now_date, n=0, weekday=weekday)
            date = {
                'dd': req_date.day,
                'mm': req_date.month,
                'yy': req_date.year,
                'type': TYPE_EXACT
            }
            date_list.append(date)
            original_list.append(original)
        self.logger.info(f"Returning from _detect_weekday -> date list : {date_list} and original list : {original_list}")
        return date_list, original_list

    @staticmethod
    def convert_numbers(text):
        result = text
        digit = re.compile(r'(\d)', re.U)
        groups = digit.findall(result)
        for group in groups:
            result = result.replace(group, str(int(group)))
        return result

    def _get_int_from_numeral(self, numeral):
        self.logger.info(f"get init from numeral")
        if numeral.replace('.', '').isdigit():
            return int(numeral)
        else:
            return int(self.numerals_constant_dict[numeral][0])

    def normalize_year(self, year):
        self.logger.info(f"normalize_year")
        past_regex = None
        # Todo: Add more language variations of birthday.
        present_regex = None
        future_regex = None
        this_century = int(str(self.now_date.year)[:2])
        if len(year) == 2:
            if (((self.bot_message and past_regex and past_regex.search(self.bot_message))
                 or (self.past_date_referenced is True)) and (int(year) > int(str(self.now_date.year)[2:]))):
                return str(this_century - 1) + year
            elif present_regex and present_regex.search(self.bot_message):
                return str(this_century) + year
            elif future_regex and future_regex.search(self.bot_message):
                return str(this_century + 1) + year
        if len(year) == 2:
            return str(this_century) + year

        return year

# object1= dateTest(entity_name='date', language='hi',locale=None,")
# print(type(object1.detect_date("मैं परसों आऊंगा")))