from __future__ import absolute_import
import re
from six.moves import range
def get_list_from_pipe_sep_string(text_string):
    text_list = text_string.split("|")
    return [x.lower().strip() for x in text_list if x.strip()]
