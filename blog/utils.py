import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from blog.models import PostComment, Post


def trigger_author_comment_notification(post_comment_obj: PostComment, post_obj: Post):
    mail_title = f'New comment on post "{post_obj.title}"'
    post_url = settings.APP_DOMAIN + reverse('post-detail', args=[post_obj.id])

    # Render HTML template
    html_content = render_to_string('emails/new_comment.html', {
        'comment': post_comment_obj,
        'post': post_obj,
        'post_url': post_url,
        'app_domain': settings.APP_DOMAIN
    })

    # Plain text fallback
    mail_body = f'''{post_comment_obj.author.username} just commented on your post "{post_obj.title}":

"{post_comment_obj.content}"

Use the link below to view the post:
{post_url}

~ Seoto Notifications
'''

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [settings.EMAIL_HOST_USER]

    try:
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=mail_title,
            body=mail_body,
            from_email=mail_sender,
            to=mail_recipient
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except:
        logging.warning("Failed to notify author of a new comment.")