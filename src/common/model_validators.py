import string

from django.core.exceptions import ValidationError
from random_string_detector import RandomStringDetector

random_string_checker = RandomStringDetector()


class Validators:
    """model validators"""

    @classmethod
    def str(cls, arg: str):
        arg = arg.strip()
        arg = arg.strip(string.punctuation)
        if not arg:
            raise ValidationError("Invalid Input")


def is_random_string(string: str) -> bool:
    if not string or not string.strip(): return False
    return random_string_checker(string.lower())
