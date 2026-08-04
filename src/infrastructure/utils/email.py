"""One way to send a branded email.

Every sender used to hand-roll the same EmailMultiAlternatives block. They now go through
`send_branded_email`, which renders the template, attaches the logo as an inline `cid:`
part, and sends. Inline beats a remote `<img>`: mail clients block remote images until the
recipient opts in, so a linked logo is invisible on first read.
"""

import logging
from email.message import MIMEPart
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class RelatedEmail(EmailMultiAlternatives):
    """Emits multipart/related instead of multipart/mixed.

    `cid:` references are only guaranteed to resolve inside multipart/related
    (RFC 2387); under Django's default multipart/mixed some clients list the logo as
    an attachment instead of drawing it. Django 6 removed the `mixed_subtype` hook
    that used to do this, so retype the root ourselves — the tree Django builds
    (alternative body first, resources after) is already the shape related wants.
    """

    def message(self, **kwargs):
        msg = super().message(**kwargs)
        if self.attachments and msg.get_content_type() == 'multipart/mixed':
            # set_type keeps the boundary parameter; replace_header would drop it.
            msg.set_type('multipart/related')
            msg.set_param('type', 'multipart/alternative')
        return msg


LOGO_CID = 'seoto-logo'
LOGO_PATH = Path(settings.SRC_DIR) / 'static' / 'img' / 'email-logo.png'

_logo_bytes = None


def _logo():
    """Read the logo once per process; it is the same file on every message."""
    global _logo_bytes
    if _logo_bytes is None:
        try:
            _logo_bytes = LOGO_PATH.read_bytes()
        except OSError:
            logger.warning('Email logo missing at %s; sending without it.', LOGO_PATH)
            _logo_bytes = b''
    return _logo_bytes


def send_branded_email(subject, template, context, to, text_body=None, fail_silently=False):
    """Render `template` against `context` and send it to `to`.

    `app_domain` is always injected — base_email.html's footer link is blank without it.
    Falls back to a tag-stripped copy of the HTML when no plain-text body is given.
    """
    recipients = [to] if isinstance(to, str) else [address for address in to if address]
    if not recipients:
        logger.warning('No recipients for %r; nothing sent.', subject)
        return False

    context = {
        'app_domain': getattr(settings, 'APP_DOMAIN', 'http://localhost:8000'),
        'logo_cid': LOGO_CID,
        **context,
    }
    html_body = render_to_string(template, context)

    message = RelatedEmail(
        subject=subject,
        body=text_body or strip_tags(html_body),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')

    logo = _logo()
    if logo:
        # MIMEPart, not MIMEImage: Django 6 deprecates MIMEBase attachments, and
        # `mixed_subtype = 'related'` was removed outright.
        part = MIMEPart()
        part.set_content(
            logo, maintype='image', subtype='png',
            cid=f'<{LOGO_CID}>', disposition='inline', filename='seoto.png',
        )
        message.attach(part)

    message.send(fail_silently=fail_silently)
    return True
