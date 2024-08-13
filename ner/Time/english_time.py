from __future__ import absolute_import
import re
import datetime
import collections
import pandas as pd
import os
import pytz
import logging
from ner.Time.constant import AM_MERIDIEM, PM_MERIDIEM, TWELVE_HOUR, EVERY_TIME_TYPE,\
    TIMEZONES_CONSTANT_FILE, TIMEZONE_VARIANTS_VARIANTS_COLUMN_NAME, \
    TIMEZONES_CODE_COLUMN_NAME, TIMEZONES_ALL_REGIONS_COLUMN_NAME, \
    TIMEZONES_PREFERRED_REGION_COLUMN_NAME
from ner.Time.utils import get_timezone, get_list_from_pipe_sep_string

TimezoneVariants = collections.namedtuple('TimezoneVariant', ['value', 'preferred'])


class detect_english_time():

    def __init__(self, entity_name, timezone=None):
        # assigning values to superclass attributes
        logging.basicConfig(filename="time_test_english.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
        self.logger= logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.entity_name = entity_name
        self.text = ''
        self.departure_flag = False
        self.return_flag = False
        self.tagged_text = ''
        self.processed_text = ''
        self.time = []
        self.original_time_text = []
        self.tag = '__' + entity_name + '__'
        self.bot_message = None
        if timezone:
            self.timezone = get_timezone(timezone)
        else:
            self.timezone = None
        self.timezones_map = {}

        self.init_regex_and_parser()
        sorted_len_timezone_keys = sorted(list(self.timezones_map.keys()), key=len, reverse=True)
        self.timezone_choices = "|".join([re.escape(x.lower()) for x in sorted_len_timezone_keys])

    def init_regex_and_parser(self):
        data_directory_path=os.path.join("ner","Time","en","data")
        timezone_variants_data_path = os.path.join(data_directory_path, TIMEZONES_CONSTANT_FILE)
        columns = [TIMEZONE_VARIANTS_VARIANTS_COLUMN_NAME, TIMEZONES_CODE_COLUMN_NAME,
                   TIMEZONES_PREFERRED_REGION_COLUMN_NAME]
        if os.path.exists(timezone_variants_data_path):
            timezone_variants_df = pd.read_csv(timezone_variants_data_path, usecols=columns, encoding='utf-8')
            for index, row in timezone_variants_df.iterrows():
                tz_name_variants = get_list_from_pipe_sep_string(row[TIMEZONE_VARIANTS_VARIANTS_COLUMN_NAME])
                value = row[TIMEZONES_CODE_COLUMN_NAME]
                preferred = row[TIMEZONES_PREFERRED_REGION_COLUMN_NAME]
                for tz_name in tz_name_variants:
                    self.timezones_map[tz_name] = TimezoneVariants(value=value, preferred=preferred)

    def convert_to_pytz_format(self, timezone_variant):
        self.logger.info("convert_to_pytz_format")
        timezone_code = self.timezones_map[timezone_variant].value
        data_directory_path=os.path.join('en','data')
        timezone_data_path = os.path.join(data_directory_path, TIMEZONES_CONSTANT_FILE)
        columns = [TIMEZONES_CODE_COLUMN_NAME, TIMEZONES_ALL_REGIONS_COLUMN_NAME]
        if os.path.exists(timezone_data_path):
            timezones_df = pd.read_csv(timezone_data_path, usecols=columns, index_col=TIMEZONES_CODE_COLUMN_NAME,
                                       encoding='utf-8')
            if re.search(self.timezone.zone, timezones_df.loc[timezone_code][TIMEZONES_ALL_REGIONS_COLUMN_NAME]):
                return self.timezone.zone
            else:
                return self.timezones_map[timezone_variant].preferred

        return self.timezone.zone

    def _detect_time(self, range_enabled=False, form_check=False):
        self.logger.info("_detect_time")
        time_list = []
        original_list = []
        time_list, original_list = self._detect_range_12_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_range_12_hour_format_without_min(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_start_range_12_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_start_range_12_hour_format_without_min(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_end_range_12_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_end_range_12_hour_format_without_min(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_range_24_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_12_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_12_hour_without_min(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_with_difference(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_with_difference_later(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_with_every_x_hour(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_with_once_in_x_day(time_list, original_list)
        self._update_processed_text(original_list)
        if form_check:
            time_list, original_list = self._detect_24_hour_optional_minutes_format(time_list, original_list)
            self._update_processed_text(original_list)
        time_list, original_list = self._detect_restricted_24_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_12_hour_word_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_12_hour_word_format2(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_24_hour_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_without_format(time_list, original_list)
        self._update_processed_text(original_list)
        time_list, original_list = self._detect_time_without_format_preceeding(time_list, original_list)
        self._update_processed_text(original_list)
        if not time_list:
            time_list, original_list = self._get_morning_time_range(time_list, original_list)
            self._update_processed_text(original_list)
            time_list, original_list = self._get_afternoon_time_range(time_list, original_list)
            self._update_processed_text(original_list)
            time_list, original_list = self._get_evening_time_range(time_list, original_list)
            self._update_processed_text(original_list)
            time_list, original_list = self._get_night_time_range(time_list, original_list)
            self._update_processed_text(original_list)
            time_list, original_list = self._get_default_time_range(time_list, original_list)
            self._update_processed_text(original_list)
        if not range_enabled and time_list:
            time_list, original_list = self._remove_time_range_entities(time_list=time_list,
                                                                        original_list=original_list)
        return time_list, original_list

    def detect_time(self, text, range_enabled=False, form_check=False, **kwargs):
        self.logger.info("detect_time")
        self.text = ' ' + text + ' '
        self.processed_text = self.text.lower()
        self.departure_flag = True if re.search(r'depart', self.text.lower()) else False
        self.return_flag = True if re.search(r'return', self.text.lower()) else False
        self.tagged_text = self.text.lower()
        time_data = self._detect_time(range_enabled=range_enabled, form_check=form_check)
        self.time = time_data[0]
        self.original_time_text = time_data[1]
        return time_data

    def _detect_range_12_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_range_12_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        regex_patterns = re.compile(
            r'\b((?:from)?({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*(?::|\.|\s)?[\s-]*?([0-5][0-9])[\s-]*?'
            r'(pm|am|a\.m\.?|p\.m\.?)[\s-]*?({timezone})?\s*(?:to|-|till|until|untill|upto|up to)'
            r'[\s-]*?({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*'
            r'(?::|\.|\s)?[\s-]*?([0-5][0-9])[\s-]*?(pm|am|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
            .format(timezone=self.timezone_choices)
        )
        patterns = regex_patterns.findall(self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            original2 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            t2 = pattern[3]
            ap1 = pattern[4]
            tz1 = pattern[1]
            tz2 = pattern[5]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']

            t3 = pattern[7]
            t4 = pattern[8]
            ap2 = pattern[9]
            tz3 = pattern[6]
            tz4 = pattern[10]
            tz = None
            if tz3 or tz4:
                tz = self.convert_to_pytz_format(tz3 or tz4)
            time2 = {
                'hh': int(t3),
                'mm': int(t4),
                'nn': str(ap2).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }
            time2['nn'] = 'am' if 'a' in time2['nn'] else time2['nn']
            time2['nn'] = 'pm' if 'p' in time2['nn'] else time2['nn']

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original2)
            break
        return time_list, original_list

    def _detect_range_24_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_range_24_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        regex_patterns = re.compile(
            r'\b((?:from)?({timezone})?\s*(00?|0?[2-9]|0?1[0-9]?|2[0-3])[:.\s]?([0-5][0-9])'
            r'[\s-]*?({timezone})?\s*(?:to|-|till|until|untill|upto|up to)[\s-]*?({timezone})?\s*'
            r'(00?|0?[2-9]|0?1[0-9]?|2[0-3])[:.\s]?([0-5][0-9])'
            r'[\s-]*?({timezone})?)(?!\s*(?:am|pm|a\.m\.?|p\.m\.?|(?:{timezone})|\d))'
            .format(timezone=self.timezone_choices)
        )
        patterns = regex_patterns.findall(self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            original2 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            t2 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': 'hrs',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']

            t3 = pattern[6]
            t4 = pattern[7]
            tz3 = pattern[5]
            tz4 = pattern[8]
            tz = None
            if tz3 or tz4:
                tz = self.convert_to_pytz_format(tz3 or tz4)
            time2 = {
                'hh': int(t3),
                'mm': int(t4),
                'nn': 'hrs',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original2)
            break
        return time_list, original_list

    def _detect_range_12_hour_format_without_min(self, time_list=None, original_list=None):
        self.logger.info("_detect_range_12_hour_format_without_min")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        regex_patterns = re.compile(
            r'\b((?:from)?({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*(am|pm|a\.m\.?|p\.m\.?)[\s-]*?({timezone})?\s*'
            r'(?:to|-|till|until|untill|upto|up to)'
            r'\s*({timezone})?[\s-]*?(0?[2-9]|0?1[0-2]?)[\s-]*(am|pm|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
            .format(timezone=self.timezone_choices)
        )
        patterns = regex_patterns.findall(self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            original2 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            ap1 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': 0,
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']

            t2 = pattern[6]
            ap2 = pattern[7]
            tz3 = pattern[5]
            tz4 = pattern[8]
            tz = None
            if tz3 or tz4:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time2 = {
                'hh': int(t2),
                'mm': 0,
                'nn': str(ap2).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }
            time2['nn'] = 'am' if 'a' in time2['nn'] else time2['nn']
            time2['nn'] = 'pm' if 'p' in time2['nn'] else time2['nn']

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original2)
            break
        return time_list, original_list

    def _detect_start_range_12_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_start_range_12_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []

        regex_patterns = re.compile(
            r'\b((?:after|aftr)[\s-]*({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*(?::|\.|\s)?[\s-]*?'
            r'([0-5][0-9])[\s-]*?(pm|am|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
            .format(timezone=self.timezone_choices)
        )
        patterns = regex_patterns.findall(self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            t2 = pattern[3]
            ap1 = pattern[4]
            tz1 = pattern[1]
            tz2 = pattern[5]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']

            time_list.append(time1)
            original_list.append(original1)
            break
        return time_list, original_list

    def _detect_end_range_12_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_end_range_12_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((?:before|bfre|till|until|untill|upto|up to)[\s-]*({timezone})?\s*'
                              r'(0?[2-9]|0?1[0-2]?)[\s-]*(?::|\.|\s)?[\s-]*?([0-5][0-9])[\s-]*?'
                              r'(pm|am|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            t2 = pattern[3]
            ap1 = pattern[4]
            tz1 = pattern[1]
            tz2 = pattern[5]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']
            time_list.append(time1)
            original_list.append(original1)
            break
        return time_list, original_list

    def _detect_start_range_12_hour_format_without_min(self, time_list=None, original_list=None):
        self.logger.info("_detect_start_range_12_hour_format_without_min")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((?:after|aftr)[\s-]*({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*'
                              r'(am|pm|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'.format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            ap1 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time1 = {
                'hh': int(t1),
                'mm': 0,
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']

            time_list.append(time1)
            original_list.append(original1)
            break
        return time_list, original_list

    def _detect_end_range_12_hour_format_without_min(self, time_list=None, original_list=None):
        self.logger.info("_detect_end_range_12_hour_format_without_min")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((?:before|bfore|till|until|untill|upto|up to)'
                              r'[\s-]*({timezone})?\s*(0?[2-9]|0?1[0-2]?)'
                              r'[\s-]*(am|pm|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            t1 = pattern[2]
            ap1 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)

            time1 = {
                'hh': int(t1),
                'mm': 0,
                'nn': str(ap1).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }
            time1['nn'] = 'am' if 'a' in time1['nn'] else time1['nn']
            time1['nn'] = 'pm' if 'p' in time1['nn'] else time1['nn']
            time_list.append(time1)
            original_list.append(original1)
            break
        return time_list, original_list

    def _detect_12_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_12_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*(?::|\.|\s)?[\s-]*?([0-5][0-9])'
                              r'[\s-]*?(pm|am|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = pattern[2]
            t2 = pattern[3]
            ap = pattern[4]
            tz1 = pattern[1]
            tz2 = pattern[5]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': str(ap).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }

            time['nn'] = 'am' if 'a' in time['nn'] else time['nn']
            time['nn'] = 'pm' if 'p' in time['nn'] else time['nn']
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_12_hour_without_min(self, time_list=None, original_list=None):
        self.logger.info("_detect_12_hour_without_min")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*(0?[2-9]|0?1[0-2]?)[\s-]*(am|pm|a\.m\.?|p\.m\.?)\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices), self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = pattern[2]
            ap = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            time = {
                'hh': int(t1),
                'mm': 0,
                'nn': str(ap).lower().strip('.'),
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time['nn'] = 'am' if 'a' in time['nn'] else time['nn']
            time['nn'] = 'pm' if 'p' in time['nn'] else time['nn']
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_with_difference(self, time_list=None, original_list=None):
        self.logger.info("_detect_time_with_difference")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((in\sabout|in\saround|after|about|in)\s(\d+)\s?'
                              r'(min|mins|minutes|hour|hours|hrs|hr))\b',
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[2])
            td = pattern[3]
            hours = ['hour', 'hours', 'hrs', 'hr']
            mins = ['min', 'mins', 'minutes']
            setter = ""
            antisetter = ""
            if td in hours:
                setter = "hh"
                antisetter = "mm"
            elif td in mins:
                setter = "mm"
                antisetter = "hh"
            time = dict()
            time[setter] = int(t1)
            time[antisetter] = 0
            time['nn'] = 'df'
            time['tz'] = None if not self.timezone else self.timezone.zone
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_with_difference_later(self, time_list=None, original_list=None):
        self.logger.info("_detect_time_with_difference_later")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((\d+)\s?(min|mins|minutes?|hour|hours|hrs|hr)\s?(later|ltr|latr|lter)s?)\b',
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[1])
            td = pattern[2]
            hours = ['hour', 'hours', 'hrs', 'hr']
            mins = ['min', 'mins', 'minutes', 'minute']
            setter = ""
            antisetter = ""
            if td in hours:
                setter = "hh"
                antisetter = "mm"
            elif td in mins:
                setter = "mm"
                antisetter = "hh"
            time = dict()
            time[setter] = int(t1)
            time[antisetter] = 0
            time['nn'] = 'df'
            time['tz'] = None if not self.timezone else self.timezone.zone
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_with_every_x_hour(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((every|evry|evy|evri)\s*(\d+)\s*(min|mins|minutes|hour|hours|hrs|hr))\b',
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[2])
            td = pattern[3]
            hours = ['hour', 'hours', 'hrs', 'hr']
            mins = ['min', 'mins', 'minutes']
            setter = ""
            antisetter = ""
            if td in hours:
                setter = "hh"
                antisetter = "mm"
            elif td in mins:
                setter = "mm"
                antisetter = "hh"
            time = dict()
            time[setter] = int(t1)
            time[antisetter] = 0
            time['nn'] = EVERY_TIME_TYPE
            time['tz'] = None if not self.timezone else self.timezone.zone
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_with_once_in_x_day(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((once|onc|1se)\s*(in|every|evry|in every)?\s*(\d+|a)\s?(day|days))\b',
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            if not pattern[3] or pattern[3] == "a":
                t1 = 24
            else:
                t1 = 24 * int(pattern[3])
            setter = "hh"
            antisetter = "mm"
            time = dict()
            time[setter] = int(t1)
            time[antisetter] = 0
            time['nn'] = EVERY_TIME_TYPE
            time['tz'] = None if not self.timezone else self.timezone.zone
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_24_hour_optional_minutes_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_24_hour_optional_minutes_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*(00?|0?[2-9]|0?1[0-9]?|2[0-3])[:.\s]([0-5][0-9])?\s*'
                              r'(?:h|hrs|hr)?\s*({timezone})?)(?!\s*(?:am|pm|a\.m\.?|p\.m\.?|(?:{timezone})'
                              r'|(?:h|hrs|hr)|\d))\b'
                              .format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t2 = 0
            t1 = pattern[2]
            if pattern[3]:
                t2 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)

            time = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': 'hrs',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_restricted_24_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_restricted_24_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*(00?|1[3-9]?|2[0-3])[:.\s]([0-5][0-9])'
                              r'\s*(?:h|hr|hrs)?\s*({timezone})?)(?!\s*(?:am|pm|a\.m\.?|p\.m\.?|(?:h|hrs|hr)|'
                              r'(?:{timezone})|\d))\b'.format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = pattern[2]
            t2 = pattern[3]
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            meridiem = self._get_meridiem(int(t1), int(t2), tz)

            time = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': meridiem,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_12_hour_word_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_12_hour_word_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b((0?[1-9]|1[0-2])[:.\s]([0-5][0-9]))(?!\s?(?:am|pm|a\.m\.?|p\.m\.?|\d))',
                              self.processed_text.lower())
        pattern_am = re.findall(r'\s(morning|early|subah|mrng|mrning|savere)\s', self.processed_text.lower())
        pattern_pm = re.findall(r'\s(noon|afternoon|evening|evng|evning|sham|lunch|dinner)\s',
                                self.processed_text.lower())
        pattern_night = re.findall(r'\s(night|nite|tonight|latenight|tonit|nit|rat)\s', self.processed_text.lower())
        pattern_tz = re.findall(r'(?:\b|[^a-zA-Z])({timezone})\b'.format(timezone=self.timezone_choices),
                                self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[1])
            t2 = int(pattern[2])
            tz = None
            if pattern_tz:
                tz = pattern_tz[0]
            time = {
                'hh': t1,
                'mm': t2,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            if pattern_am:
                time['nn'] = 'am'
            elif pattern_pm:
                time['nn'] = 'pm'
            elif pattern_night:
                time['nn'] = 'am' if (t1 == 12 or t1 < 5) else 'pm'
            else:
                return time_list, original_list
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_12_hour_word_format2(self, time_list=None, original_list=None):
        self.logger.info("_detect_12_hour_word_format2")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'((?:by|before|after|at|on|dot|exactly|exact)[\s-]*(0?[1-9]|1[0-2]))\b',
                              self.processed_text.lower())
        pattern_am = re.findall(r'\s(morning|early|subah|mrng|mrning|savere)', self.processed_text.lower())
        pattern_pm = re.findall(r'\s(noon|afternoon|evening|evng|evning|sham)', self.processed_text.lower())
        pattern_night = re.findall(r'\s(night|nite|tonight|latenight|tonit|nit|rat)', self.processed_text.lower())
        pattern_tz = re.findall(r'(?:\b|[^a-zA-Z])({timezone})\b'.format(timezone=self.timezone_choices),
                                self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[1])
            tz = None
            if pattern_tz:
                tz = pattern_tz[0]
            time = {
                'hh': t1,
                'mm': 0,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            if pattern_am:
                time['nn'] = 'am'
            elif pattern_pm:
                time['nn'] = 'pm'
            elif pattern_night:
                time['nn'] = 'am' if (t1 == 12 or t1 < 5) else 'pm'
            else:
                return time_list, original_list
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_24_hour_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_24_hour_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*(00?|0?[2-9]|0?1[0-9]?|2[0-3])[:.\s]([0-5][0-9])\s*({timezone})?)'
                              r'(?!\s*(?:am|pm|a\.m\.?|p\.m\.?|(?:{timezone})|\d))'
                              .format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        if not patterns:
            # Optional minutes but compulsory "hour" mention
            patterns = re.findall(r'\b(({timezone})?\s*(00?|0?[2-9]|0?1[0-9]?|2[0-3])(?:[:.\s]?([0-5][0-9]))?\s+'
                                  r'(?:hours?|hrs?)\s*({timezone})?\b)'.format(timezone=self.timezone_choices),
                                  self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = int(pattern[2])
            t2 = int(pattern[3]) if pattern[3] else 0
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            meridiem = self._get_meridiem(t1, t2, tz)
            time = {
                'hh': t1,
                'mm': t2,
                'nn': meridiem,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_without_format(self, time_list=None, original_list=None):
        self.logger.info("_detect_time_without_format")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        self.logger.info(f"Text recieved in the _detect_time_without_format -> {self.processed_text}")
        patterns = re.findall(r'\b((?:by|before|after|at|dot|exactly|exact)[\s-]*((0?[1-9]|1[0-2])[:.\s]*'
                              r'([0-5][0-9])?)\s*({timezone})?)\s'.format(timezone=self.timezone_choices),
                              self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = pattern[2]
            t2 = 0
            tz = pattern[4] or None
            if tz:
                tz = self.convert_to_pytz_format(tz)
            if pattern[3]:
                t2 = pattern[3]
            meridiem = self._get_meridiem(int(t1), int(t2), tz)
            time = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': meridiem,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _detect_time_without_format_preceeding(self, time_list=None, original_list=None):
        self.logger.info("_detect_time_without_format_preceeding")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        patterns = re.findall(r'\b(({timezone})?\s*((0?[1-9]|1[0-2])[:.\s]*([0-5][0-9])?)[\s-]*'
                              r'(?:o\'clock|o\' clock|clock|oclock|o clock|hours)\s*'
                              r'({timezone})?)\b'.format(timezone=self.timezone_choices),
                              self.processed_text.lower())

        if not patterns and self.bot_message and re.findall(r"Time|time", self.bot_message.lower()):
            patterns = re.findall(r'\b(({timezone})?\s*([0-2]?[0-9])'
                                  r'()\s*({timezone})?)\b'.format(timezone=self.timezone_choices),
                                  self.processed_text.lower())
        for pattern in patterns:
            original = pattern[0].strip()
            t1 = pattern[2]
            t2 = 0
            tz1 = pattern[1]
            tz2 = pattern[4]
            tz = None
            if tz1 or tz2:
                tz = self.convert_to_pytz_format(tz1 or tz2)
            if pattern[3]:
                t2 = pattern[3]
            meridiem = self._get_meridiem(int(t1), int(t2), tz)
            time = {
                'hh': int(t1),
                'mm': int(t2),
                'nn': meridiem,
                'tz': tz or (None if not self.timezone else self.timezone.zone),
            }
            time_list.append(time)
            original_list.append(original)
        return time_list, original_list

    def _get_meridiem(self, hours, mins, timezone):
        self.logger.info("_get_meridiem")
        if timezone is not None:
            new_timezone = get_timezone(timezone)
        else:
            # If no TZ(neither from api call not from the user message) is given, use 'UTC'
            new_timezone = self.timezone or pytz.timezone('UTC')

        current_datetime = datetime.datetime.now(new_timezone)
        current_hour = current_datetime.hour
        current_min = current_datetime.minute
        if hours == 0 or hours >= TWELVE_HOUR:
            return 'hrs'
        if current_hour >= TWELVE_HOUR:
            current_hour -= 12
            if (current_hour < hours) or (current_hour == hours and current_min < mins):
                return PM_MERIDIEM
        else:
            if current_hour > hours:
                return PM_MERIDIEM
            elif current_hour == hours and current_min > mins:
                return PM_MERIDIEM
        return AM_MERIDIEM

    def _get_morning_time_range(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        # pattern to detect morning
        patterns = re.findall(r'\b((?:morning|early|subah|mrng|mrning|savere)\s*(?:in|of|at)?\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices), self.processed_text.lower())
        for pattern in patterns:
            original1 = pattern[0].strip()
            tz = None
            if pattern[1]:
                tz = self.convert_to_pytz_format(pattern[1])
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            time1 = {
                'hh': 12,
                'mm': 0,
                'nn': 'am',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }

            time2 = {
                'hh': 11,
                'mm': 0,
                'nn': 'am',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original1)

        return time_list, original_list

    def _get_afternoon_time_range(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        # patterns
        patterns = re.findall(r'\b((?:noon|afternoon)\s*(?:in|of|at)?\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices), self.processed_text.lower())

        for pattern in patterns:
            original1 = pattern[0].strip()
            tz = None
            if pattern[1]:
                tz = self.convert_to_pytz_format(pattern[1])
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            time1 = {
                'hh': 11,
                'mm': 0,
                'nn': 'am',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }

            time2 = {
                'hh': 5,
                'mm': 0,
                'nn': 'pm',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original1)

        return time_list, original_list

    def _get_evening_time_range(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        # patterns
        patterns = re.findall(r'\b((?:evening|evng|evning|sham)\s*(?:in|of|at)?\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices), self.processed_text.lower())

        for pattern in patterns:
            original1 = pattern[0].strip()
            tz = None
            if pattern[1]:
                tz = self.convert_to_pytz_format(pattern[1])
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            time1 = {
                'hh': 5,
                'mm': 0,
                'nn': 'pm',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }

            time2 = {
                'hh': 9,
                'mm': 0,
                'nn': 'pm',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original1)

        return time_list, original_list

    def _get_night_time_range(self, time_list=None, original_list=None):
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        # patterns
        patterns = re.findall(r'\b((?:night|nite|tonight|latenight|tonit|nit|rat)\s*(?:in|of|at)?\s*({timezone})?)\b'
                              .format(timezone=self.timezone_choices), self.processed_text.lower())

        for pattern in patterns:
            original1 = pattern[0].strip()
            tz = None
            if pattern[1]:
                tz = self.convert_to_pytz_format(pattern[1])
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            time1 = {
                'hh': 9,
                'mm': 0,
                'nn': 'pm',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }

            time2 = {
                'hh': 12,
                'mm': 0,
                'nn': 'am',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original1)

        return time_list, original_list

    def _get_default_time_range(self, time_list=None, original_list=None):
        self.logger.info("_get_default_time_range")
        if time_list is None:
            time_list = []
        if original_list is None:
            original_list = []
        # patterns
        preference = re.compile(r'\b((?:no particular preference|no preference|no particular time|no time|'
                                r'anytime|any time|all day|full day|entire day|entireday)'
                                r'\s*(?:in|of|at)?\s*({timezone})?)\b'
                                .format(timezone=self.timezone_choices))
        patterns = preference.findall(self.processed_text.lower())

        for pattern in patterns:
            original1 = pattern[0].strip()
            tz = None
            if pattern[1]:
                tz = self.convert_to_pytz_format(pattern[1])
            if self.departure_flag:
                time_type = 'departure'
            elif self.return_flag:
                time_type = 'return'
            else:
                time_type = None
            time1 = {
                'hh': 12,
                'mm': 0,
                'nn': 'am',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'start',
                'time_type': time_type
            }

            time2 = {
                'hh': 11,
                'mm': 59,
                'nn': 'pm',
                'tz': tz or (None if not self.timezone else self.timezone.zone),
                'range': 'end',
                'time_type': time_type
            }

            time_list.append(time1)
            original_list.append(original1)
            time_list.append(time2)
            original_list.append(original1)

        return time_list, original_list

    def _remove_time_range_entities(self, time_list, original_list):
        self.logger.info("_remove_time_range_entities")
        time_list_final = []
        original_list_final = []
        for i, entity in enumerate(time_list):
            if not entity.get('range'):
                time_list_final.append(entity)
                original_list_final.append(original_list[i])
        return time_list_final, original_list_final

    def _update_processed_text(self, original_time_strings):
        self.logger.info("_update_processed_text")
        # self.logger.info(f"Self Processed Text ->{self.processed_text}")
        # self.logger.info(f"self tagged text -> {self.tagged_text}")
        # self.logger.info(f"Type --> {type(original_time_strings)}")
        for detected_text in original_time_strings:
            self.tagged_text = self.tagged_text.replace(detected_text, self.tag)
            self.processed_text = self.processed_text.replace(detected_text, '')

# time=English_Time_Detector(entity_name="time")
# print(time.detect_time(text="I'll be there after 10"))