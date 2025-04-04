from .models import Business

def business_info(request):
    """Adds business name and logo to the context globally and checks if the user is a member of a business."""
    business_name = None
    business_logo = None
    user_businesses = None  # Initialize user_businesses variable
    is_member = False  # Add a flag to check if the user is a member of a business
    
    if request.user.is_authenticated:
        # Get the businesses associated with the authenticated user
        user_businesses = Business.objects.filter(user=request.user)
        
        if user_businesses.exists():
            # If businesses exist for the user, get the first business details
            first_business = user_businesses.first()
            business_name = first_business.name
            business_logo = first_business.icon.url if first_business.icon else None
            
            # Check if the user is a member of the business (you might need to adjust this according to your models)
            if request.user in first_business.members.all():  # Assuming 'members' is a related name for users in the business
                is_member = True

            print(f"Business Logo: {business_logo}")  # Debugging output

    # Return business info along with membership status
    return {
        'business_name': business_name,
        'business_logo': business_logo,
        'user_businesses': user_businesses,
        'is_member': is_member  # Add the membership status to the context
    }
