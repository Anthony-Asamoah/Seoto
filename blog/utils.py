import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from blog.models import PostComment, Post


def trigger_author_comment_notification(post_comment_obj: PostComment, post_obj: Post):
    mail_title = f'New comment on post "{post_obj.title}"'
    mail_body = f'''{post_comment_obj.author.username} just commented.
"
{post_comment_obj.content}
"
Use the link below to view the post.
{settings.APP_DOMAIN + reverse('post-detail', args=[post_obj.id])}

'''
    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [settings.EMAIL_HOST_USER]

    try:
        send_mail(mail_title, mail_body, mail_sender, mail_recipient, fail_silently=False)
    except:
        logging.warning("Failed to notify author of a new comment.")