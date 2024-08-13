import logging
import logging
import datetime
import os
import re

import pytz

from ner.Time.constant import (DATETIME_CONSTANT_FILE, ADD_DIFF_DATETIME_TYPE, NUMERALS_CONSTANT_FILE,
                                                TIME_CONSTANT_FILE, REF_DATETIME_TYPE, HOUR_TIME_TYPE,
                                                MINUTE_TIME_TYPE, DAYTIME_MERIDIEM, AM_MERIDIEM, PM_MERIDIEM,
                                                TWELVE_HOUR)
from ner.Time.utils import get_tuple_dict, get_hour_min_diff, get_timezone

class detect_indic_time():
    def __init__(self,entity_name,language,timezone=None):
        logging.basicConfig(filename="time_test.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
        self.logger= logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.text = ''
        self.tagged_text = ''
        self.processed_text = ''
        self.entity_name = entity_name
        self.tag = '__' + entity_name + '__'
        if timezone:
            self.timezone = get_timezone(timezone)
        else:
            self.timezone = None
        self.now_date = datetime.datetime.now(tz=self.timezone)
        self.bot_message = None
        self.time_constant_dict = {}
        self.datetime_constant_dict = {}
        self.numerals_constant_dict = {}
        self.regex_time = None
        self.language=language
        self.init_regex_and_parser()
        self.detector_preferences = [
            self._detect_time_with_coln_format,
            self._detect_hour_minute]
    
    @staticmethod
    def _sort_choices_by_word_counts(choices_list):
        choices_list.sort(key=lambda s: len(s.split()), reverse=True)
        return choices_list

    def init_regex_and_parser(self):
        data_directory_path=os.path.join("ner","Time",self.language,"data")
        self.time_constant_dict = get_tuple_dict(
            csv_file=os.path.join(data_directory_path.rstrip(os.sep), TIME_CONSTANT_FILE)
        )
        self.datetime_constant_dict = get_tuple_dict(
            csv_file=os.path.join(data_directory_path.rstrip(os.sep), DATETIME_CONSTANT_FILE)
        )
        self.numerals_constant_dict = get_tuple_dict(
            csv_file=os.path.join(data_directory_path.rstrip(os.sep), NUMERALS_CONSTANT_FILE)
        )

        # datetime_add_diff choices for regex
        datetime_diff_choices = [x for x in self.datetime_constant_dict
                                 if self.datetime_constant_dict[x][2] == ADD_DIFF_DATETIME_TYPE]
        datetime_diff_choices = self._sort_choices_by_word_counts(datetime_diff_choices)
        datetime_diff_choices = u'({}|)'.format(u'|'.join(datetime_diff_choices))

        # datetime_ref choices in regex
        datetime_add_ref_choices = [x for x in self.datetime_constant_dict
                                    if self.datetime_constant_dict[x][2] == REF_DATETIME_TYPE]
        datetime_add_ref_choices = self._sort_choices_by_word_counts(datetime_add_ref_choices)
        datetime_add_ref_choices = u'({}|)'.format(u'|'.join(datetime_add_ref_choices))

        # hour choices for regex
        hour_variants = [x.lower() for x in self.time_constant_dict
                         if self.time_constant_dict[x][0] == HOUR_TIME_TYPE]
        hour_variants = self._sort_choices_by_word_counts(hour_variants)
        hour_variants = u'({}|)'.format(u'|'.join(hour_variants))

        # minute OR choices for regex
        minute_variants = [x.lower() for x in self.time_constant_dict
                           if self.time_constant_dict[x][0] == MINUTE_TIME_TYPE]
        minute_variants = self._sort_choices_by_word_counts(minute_variants)
        minute_variants = u'({}|)'.format(u'|'.join(minute_variants))

        # meridiem OR choices for regex
        daytime_meridiem = [x.lower() for x in self.time_constant_dict
                            if self.time_constant_dict[x][0] == DAYTIME_MERIDIEM]
        daytime_meridiem = self._sort_choices_by_word_counts(daytime_meridiem)
        daytime_meridiem = u'({}|)'.format(u'|'.join(daytime_meridiem))

        # numeral OR choices for regex
        numeral_variants = [x.lower() for x in self.numerals_constant_dict]
        numeral_variants = self._sort_choices_by_word_counts(numeral_variants)
        numeral_variants = u'|'.join(numeral_variants)

        self.regex_time = re.compile(r'(' +
                                     daytime_meridiem +
                                     r'\s*[a-z]*?\s*' +
                                     datetime_add_ref_choices +
                                     r'\s*(\d+|' + numeral_variants + r')\s*' +
                                     hour_variants +
                                     r'\s*(\d*|' + numeral_variants + r')\s*' +
                                     minute_variants +
                                     r'\s+' +
                                     datetime_diff_choices +
                                     r'\s*' +
                                     daytime_meridiem +
                                     r')', flags=re.UNICODE)
    
    def detect_time(self, text, range_enabled=False, form_check=False, **kwargs):
        self.text = text
        self.processed_text = self.text
        self.tagged_text = self.text

        time_list, original_list = [], []

        for detector in self.detector_preferences:
            time_list, original_list = detector(time_list, original_list)
            self._update_processed_text(original_list)

        return time_list, original_list

    def _get_float_from_numeral(self, numeral):
        if numeral.replace('.', '').isdigit():
            return float(numeral)
        else:
            return float(self.numerals_constant_dict[numeral][0])

    def _get_meridiem(self, hours, mins, original_text):
        new_timezone = self.timezone or pytz.timezone('Asia/Kolkata')
        current_datetime = datetime.datetime.now(new_timezone)
        current_hour = current_datetime.hour
        current_min = current_datetime.minute
        if hours == 0 or hours >= TWELVE_HOUR:
            return 'hrs'

        for key, values in self.time_constant_dict.items():
            if values[0] == DAYTIME_MERIDIEM and key in original_text:
                return values[1]

        if current_hour >= TWELVE_HOUR:
            current_hour -= 12
            if current_hour < hours:
                return PM_MERIDIEM
            elif current_hour == hours and current_min < mins:
                return PM_MERIDIEM
        else:
            if current_hour > hours:
                return PM_MERIDIEM
            elif current_hour == hours and current_min > mins:
                return PM_MERIDIEM
        return AM_MERIDIEM

    def _detect_hour_minute(self, time_list, original_list):
        time_list = time_list or []
        original_list = original_list or []

        time_matches = self.regex_time.findall(self.processed_text)
        for time_match in time_matches:
            hh = 0
            mm = 0
            nn = None
            original = time_match[0].strip()
            val = self._get_float_from_numeral(time_match[3])

            if time_match[2]:
                val_add = self.datetime_constant_dict[time_match[2]][1]
                val = val + val_add

            if time_match[4]:
                hh = val
            else:
                mm = val

            if time_match[5]:
                mm = self._get_float_from_numeral(time_match[5])

            if time_match[7]:
                _dt = datetime.timedelta(hours=hh, minutes=mm)
                ref_date = (self.now_date + int(self.datetime_constant_dict[time_match[7]][1]) * _dt)
                hh, mm, nn = get_hour_min_diff(self.now_date, ref_date)

            if int(hh) != hh:
                mm = int((hh - int(hh)) * 60)
                hh = int(hh)

            if not nn:
                nn = self._get_meridiem(hh, mm, original)
            if hh == 0 and mm > 0 and nn == 'hrs':
                break
            time = {
                'hh': int(hh),
                'mm': int(mm),
                'nn': nn,
                'tz': None if not self.timezone else self.timezone.zone
            }

            time_list.append(time)
            original_list.append(original)

        return time_list, original_list

    def _detect_time_with_coln_format(self, time_list, original_list):
        patterns = re.findall(r'\s*((\d+)\:(\d+))\s*', self.processed_text.lower(), re.U)
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []

        for pattern in patterns:
            t1 = pattern[1]
            t2 = pattern[2]
            original = pattern[0]

            if len(t1) <= 2 and len(t2) <= 2:
                hh = int(t1)
                mm = int(t2)
                time = {
                    'hh': hh,
                    'mm': mm,
                    'tz': None if not self.timezone else self.timezone.zone,
                    'time_type': None
                }

                nn = self._get_meridiem(hh, mm, original)
                time.update({'nn': nn})

                original_list.append(original)
                time_list.append(time)

        return time_list, original_list

    def _update_processed_text(self, original_time_list): 
        for detected_text in original_time_list:
            self.tagged_text = self.tagged_text.replace(detected_text, self.tag)
            self.processed_text = self.processed_text.replace(detected_text, '')
    
# object1=detect_Indic_Time(entity_name="time", language='hi')
# print(object1.detect_time("आठ बजे के बाद आऊंगा"))