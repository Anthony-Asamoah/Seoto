from django.db import models


class BaseChoices(models.TextChoices):
    @classmethod
    def names_list(cls) -> list[str]:
        return [member.name for member in cls]
