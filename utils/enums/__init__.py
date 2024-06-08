from enum import Enum


class DefaultEnum(Enum):
    @classmethod
    def keys(cls):
        return tuple(i.name for i in cls)

    @classmethod
    def values(cls):
        return tuple(i.name for i in cls)

    @classmethod
    def key_value_pairs(cls):
        return ((i.name, i.value) for i in cls)

    @classmethod
    def value_key_pairs(cls):
        return ((i.value, i.name) for i in cls)

    @classmethod
    def value_value_pairs(cls):
        return ((i.value, i.name) for i in cls)
