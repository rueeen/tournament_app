from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth.models import User
from django.utils import timezone

from .models import Match, MatchNotification


class NotificationService:
    @staticmethod
    def create_notification(
        *,
        recipient: User,
        actor: User,
        match: Match,
        notification_type: str,
        title: str,
        message: str,
        action_url: str = '',
        action_label: str = '',
        metadata: dict | None = None,
        dedupe_window_seconds: int = 10,
    ) -> MatchNotification | None:
        if not recipient or not actor or recipient.id == actor.id:
            return None

        metadata = metadata or {}
        dedupe_since = timezone.now() - timezone.timedelta(seconds=dedupe_window_seconds)
        already_exists = MatchNotification.objects.filter(
            recipient=recipient,
            actor=actor,
            match=match,
            notification_type=notification_type,
            message=message,
            created_at__gte=dedupe_since,
        ).exists()
        if already_exists:
            return None

        return MatchNotification.objects.create(
            recipient=recipient,
            actor=actor,
            match=match,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            action_label=action_label,
            metadata=metadata,
            is_read=False,
            read_at=None,
        )

    @staticmethod
    def create_bulk_notifications(
        *,
        recipients: Iterable[User],
        actor: User,
        match: Match,
        notification_type: str,
        title: str,
        message: str,
        action_url: str = '',
        action_label: str = '',
        metadata: dict | None = None,
    ) -> list[MatchNotification]:
        created_notifications = []
        for recipient in recipients:
            notification = NotificationService.create_notification(
                recipient=recipient,
                actor=actor,
                match=match,
                notification_type=notification_type,
                title=title,
                message=message,
                action_url=action_url,
                action_label=action_label,
                metadata=metadata,
            )
            if notification:
                created_notifications.append(notification)
        return created_notifications

    @staticmethod
    def mark_notification_read(notification: MatchNotification):
        notification.mark_as_read()

    @staticmethod
    def mark_all_read_for_user(user: User):
        now = timezone.now()
        MatchNotification.objects.filter(recipient=user, is_read=False).update(is_read=True, read_at=now)


def notify_users(
    *,
    recipients,
    actor: User,
    match: Match,
    notification_type: str,
    message: str,
    title: str = 'Notificación',
    action_url: str = '',
    action_label: str = '',
    metadata: dict | None = None,
):
    NotificationService.create_bulk_notifications(
        recipients=recipients,
        actor=actor,
        match=match,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        action_label=action_label,
        metadata=metadata,
    )
