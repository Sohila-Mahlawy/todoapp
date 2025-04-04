from .models import Notification

def notifications(request):
    """
    Context processor that adds recent notifications to all templates.
    """
    if request.user.is_authenticated:
        # Get only unread notifications for the dropdown display
        user_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Also provide a count of all unread notifications
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return {
            'notifications': user_notifications,
            'unread_notification_count': unread_count
        }
    return {'notifications': [], 'unread_notification_count': 0} 