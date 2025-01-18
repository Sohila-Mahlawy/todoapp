from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from models import UnloggedUserTask,LoggedUserTask, ProUserTask,TaskFeedback,CustomUser, SubscriptionOrder, UserProfile
from projects.models import Project
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.timezone import now
from django.contrib import messages
import requests
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash




# Function to submit feedback for a task
@login_required
def submit_feedback(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id, user=request.user)
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        feedback = TaskFeedback.objects.create(task=task, feedback=feedback_text)
        return render(request, 'feedback_submitted.html', {'feedback': feedback})
    return render(request, 'submit_feedback.html', {'task': task})


def dashboard_view(request):
    user = request.user
    context = {}

    if user.is_authenticated:
        from businesses.models import Business
        business_name = None
        user_businesses = Business.objects.filter(user=request.user)
        user_business_image = None
        user_members = []

        if user.subscription_type == 'pro':
            tasks = ProUserTask.objects.filter(user=user).order_by('-created_at')
            if user_businesses.exists():
                first_business = user_businesses.first()
                business_name = first_business.name
                user_business_image = first_business.icon.url if first_business.icon else None

                user_members = []
                for member in first_business.members.all():
                    profile, created = UserProfile.objects.get_or_create(user=member)
                    member_info = {
                        'username': member.username,
                        'email': member.email,
                        'role': member.role,
                        'id': member.id,
                        'status': profile.logged_in_status,
                        'is_active': profile.status
                    }
                    user_members.append(member_info)
            else:
                user_business_image = None
                user_members = []
            print(f"User Members: {list(user_members)}")

        else:
            user_tasks = LoggedUserTask.objects.filter(user=user).order_by('-created_at')
            assigned_tasks = ProUserTask.objects.filter(assigned_to=user).order_by('-created_at')
            tasks = sorted(
                list(user_tasks) + list(assigned_tasks),
                key=lambda t: t.created_at,
                reverse=True
            )

        completed_task_count = sum(1 for task in tasks if task.is_done)
        tasks = tasks[:5]

        context['tasks'] = tasks
        context['task_count'] = len(tasks)
        context['completed_task_count'] = completed_task_count
        context['is_pro_user'] = user.subscription_type == 'pro'
        context['user'] = user
        context['business_name'] = business_name
        context['user_business_image'] = user_business_image
        context['user_businesses'] = user_businesses
        context['user_members'] = user_members
        context['has_businesses'] = user_businesses.exists()

        return render(request, 'index.html', context)

    else:
        ip_address = get_client_ip(request)
        tasks = UnloggedUserTask.objects.filter(ip_address=ip_address).order_by('-created_at')
        completed_task_count = tasks.filter(is_done=True).count()
        tasks = tasks[:5]

        context['tasks'] = tasks
        context['task_count'] = len(tasks)
        context['completed_task_count'] = completed_task_count

        return render(request, 'index.html', context)
    


def update_task_status(request, task_id):
    if request.method == "POST":
        task = None
        if request.user.is_authenticated:
            # For logged-in users
            if request.user.subscription_type == 'pro':
                task = ProUserTask.objects.get(id=task_id, user=request.user)
            else:
                task = LoggedUserTask.objects.get(id=task_id, user=request.user)
        else:
            # For unlogged users (using IP address to identify)
            task = UnloggedUserTask.objects.get(id=task_id, ip_address=get_client_ip(request))

        # Toggle the task's `is_done` field
        task.is_done = not task.is_done
        task.save()

        return JsonResponse({'status': 'success', 'is_done': task.is_done})

    return JsonResponse({'status': 'failed'})

