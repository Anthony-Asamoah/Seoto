import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from blog.models import PostComment, Post, PostReadGroup


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


def notify_user_added_to_group(user, group: PostReadGroup):
    """Notify a user when they are added to a read group"""
    mail_title = f'Added to Read Group: {group.label}'

    # Render HTML template
    html_content = render_to_string('emails/group_added.html', {
        'user': user,
        'group': group,
        'group_owner': group.author,
        'app_domain': settings.APP_DOMAIN
    })

    # Plain text fallback
    mail_body = f'''Hello {user.first_name or user.username},

{group.author.username} has added you to their read group "{group.label}" on Seoto.

Being in this group means you now have access to private posts that {group.author.username} has shared with this group.

You can view your groups and leave at any time by visiting:
{settings.APP_DOMAIN}/blog/read-groups/my/

~ Seoto Notifications
'''

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [user.email]

    try:
        email = EmailMultiAlternatives(
            subject=mail_title,
            body=mail_body,
            from_email=mail_sender,
            to=mail_recipient
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except:
        logging.warning(f"Failed to notify {user.username} about being added to group {group.label}.")


def notify_user_removed_from_group(user, group: PostReadGroup):
    """Notify a user when they are removed from a read group"""
    mail_title = f'Removed from Read Group: {group.label}'

    # Render HTML template
    html_content = render_to_string('emails/group_removed.html', {
        'user': user,
        'group': group,
        'group_owner': group.author,
        'app_domain': settings.APP_DOMAIN
    })

    # Plain text fallback
    mail_body = f'''Hello {user.first_name or user.username},

{group.author.username} has removed you from their read group "{group.label}" on Seoto.

You will no longer have access to private posts that were shared with this group.

~ Seoto Notifications
'''

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [user.email]

    try:
        email = EmailMultiAlternatives(
            subject=mail_title,
            body=mail_body,
            from_email=mail_sender,
            to=mail_recipient
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except:
        logging.warning(f"Failed to notify {user.username} about being removed from group {group.label}.")


def notify_owner_user_left_group(user, group: PostReadGroup):
    """Notify group owner when a user leaves their group"""
    mail_title = f'{user.username} left your Read Group: {group.label}'

    # Render HTML template
    html_content = render_to_string('emails/group_left.html', {
        'user': user,
        'group': group,
        'group_owner': group.author,
        'app_domain': settings.APP_DOMAIN
    })

    # Plain text fallback
    mail_body = f'''Hello {group.author.first_name or group.author.username},

{user.username} has left your read group "{group.label}".

They will no longer have access to private posts shared with this group.

Manage your group at:
{settings.APP_DOMAIN}/blog/read-groups/{group.id}/edit/

~ Seoto Notifications
'''

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [group.author.email]

    try:
        email = EmailMultiAlternatives(
            subject=mail_title,
            body=mail_body,
            from_email=mail_sender,
            to=mail_recipient
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except:
        logging.warning(f"Failed to notify {group.author.username} about {user.username} leaving group {group.label}.")