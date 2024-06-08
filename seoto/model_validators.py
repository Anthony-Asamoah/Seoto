import string

from django.core.exceptions import ValidationError


class Validators:
    """model validators"""

    @classmethod
    def str(cls, arg: str):
        arg = arg.strip()
        arg = arg.strip(string.punctuation)
        if not arg:
            raise ValidationError("Invalid Input")
