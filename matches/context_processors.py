from .models import MatchNotification


def notifications(request):
    if not request.user.is_authenticated:
        return {'header_notifications': [], 'unread_notifications_count': 0}

    notifications_qs = (
        MatchNotification.objects.filter(recipient=request.user)
        .select_related('match')
        .order_by('-created_at')[:7]
    )
    header_notifications = list(notifications_qs)
    unread_notifications_count = MatchNotification.objects.filter(recipient=request.user, is_read=False).count()
    return {
        'header_notifications': header_notifications,
        'unread_notifications_count': unread_notifications_count,
    }
