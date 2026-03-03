import ast
import os

from django.db import models


class GetEnv:
    class NotFound(Exception):
        pass

    @classmethod
    def str(cls, var_name: str, default=None) -> str:
        var = os.environ.get(var_name)
        if not var and not default: raise cls.NotFound(f"{var_name} not found")
        return var or default

    @classmethod
    def int(cls, var_name: str, default=None) -> int:
        return int(cls.str(var_name, default))

    @classmethod
    def float(cls, var_name: str, default: float = None) -> float:
        try:
            return float(cls.str(var_name))
        except cls.NotFound:
            if default is not None:
                return default
            raise

    @classmethod
    def bool(cls, var_name: str, default: bool = None) -> bool:
        try:
            return ast.literal_eval(cls.str(var_name))
        except cls.NotFound:
            if default is not None:
                return default
            raise

    @classmethod
    def tuple(cls, var_name: str, default=None) -> tuple:
        return tuple(cls.str(var_name, default).split(","))


class BaseChoices(models.TextChoices):
    @classmethod
    def names_list(cls) -> list[str]:
        return [member.name for member in cls]
