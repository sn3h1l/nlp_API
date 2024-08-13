from __future__ import absolute_import
import calendar
from datetime import datetime, timedelta, tzinfo  # FIXME: Change import to `import datetime`
import os
import pandas as pd
import pytz
import six
import requests
from ner.date.constant import POSITIVE_TIME_DIFF, NEGATIVE_TIME_DIFF, CONSTANT_FILE_KEY
from six.moves import range

def nth_weekday(weekday, n, ref_date):
    first_day_of_month = datetime(ref_date.year, ref_date.month, 1)
    first_weekday = first_day_of_month + timedelta(days=((weekday - calendar.monthrange(
        ref_date.year, ref_date.month)[0]) + 7) % 7)
    return first_weekday + timedelta(days=(n - 1) * 7)


def next_weekday(current_date, weekday, n):
    days_ahead = weekday - current_date.weekday()
    if days_ahead < 0:
        n = n + 1
    days_ahead += n * 7
    return current_date + timedelta(days=days_ahead)


def get_hour_min_diff(time1, time2):
    nn = POSITIVE_TIME_DIFF
    if time2 > time1:
        diff = time2 - time1
    else:
        diff = time1 - time2
        nn = NEGATIVE_TIME_DIFF
    minutes = (diff.seconds / 60) % 60
    hours = diff.seconds / 3600
    return hours, minutes, nn


def get_tuple_dict(csv_file):
    data_df = pd.read_csv(csv_file, encoding='utf-8')
    data_df = data_df.set_index(CONSTANT_FILE_KEY)
    records = data_df.to_records()
    tuple_records = {}
    for record in records:
        keys = record[0]
        keys = [x.strip().lower() for x in keys.split("|") if x.strip() != ""]
        for key in keys:
            tuple_records[key] = tuple(list(record)[1:])
    return tuple_records


def get_weekdays_for_month(weeknumber, month, year):
    calendar_month = calendar.monthcalendar(year, month)
    if weeknumber == -1:
        return [day for day in calendar_month[-1] if day != 0]
    elif 0 < weeknumber <= len(calendar_month):
        return [day for day in calendar_month[weeknumber - 1] if day != 0]
    return []


def is_valid_date(dd, mm, yy, tz=None):
    if dd and mm and yy:
        try:
            dt = datetime(year=yy, month=mm, day=dd)
            if tz:
                tz.localize(dt)
            return True
        except (ValueError, AttributeError):
            pass
    return False


def get_previous_month_number(mm, yy):
    if 1 <= mm <= 12:
        if mm == 1:
            mm = 12
            yy -= 1
        else:
            mm -= 1
    else:
        raise ValueError('mm should be between 1 and 12 inclusive')

    return mm, yy


def get_next_month_number(mm, yy):
    if 1 <= mm <= 12:
        if mm == 12:
            mm = 1
            yy += 1
        else:
            mm += 1
    else:
        raise ValueError('mm should be between 1 and 12 inclusive')

    return mm, yy


def get_previous_date_with_dd(dd, before_datetime):
    end_dd = before_datetime.day
    mm = before_datetime.month
    yy = before_datetime.year

    if dd > end_dd:
        mm, yy = get_previous_month_number(mm=mm, yy=yy)
    for _ in range(3):
        if is_valid_date(dd=dd, mm=mm, yy=yy):
            return dd, mm, yy
        mm, yy = get_previous_month_number(mm=mm, yy=yy)

    return None, None, None


def get_next_date_with_dd(dd, after_datetime):
    start_dd = after_datetime.day
    mm = after_datetime.month
    yy = after_datetime.year

    if dd < start_dd:
        mm, yy = get_next_month_number(mm=mm, yy=yy)
    for _ in range(3):
        if is_valid_date(dd=dd, mm=mm, yy=yy):
            return dd, mm, yy
        mm, yy = get_next_month_number(mm=mm, yy=yy)

    return None, None, None


def get_timezone(timezone, ignore_errors=False):
    if (not isinstance(timezone, six.string_types) and
            isinstance(timezone, tzinfo) and
            hasattr(timezone, 'localize')):
        return timezone

    try:
        timezone = pytz.timezone(timezone)
    except Exception as e:
        if ignore_errors:
            timezone = pytz.timezone('UTC')
        else:
            return None
    return timezone


def get_list_from_pipe_sep_string(text_string):
    text_list = text_string.split("|")
    return [x.lower().strip() for x in text_list if x.strip()]

def unicode_urlencode(params):
    """
    Method to convert the params to url encode data
    Args:
        params (dict): dict containing requests params
    Returns:
        (str): url string with params encoded
    """
    if isinstance(params, dict):
        params = list(params.items())
    return six.moves.urllib.parse.urlencode(
        [(
            k, isinstance(
                v,
                six.text_type
            ) and v.encode('utf-8') or v
        ) for (k, v) in params
        ]
    )
def get_lang_data_path(detector_path, lang_code):
    data_directory_path = os.path.abspath(
        os.path.join(
            os.path.dirname(detector_path).rstrip(os.sep),
            lang_code,
            'data'
        )
    )
    return data_directory_path
def translate_text(text, source_language_code, target_language_code='en'):
    """
    Args:
       text (str): Text snippet which needs to be translated
       source_language_code (str): ISO-639-1 code for language script corresponding to text ''
       target_language_code (str): ISO-639-1 code for target language script
    Return:
       dict: Dictionary containing two keys corresponding to 'status'(bool) and 'translated text'(unicode)
       For example: Consider following example
                    text: 'नमस्ते आप कैसे हैं'
                    'source_language_code': 'hi'
                    'target_language_code': 'en'

                    translate_text(text, 'hi', 'en')
                    >> {'status': True,
                       'translated_text': 'Hello how are you'}
    """
    response = {'translated_text': None, 'status': False}
    TRANSLATE_URL = "https://www.googleapis.com/language/translate/v2?key="
    query_params = {"q": text, "format": "text", "source": source_language_code, "target": target_language_code}
    url =    + "&" + unicode_urlencode(query_params)
    request = requests.get(url, timeout=2)
    if request.status_code == 200:
        translate_response = request.json()
        response['translated_text'] = translate_response["data"]["translations"][0]["translatedText"]
        response['status'] = True
    return response