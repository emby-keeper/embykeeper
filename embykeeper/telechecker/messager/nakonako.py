from .base import Messager
from .common import GOOD_DAY_NIGHT, WATERY


class NakonakoMessager(Messager):
    name = "NakoNako"
    chat_name = "NakoNetwork"
    messages = [*GOOD_DAY_NIGHT]