def trial_middleware(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            user = request.user
            if user.subscription_type == 'free':
                if user.trial_start_date:
                    trial_end_date = user.trial_start_date + timedelta(weeks=2)
                    if datetime.now().date() > trial_end_date:
                        user.subscription_type = 'free'
                        user.role = 'expired'
                        user.save()
                        return redirect('trial_expired')
            elif user.subscription_type == 'pro':
                if user.pro_subscription_date and datetime.now().date() - user.pro_subscription_date > timedelta(weeks=4):
                    return redirect('pro_payment_required')
        return get_response(request)
    return middleware

@login_required
def subscribe_pro(request):
    user = request.user
    if user.subscription_type == 'pro':
        # Render a Pro-specific page
        return render(request, 'already_pro.html', {'user': user})
    
    if request.method == 'POST':
        if user.subscription_type == 'free':
            if not user.pro_subscription_date or (now().date() - user.pro_subscription_date).days > 30:
                # Start a free Pro trial
                user.subscription_type = 'pro'
                user.role = 'team_leader'
                user.pro_subscription_date = now().date()
                user.save()
                messages.success(request, "Enjoy your free Pro trial!")
                return redirect('dashboard')
            else:
                # Redirect to payment page
                messages.error(request, "You have already used your free trial. Please subscribe to Pro.")
                return redirect('payment_page')  # Replace with your payment page URL or view name
    return render(request, 'subscribe_pro.html')



def pay(request):
    # Step 1: Set and Validate the Amount
    amount = 300  # Fixed amount in EGP
    if amount <= 0:
        messages.error(request, 'Invalid amount. Must be greater than zero.')
        return redirect('dashboard')

    # Step 2: Get Auth Token
    try:
        auth_response = requests.post(
            'https://accept.paymobsolutions.com/api/auth/tokens',
            json={'api_key': settings.PAYMOB_API_KEY}
        )
        auth_response.raise_for_status()
        auth_token = auth_response.json().get('token')
        if not auth_token:
            raise ValueError('No auth token received from Paymob.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error obtaining auth token: {e}')
        return redirect('dashboard')

    # Step 3: Create Order
    try:
        unique_order_id = str(uuid.uuid4())
        order_response = requests.post(
            'https://accept.paymobsolutions.com/api/ecommerce/orders',
            json={
                'auth_token': auth_token,
                'delivery_needed': False,
                'amount_cents': amount * 100,  # Convert to cents
                'currency': 'EGP',
                'merchant_order_id': unique_order_id,
            }
        )
        order_response.raise_for_status()
        order_id = order_response.json().get('id')
        if not order_id:
            raise ValueError('No order ID received from Paymob.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error creating order: {e}')
        return redirect('dashboard')

    # Step 4: Generate Payment Key
    try:
        billing_data = {
            'first_name': request.user.first_name or 'First',
            'last_name': request.user.last_name or 'Last',
            'street': '123 Main St',  # Replace with real data
            'building': '1',
            'floor': '1',
            'apartment': '1A',
            'city': 'Cairo',
            'state': 'Cairo',
            'country': 'EGY',  # ISO code
            'postal_code': '3753450',
            'email': request.user.email or 'user@example.com',
            'phone_number': '01145871860',
        }
        payment_key_response = requests.post(
            'https://accept.paymobsolutions.com/api/acceptance/payment_keys',
            json={
                'auth_token': auth_token,
                'amount_cents': amount * 100,
                'expiration': 3600,
                'order_id': order_id,
                'currency': 'EGP',
                'integration_id': settings.PAYMOB_INTEGRATION_ID,
                'billing_data': billing_data,
            }
        )
        payment_key_response.raise_for_status()
        payment_key = payment_key_response.json().get('token')
        if not payment_key:
            raise ValueError('No payment key received.')
    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'Error generating payment key: {e}')
        return redirect('dashboard')

    # Step 5: Create Subscription Order
    try:
        subscription_order = SubscriptionOrder.objects.create(
            user=request.user,
            payment_status='Pending',
            payment_key=payment_key,
            amount_cents=amount * 100,
        )
    except Exception as e:
        messages.error(request, f'Error creating subscription order: {e}')
        return redirect('dashboard')

    # Step 6: Redirect to Payment Page
    payment_url = f'https://accept.paymobsolutions.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}'
    return redirect(payment_url)


def payment_result(request):
    # Extract payment result data
    payment_data = request.POST
    payment_key = payment_data.get('payment_token')
    payment_status = payment_data.get('success', 'false') == 'true'

    try:
        # Fetch the related subscription order
        subscription_order = SubscriptionOrder.objects.filter(payment_key=payment_key).first()
        if not subscription_order:
            messages.error(request, 'Payment not found.')
            return redirect('dashboard')

        # Update payment and subscription details
        if payment_status:
            subscription_order.payment_status = 'Completed'
            subscription_order.save()

            # Update user's subscription
            user = subscription_order.user
            user.subscription_type = 'pro'
            user.pro_subscription_date = timezone.now().date()
            user.subscription_end_date = user.pro_subscription_date + timedelta(days=30)
            user.save()

            messages.success(request, 'Payment successful! Welcome to Pro membership.')
        else:
            subscription_order.payment_status = 'Failed'
            subscription_order.save()
            messages.error(request, 'Payment failed. Please try again.')
    except Exception as e:
        messages.error(request, f'Error processing payment result: {e}')

    return redirect('dashboard')


@login_required
def members_dashboard_view(request):
    from businesses.models import Business
    user = request.user
    user_businesses = Business.objects.filter(members=user)  # Assuming you have a ManyToMany relationship

    if user_businesses.exists():
        # Get the first business the user is a member of
        first_business = user_businesses.first()
        user_members = first_business.members.all()  # Assuming 'members' is a related name for the user field

        context = {
            'user_members': user_members,
            'business_name': first_business.name,  # Pass the business name to the template
        }
        return render(request, 'members_dashboard.html', context)
    else:
        # Redirect to a different page if the user is not a member of any business
        return redirect('dashboard')  # Replace with your desired route




@login_required
def user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'user_detail.html', {'user': user})
