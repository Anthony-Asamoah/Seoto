import logging

from django.conf import settings
from django.urls import reverse

from infrastructure.utils import send_branded_email

from domains.apps.blog.models import PostComment, Post, PostReadGroup


def pluralize_label(text):
    """Ensure a label (word or phrase) is in plural lowercase form.
    Only the last word of the phrase is pluralized.
    """
    if not text:
        return text
    words = text.lower().split()
    last = words[-1]
    # Already ends with 's' but not 'ss' — likely already plural
    if last.endswith('s') and not last.endswith('ss'):
        return ' '.join(words)
    # Ends with 'ss', 'sh', 'ch', 'x', 'z' → add 'es'
    if last.endswith(('ss', 'sh', 'ch', 'x', 'z')):
        words[-1] = last + 'es'
    # Consonant + 'y' → replace 'y' with 'ies'
    elif last.endswith('y') and len(last) > 1 and last[-2] not in 'aeiou':
        words[-1] = last[:-1] + 'ies'
    else:
        words[-1] = last + 's'
    return ' '.join(words)


def singularize_label(text):
    """Ensure a label (word or phrase) is in singular lowercase form.
    Only the last word of the phrase is singularized.
    """
    if not text:
        return text
    words = text.lower().split()
    last = words[-1]
    # 'ies' → 'y' (technologies → technology)
    if last.endswith('ies') and len(last) > 3:
        words[-1] = last[:-3] + 'y'
    # 'sses'/'xes'/'ches'/'shes' → remove 'es' (classes→class, boxes→box, churches→church)
    elif last.endswith(('sses', 'xes', 'ches', 'shes')):
        words[-1] = last[:-2]
    # ends in 's' but not 'ss' → remove 's'
    elif last.endswith('s') and not last.endswith('ss'):
        words[-1] = last[:-1]
    # already singular — leave as-is
    return ' '.join(words)


def trigger_author_comment_notification(post_comment_obj: PostComment, post_obj: Post):
    mail_title = f'New comment on post "{post_obj.title}"'
    post_url = settings.APP_DOMAIN + reverse('post-detail', args=[post_obj.id])

    try:
        send_branded_email(
            mail_title,
            'emails/new_comment.html',
            {
                'comment': post_comment_obj,
                'post': post_obj,
                'post_url': post_url,
            },
            [settings.EMAIL_HOST_USER],
            text_body=f'''{post_comment_obj.author.username} just commented on your post "{post_obj.title}":

"{post_comment_obj.content}"

Use the link below to view the post:
{post_url}

~ Seoto Notifications
''',
        )
    except Exception:
        logging.warning("Failed to notify author of a new comment.")


def notify_user_added_to_group(user, group: PostReadGroup):
    """Notify a user when they are added to a read group"""
    mail_title = f'Added to Read Group: {group.label}'

    try:
        send_branded_email(
            mail_title,
            'emails/group_added.html',
            {
                'user': user,
                'group': group,
                'group_owner': group.author,
            },
            [user.email],
            text_body=f'''Hello {user.first_name or user.username},

{group.author.username} has added you to their read group "{group.label}" on Seoto.

Being in this group means you now have access to private posts that {group.author.username} has shared with this group.

You can view your groups and leave at any time by visiting:
{settings.APP_DOMAIN}/blog/read-groups/my/

~ Seoto Notifications
''',
        )
    except Exception:
        logging.warning(f"Failed to notify {user.username} about being added to group {group.label}.")


def notify_user_removed_from_group(user, group: PostReadGroup):
    """Notify a user when they are removed from a read group"""
    mail_title = f'Removed from Read Group: {group.label}'

    try:
        send_branded_email(
            mail_title,
            'emails/group_removed.html',
            {
                'user': user,
                'group': group,
                'group_owner': group.author,
            },
            [user.email],
            text_body=f'''Hello {user.first_name or user.username},

{group.author.username} has removed you from their read group "{group.label}" on Seoto.

You will no longer have access to private posts that were shared with this group.

~ Seoto Notifications
''',
        )
    except Exception:
        logging.warning(f"Failed to notify {user.username} about being removed from group {group.label}.")


def notify_owner_user_left_group(user, group: PostReadGroup):
    """Notify group owner when a user leaves their group"""
    mail_title = f'{user.username} left your Read Group: {group.label}'

    mail_body = f'''Hello {group.author.first_name or group.author.username},

{user.username} has left your read group "{group.label}".

They will no longer have access to private posts shared with this group.

Manage your group at:
{settings.APP_DOMAIN}/blog/read-groups/{group.id}/edit/

~ Seoto Notifications
'''

    try:
        send_branded_email(
            mail_title,
            'emails/group_left.html',
            {
                'user': user,
                'group': group,
                'group_owner': group.author,
            },
            [group.author.email],
            text_body=mail_body,
        )
    except Exception:
        logging.warning(f"Failed to notify {group.author.username} about {user.username} leaving group {group.label}.")