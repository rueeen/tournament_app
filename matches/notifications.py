from django.contrib.auth.models import User

from .models import Match, MatchNotification


def notify_users(*, recipients, actor: User, match: Match, notification_type: str, message: str):
    recipient_ids = {user.id for user in recipients if user and user.id != actor.id}
    if not recipient_ids:
        return

    notifications = [
        MatchNotification(
            recipient_id=recipient_id,
            actor=actor,
            match=match,
            notification_type=notification_type,
            message=message,
        )
        for recipient_id in recipient_ids
    ]
    MatchNotification.objects.bulk_create(notifications)
