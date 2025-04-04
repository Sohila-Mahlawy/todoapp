from .models import Notification
from businesses.models import Business

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

def business_details(request):
    """
    Context processor that adds business details to all templates.
    This makes the business name and logo available in the sidebar.
    """
    business_name = None
    business_logo = None
    
    if request.user.is_authenticated:
        # Check for owned businesses first
        user_businesses = Business.objects.filter(user=request.user)
        
        # If user owns any businesses, use the first one
        if user_businesses.exists():
            business = user_businesses.first()
            business_name = business.name
            if business.icon:
                business_logo = business.icon.url
        
        # If user doesn't own businesses, check if they're a member of any
        elif hasattr(request.user, 'member_of_businesses'):
            member_businesses = request.user.member_of_businesses.all()
            if member_businesses.exists():
                business = member_businesses.first()
                business_name = business.name
                if business.icon:
                    business_logo = business.icon.url
    
    return {
        'business_name': business_name,
        'business_logo': business_logo
    } 