from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync

try:
    from channels.layers import get_channel_layer
except Exception:  # pragma: no cover
    get_channel_layer = None

from .models import MealOrder


def _broadcast_to_user(user_id: int, event: str, payload: dict):
    if not get_channel_layer:
        return
    try:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"user_{user_id}",
            {
                "type": "foodie_event",
                "event": event,
                "payload": payload,
            },
        )
    except Exception:
        # Avoid crashing on broadcast errors
        pass


@receiver(pre_save, sender=MealOrder)
def capture_old_status(sender, instance: MealOrder, **kwargs):
    if instance.pk:
        try:
            old = MealOrder.objects.get(pk=instance.pk)
        except MealOrder.DoesNotExist:
            old = None
        instance._old_confirmed = getattr(old, 'is_confirmed', False)
        instance._old_purchased = getattr(old, 'is_purchased', False)
        instance._old_delivered = getattr(old, 'is_delivered', False)
        instance._old_not_available = getattr(old, 'not_available', False)
    else:
        instance._old_confirmed = False
        instance._old_purchased = False
        instance._old_delivered = False
        instance._old_not_available = False


@receiver(post_save, sender=MealOrder)
def order_notifications(sender, instance: MealOrder, created: bool, **kwargs):
    user = instance.user
    subject = None
    message = None

    if created:
        subject = "Order placed"
        message = (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Your order for '{instance.meal}' (x{instance.quantity}) has been received.\n"
            f"We will notify you on updates."
        )
        _broadcast_to_user(user.id, 'order.created', {
            'id': instance.id,
            'meal': str(instance.meal),
            'quantity': instance.quantity,
        })
    else:
        # not_available toggled on
        if (not getattr(instance, '_old_not_available', False)) and instance.not_available:
            subject = "Order item not available"
            message = (
                f"Hi {user.get_full_name() or user.username},\n\n"
                f"The item for your order '{instance.meal}' is currently not available. "
                f"Please edit your order to choose an alternative."
            )
            _broadcast_to_user(user.id, 'order.not_available', {
                'id': instance.id,
                'meal': str(instance.meal),
            })
        # transitioned back to pending (after edit)
        elif getattr(instance, '_old_not_available', False) and not instance.not_available and not instance.is_confirmed and not instance.is_purchased and not instance.is_delivered:
            subject = "Order updated"
            message = (
                f"Hi {user.get_full_name() or user.username},\n\n"
                f"Your order has been updated and is now pending confirmation."
            )
            _broadcast_to_user(user.id, 'order.updated_pending', {
                'id': instance.id,
                'meal': str(instance.meal),
                'quantity': instance.quantity,
            })
        # other status updates
        elif (not getattr(instance, '_old_confirmed', False)) and instance.is_confirmed:
            subject = "Order confirmed"
            message = f"Your order for '{instance.meal}' has been confirmed."
            _broadcast_to_user(user.id, 'order.confirmed', {'id': instance.id, 'meal': str(instance.meal)})
        elif (not getattr(instance, '_old_purchased', False)) and instance.is_purchased:
            subject = "Order purchased"
            message = f"Your order for '{instance.meal}' has been purchased."
            _broadcast_to_user(user.id, 'order.purchased', {'id': instance.id, 'meal': str(instance.meal)})
        elif (not getattr(instance, '_old_delivered', False)) and instance.is_delivered:
            subject = "Order delivered"
            message = f"Your order for '{instance.meal}' has been delivered."
            _broadcast_to_user(user.id, 'order.delivered', {'id': instance.id,  'meal': str(instance.meal)})

    # Send email if we have a subject and user email
    if subject and user and user.email:
        try:
            send_mail(subject, message, getattr(settings, 'EMAIL_HOST_USER', None), [user.email], fail_silently=True)
        except Exception:
            pass
