from django.core import mail


def sent():
    return mail.outbox[-1].message()


def parts(message):
    return {part.get_content_type() for part in message.walk()}
