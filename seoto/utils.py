import ast
import os


class GetEnv:
    class NotFound(Exception):
        pass

    @classmethod
    def str(cls, var_name: str) -> str:
        var = os.environ.get(var_name)
        if not var: raise cls.NotFound(f"{var_name} not found")
        return var

    @classmethod
    def int(cls, var_name: str) -> int:
        return int(cls.str(var_name))

    @classmethod
    def bool(cls, var_name: str) -> bool:
        return ast.literal_eval(cls.str(var_name))

    @classmethod
    def tuple(cls, var_name: str) -> tuple:
        return tuple(cls.str(var_name).split(","))
