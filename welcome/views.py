import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import UnloggedUserTask,LoggedUserTask, Notification,UISettings , CalendarEvent , ProUserTask,TaskFeedback,CustomUser, SubscriptionOrder, UserProfile
from projects.models import Project
from tasks.views import get_client_ip,user_tasks_view
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from datetime import timedelta, datetime
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.timezone import now
from django.contrib import messages
import requests
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from urllib.parse import quote_plus
import uuid
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from django.db.models.functions import TruncDate
from django.db.models import Count
from .utils import business_required, pro_required
import stripe  # Add this line
from django.http import HttpResponse  # Add this line
from django.views.decorators.http import require_POST


@pro_required
@login_required
def submit_feedback(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id, user=request.user)
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        feedback = TaskFeedback.objects.create(task=task, feedback=feedback_text)
        return render(request, 'feedback_submitted.html', {'feedback': feedback})
    return render(request, 'submit_feedback.html', {'task': task})


def dashboard_view(request):
    from datetime import timedelta, datetime
    context = {}
    user = request.user

    # Initialize default values for all users
    context.update({
        'is_authenticated': False,
        'tasks': [],
        'task_count': 0,
        'completed_task_count': 0,
        'is_pro_user': False,
        'business_name': None,
        'user_business_image': None,
        'user_members': [],
        'has_more_members': False,
        'notifications': [],
        'user_projects': [],
        'project_count': 0,
        'nearest_tasks': [],
        'selected_project_id': None,
        'chart_dates': [(timezone.now().date() - timedelta(days=x)).strftime('%a') for x in range(6, -1, -1)],
        'business_tasks_data': [0] * 7,  # Seven zeros for the week
        'today_active_users': 0,
        'member_count': 0,
        'has_businesses': False,
        'user_businesses': None
    })

    now = timezone.now()

    # Handle nearest tasks for both logged and unlogged users
    if user.is_authenticated:
        # For logged-in users
        nearest_query = ProUserTask.objects.filter(
            Q(user=user) | Q(assigned_to=user),
            due_date__gte=now,
            is_done=False
        ).exclude(due_date__isnull=True)
        
        # Add logged user tasks
        logged_tasks_query = LoggedUserTask.objects.filter(
            user=user,
            due_date__gte=now,
            is_done=False
        ).exclude(due_date__isnull=True)
        
        nearest_query = list(nearest_query) + list(logged_tasks_query)
    else:
        # For unlogged users (using IP address to identify)
        ip_address = get_client_ip(request)
        nearest_query = UnloggedUserTask.objects.filter(
            ip_address=ip_address,
            due_date__gte=now,
            is_done=False
        ).exclude(due_date__isnull=True)

    # Sort all tasks by due date and get the nearest one
    nearest_tasks = sorted(nearest_query, key=lambda t: t.due_date)[:1] if nearest_query else []

    # Process nearest task if exists
    if nearest_tasks:
        task = nearest_tasks[0]
        if task.due_date:
            total_time = task.due_date - task.created_at
            elapsed_time = now - task.created_at
            total_seconds = total_time.total_seconds()
            elapsed_seconds = elapsed_time.total_seconds()

            task.progress_percent = min(100, (elapsed_seconds / total_seconds) * 100) if total_seconds > 0 else 100
            task.is_urgent = (task.due_date - now) <= timedelta(hours=24)
        else:
            task.progress_percent = 0
            task.is_urgent = False

    context['nearest_tasks'] = nearest_tasks

    # If user is not authenticated, return the default context
    if not user.is_authenticated:
        return render(request, 'index.html', context)

    # If we get here, user is authenticated, update context
    context['is_authenticated'] = True

    # Fetch unread notifications
    context['notifications'] = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')

    from businesses.models import Business
    user_businesses = Business.objects.filter(user=request.user)
    context['has_businesses'] = user_businesses.exists()
    context['user_businesses'] = user_businesses

    # Get projects information
    user_projects_created = Project.objects.filter(created_by=user)
    user_projects_member = Project.objects.filter(members=user)
    user_projects = (user_projects_created | user_projects_member).distinct()
    context['user_projects'] = user_projects
    context['project_count'] = user_projects.count()

    # Handle tasks based on subscription type
    if request.user.subscription_type.lower() in ['pro', 'business']:
        tasks = ProUserTask.objects.filter(user=user).order_by('-created_at')
        # Get selected project from URL parameters
        selected_project_id = request.GET.get('project')
        context['selected_project_id'] = selected_project_id
        if selected_project_id and selected_project_id != 'all':
            tasks = tasks.filter(project_id=selected_project_id)
    else:
        user_tasks = LoggedUserTask.objects.filter(user=user).order_by('-created_at')
        assigned_tasks = ProUserTask.objects.filter(assigned_to=user).order_by('-created_at')
        
        # Get selected project from URL parameters
        selected_project_id = request.GET.get('project')
        context['selected_project_id'] = selected_project_id
        if selected_project_id and selected_project_id != 'all':
            assigned_tasks = assigned_tasks.filter(project_id=selected_project_id)
        
        tasks = sorted(
            list(user_tasks) + list(assigned_tasks),
            key=lambda t: t.created_at,
            reverse=True
        )

    tasks = tasks[:5]
    context['tasks'] = tasks
    context['task_count'] = len(tasks)
    context['completed_task_count'] = sum(1 for task in tasks if task.is_done)
    context['is_pro_user'] = user.subscription_type == 'pro'

    # Handle business-related data if business exists
    if user_businesses.exists():
        business = user_businesses.first()
        context['business_name'] = business.name
        context['user_business_image'] = business.icon.url if business.icon else None

        # Get business projects
        business_projects = Project.objects.filter(business=business)

        # Get business tasks data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)
        date_range = [start_date + timedelta(days=x) for x in range(7)]

        business_tasks = ProUserTask.objects.filter(
            Q(project__in=business_projects) |
            Q(user__in=business.members.all()),
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_done=True
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        business_tasks_dict = {item['date']: item['count'] for item in business_tasks}
        context['business_tasks_data'] = [business_tasks_dict.get(date, 0) for date in date_range]

        # Get active users count
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        context['today_active_users'] = business.members.filter(
            last_login__gte=today_start
        ).count()

        # Handle business members
        user_members = []
        for member in business.members.all():
            profile, created = UserProfile.objects.get_or_create(user=member)
            user_members.append({
                'username': member.username,
                'email': member.email,
                'role': member.role,
                'id': member.id,
                'status': profile.logged_in_status,
                'is_active': profile.status
            })

        context['member_count'] = len(user_members)
        context['user_members'] = user_members[:4]
        context['has_more_members'] = len(user_members) > 4

    return render(request, 'index.html', context)




@require_POST
def clear_warning_modal(request):
    if 'show_warning_modal' in request.session:
        del request.session['show_warning_modal']
    return JsonResponse({'status': 'success'})


@csrf_exempt
def update_task_status(request, task_id):
    if request.method == "POST":
        try:
            task = None
            if request.user.is_authenticated:
                # For authenticated users, try all possible task types
                try:
                    if request.user.subscription_type.lower() in ['pro', 'business']:
                        # Check if user is either the creator or the assigned user
                        task = ProUserTask.objects.filter(
                            id=task_id
                        ).filter(
                            Q(user=request.user) | Q(assigned_to=request.user)
                        ).first()
                        print(f"DEBUG: Found ProUserTask with ID {task_id}, is_done before: {task.is_done}")
                    else:
                        task = LoggedUserTask.objects.get(id=task_id, user=request.user)
                except (ProUserTask.DoesNotExist, LoggedUserTask.DoesNotExist):
                    pass
            else:
                # For unauthenticated users
                client_ip = get_client_ip(request)
                try:
                    task = UnloggedUserTask.objects.get(id=task_id, ip_address=client_ip)
                except UnloggedUserTask.DoesNotExist:
                    pass

            if task is None:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Task not found or you do not have permission to update it'
                }, status=404)

            # Update the task status
            task.is_done = not task.is_done
            print(f"DEBUG: ProUserTask status changed to: {task.is_done}")
            
            # Update completed_at for ProUserTask
            if isinstance(task, ProUserTask):
                task.completed_at = timezone.now() if task.is_done else None
                
            # Save the task - this should trigger notifications
            task.save()
            print(f"DEBUG: Task saved once, ID: {task.id}")

            # Return the updated status
            return JsonResponse({
                'status': 'success',
                'is_done': task.is_done,
                'message': 'Task status updated successfully'
            })

        except Exception as e:
            print(f"Error updating task {task_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while updating the task'
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

def trial_middleware(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            # Call the utility function to check the user's subscription
            response = check_user_subscription(request.user)
            if response:
                return response

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
                return redirect('welcome:dashboard')
            else:
                # Redirect to payment page
                messages.info(request, "Redirecting to payment for Pro subscription.")
                return redirect('pay')  # Redirect to the pay view
    return render(request, 'subscribe_pro.html')

logger = logging.getLogger(__name__)

def pay_paymob(request):
    try:
        # Hardcoded subscription amount for Pro plan
        amount = 500  # Example: 500 EGP
        print(f"Amount: {amount}")  # Log to check the value

        # Step 1: Get Auth Token
        auth_response = requests.post(
            'https://accept.paymobsolutions.com/api/auth/tokens',
            json={'api_key': settings.PAYMOB_API_KEY}
        )
        auth_response.raise_for_status()
        auth_token = auth_response.json().get('token')
        print(f"Auth Response: {auth_response.status_code}, {auth_response.json()}")
        if not auth_token:
            raise ValueError('No auth token received.')

        # Generate a unique order ID
        unique_order_id = str(uuid.uuid4())

        # Step 2: Create Order
        order_response = requests.post(
            'https://accept.paymobsolutions.com/api/ecommerce/orders',
            json={
                'auth_token': auth_token,
                'delivery_needed': False,
                'amount_cents': int(amount * 100),
                'currency': 'EGP',
                'merchant_order_id': unique_order_id
            }
        )
        order_response.raise_for_status()
        order_id = order_response.json().get('id')
        if not order_id:
            raise ValueError('No order ID received.')
        print(f"Order Response: {order_response.status_code}, {order_response.json()}")

        # Step 3: Generate Payment Key
        billing_data = {
            'first_name': request.user.username,
            'last_name': request.user.username,
            'street': '123 Main St',  # Replace with actual data
            'building': '1',
            'floor': '1',
            'apartment': '1A',
            'city': 'Cairo',
            'state': 'Cairo',
            'country': 'EGY',  # ISO 3166-1 alpha-3 country code
            'postal_code': '3753450',  # Replace with actual data
            'email': request.user.email,
            'phone_number': '01145871860'
        }
        payment_key_response = requests.post(
            'https://accept.paymobsolutions.com/api/acceptance/payment_keys',
            json={
                'auth_token': auth_token,
                'amount_cents': int(amount * 100),
                'expiration': 3600,
                'order_id': order_id,
                'currency': 'EGP',
                'integration_id': settings.PAYMOB_INTEGRATION_ID,
                'billing_data': billing_data
            }
        )
        payment_key_response.raise_for_status()
        payment_key = payment_key_response.json().get('token')
        if not payment_key:
            raise ValueError('No payment key received.')

        # Step 4: Save Payment Info to SubscriptionOrder Model
        payment_url = f'https://accept.paymobsolutions.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}'
        subscription_order = SubscriptionOrder.objects.create(
            user=request.user,
            payment_status='Pending',
            payment_key=payment_key,
            payment_url=payment_url,
            amount_cents=int(amount * 100)
        )
        print(f"SubscriptionOrder created: {subscription_order.id}")

        # Step 5: Redirect to Paymob iframe
        return redirect(payment_url)

    except (requests.exceptions.RequestException, ValueError) as e:
        messages.error(request, f'An error occurred during payment processing: {e}')
        return redirect('welcome:dashboard')  # Redirect to a valid URL pattern name

def payment_result_paymob(request):
    # Log the entire payment data for debugging
    payment_data = request.POST
    print(f"Payment Data Received: {payment_data}")

    payment_key = payment_data.get('payment_token')
    payment_status = payment_data.get('success', False)

    try:
        # Validate payment key
        if not payment_key:
            messages.error(request, 'Invalid payment token received.')
            return redirect('dashboard')

        # Retrieve the SubscriptionOrder using the payment_key
        subscription_order = SubscriptionOrder.objects.filter(payment_key=payment_key).first()
        if not subscription_order:
            messages.error(request, 'Payment not found.')
            return redirect('dashboard')

        # Validate payment status
        if payment_status is None:
            messages.error(request, 'Invalid payment status received.')
            return redirect('dashboard')

        # Update payment status based on Paymob's response
        if payment_status == 'true':  # Adjust based on Paymob's actual response
            # Update user's subscription status
            user = request.user
            user.subscription_type = 'pro'
            user.role = 'team_leader'
            user.pro_subscription_date = now().date()
            user.save()

            # Update SubscriptionOrder status
            subscription_order.payment_status = 'Completed'
            subscription_order.save()

            messages.success(request, 'Payment successful! Your Pro subscription has been activated.')
        else:
            # Mark payment as failed
            subscription_order.payment_status = 'Failed'
            subscription_order.save()
            messages.error(request, 'Payment failed. Please try again.')
    except Exception as e:
        messages.error(request, f'An error occurred while updating payment status: {e}')

    return redirect('dashboard')




# Initialize Stripe API
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def pay(request):
    try:
        # Get the plan type from URL parameters
        plan_type = request.GET.get('plan', 'pro').lower()
        
        # Set amount and description based on plan type
        if plan_type == 'business':
            amount = 39900  # 399.00 EGP
            plan_name = 'Business'
            subscription_type = 'business'
        else:  # default to pro
            amount = 19900  # 199.00 EGP
            plan_name = 'Pro'
            subscription_type = 'pro'

        # Verify Stripe API key is set
        if not settings.STRIPE_SECRET_KEY:
            logger.error("Stripe secret key is not configured")
            messages.error(request, 'Payment system is not properly configured.')
            return redirect('welcome:dashboard')

        # Initialize Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Create Checkout Session with better error handling
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'egp',
                        'product_data': {
                            'name': plan_name,
                            'description': f'Monthly {plan_name}',
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(f'/payment-success/?plan={plan_type}'),
                cancel_url=request.build_absolute_uri('/payment-cancel/'),
                metadata={
                    'user_id': str(request.user.id),
                    'plan_type': plan_type
                },
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe session creation error: {str(e)}")
            messages.error(request, 'Unable to initialize payment. Please try again.')
            return redirect('welcome:dashboard')

        # Create SubscriptionOrder
        try:
            subscription_order = SubscriptionOrder.objects.create(
                user=request.user,
                payment_status='Pending',
                payment_intent_id=checkout_session.payment_intent,
                amount_cents=amount,
                subscription_type=subscription_type  # Store the subscription type
            )
            logger.info(f"SubscriptionOrder created: {subscription_order.id}")
        except Exception as e:
            logger.error(f"Error creating subscription order: {str(e)}")
            messages.error(request, 'Error creating subscription order.')
            return redirect('welcome:dashboard')

        # Redirect to Stripe Checkout
        logger.info(f"Redirecting to Stripe checkout: {checkout_session.url}")
        return redirect(checkout_session.url)

    except Exception as e:
        logger.error(f"Unexpected error in pay view: {str(e)}")
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect('welcome:dashboard')

def payment_success(request):
    try:
        plan_type = request.GET.get('plan', 'pro').lower()
        user = request.user
        subscription_order = SubscriptionOrder.objects.filter(
            user=user,
            payment_status='Pending'
        ).latest('created_at')

        # Set role and subscription type
        if plan_type == 'business':
            user.subscription_type = 'business'
            user.role = 'team_leader'
        else:  # default to pro
            user.subscription_type = 'pro'
            user.role = 'team_leader'

        # Set subscription dates
        current_date = timezone.now().date()
        user.pro_subscription_date = current_date
        user.subscription_end_date = current_date + timedelta(days=30)

        # Save all user changes
        user.save(update_fields=[
            'subscription_type', 
            'role', 
            'pro_subscription_date', 
            'subscription_end_date'
        ])
        # Verify after save
        updated_user = CustomUser.objects.get(id=user.id)
        print(f"After save - Role: {updated_user.role}, Subscription End Date: {updated_user.subscription_end_date}")

        # Update subscription order status
        subscription_order.payment_status = 'Completed'
        subscription_order.completed_at = timezone.now()
        subscription_order.save()

        # Create a success notification
        Notification.objects.create(
            user=user,
            notification_type='success',
            message=f'Your {plan_type.title()} subscription has been activated successfully!'
        )

        messages.success(request, f'Payment successful! Your {plan_type.title()} subscription has been activated.')
        
        return render(request, 'payment_success.html', {
            'subscription_type': user.subscription_type,
            'role': user.role,
            'subscription_date': user.pro_subscription_date,
            'plan_type': plan_type
        })

    except SubscriptionOrder.DoesNotExist:
        messages.error(request, 'No pending subscription order found.')
        return redirect('welcome:dashboard')
    except Exception as e:
        logger.error(f"Error in payment_success: {str(e)}")
        messages.error(request, 'An error occurred while processing your payment success.')
        return redirect('welcome:dashboard')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # Verify the webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']

        # Find the corresponding SubscriptionOrder
        subscription_order = SubscriptionOrder.objects.filter(payment_intent_id=payment_intent_id).first()
        if subscription_order:
            # Update the payment status to Completed
            subscription_order.payment_status = 'Completed'
            subscription_order.completed_at = timezone.now()  # Record the completion time
            subscription_order.save()

            # Update the user's subscription status based on the plan type
            user = subscription_order.user
            if subscription_order.subscription_type == 'business':
                user.subscription_type = 'business'
                user.role = 'product_owner'
            else:  # default to pro
                user.subscription_type = 'pro'
                user.role = 'team_leader'
            
            user.pro_subscription_date = timezone.now().date()
            user.save()

            # Create a success notification
            Notification.objects.create(
                user=user,
                notification_type='success',
                message=f'Your {subscription_order.subscription_type.title()} subscription has been activated successfully!'
            )

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']

        # Mark the payment as Failed
        subscription_order = SubscriptionOrder.objects.filter(payment_intent_id=payment_intent_id).first()
        if subscription_order:
            subscription_order.payment_status = 'Failed'
            subscription_order.save()

            # Create a failure notification
            Notification.objects.create(
                user=subscription_order.user,
                notification_type='error',
                message=f'Your {subscription_order.subscription_type.title()} subscription payment has failed.'
            )

    return HttpResponse(status=200)

def payment_result(request):
    # Log the entire payment data for debugging
    payment_data = request.POST
    logger.info(f"Payment Data Received: {payment_data}")

    payment_key = payment_data.get('payment_token')
    payment_status = payment_data.get('success', False)

    try:
        # Validate payment key
        if not payment_key:
            messages.error(request, 'Invalid payment token received.')
            return redirect('welcome:dashboard')  # Fixed namespace

        # Retrieve the SubscriptionOrder using the payment_key
        subscription_order = SubscriptionOrder.objects.filter(payment_key=payment_key).first()
        if not subscription_order:
            messages.error(request, 'Payment not found.')
            return redirect('welcome:dashboard')  # Fixed namespace

        # Validate payment status
        if payment_status is None:
            messages.error(request, 'Invalid payment status received.')
            return redirect('welcome:dashboard')  # Fixed namespace

        # Update payment status based on response
        if payment_status in ['true', 'True', '1']:
            try:
                # Update user's subscription status
                user = request.user
                user.subscription_type = 'pro'
                user.role = 'team_leader'
                user.pro_subscription_date = timezone.now().date()  # Use timezone.now()
                user.save()
                logger.info(f"Updated user {user.id} to pro subscription")

                # Update SubscriptionOrder status
                subscription_order.payment_status = 'Completed'
                subscription_order.completed_at = timezone.now()  # Add completion timestamp
                subscription_order.save()
                logger.info(f"Updated subscription order {subscription_order.id} to Completed")

                messages.success(request, 'Payment successful! Your Pro subscription has been activated.')
            except Exception as e:
                logger.error(f"Error updating user/subscription: {str(e)}")
                messages.error(request, 'Error updating subscription status.')
        else:
            # Mark payment as failed
            subscription_order.payment_status = 'Failed'
            subscription_order.save()
            logger.info(f"Marked subscription order {subscription_order.id} as Failed")
            messages.error(request, 'Payment failed. Please try again.')
    except Exception as e:
        logger.error(f"Payment result error: {str(e)}")
        messages.error(request, f'An error occurred while updating payment status: {e}')

    return redirect('welcome:dashboard')  # Fixed namespace

@login_required
def members_dashboard_view(request):
    from businesses.models import Business
    from projects.models import Project
    from .models import ProUserTask
    
    user = request.user
    user_profile = user.userprofile  # Accessing the related UserProfile instance
    
    user_businesses = Business.objects.filter(members=user)  # Assuming you have a ManyToMany relationship

    if user_businesses.exists():
        # Get the first business the user is a member of
        first_business = user_businesses.first()
        print(f'User profile status: {user_profile.status}')

        # Check if the user is activated (using UserProfile status)
        if user_profile.status == 'Activated':
            # Retrieve projects the user is a member of
            user_projects = Project.objects.filter(members=user, business=first_business)
            # Retrieve tasks assigned to the user in those projects
            user_tasks = ProUserTask.objects.filter(assigned_to=user, project__in=user_projects)
            
            # Get members of the first business
            members = first_business.members.select_related(
                'profile', 'userprofile'
            ).all()

            context = {
                'user_projects': user_projects,
                'user_tasks': user_tasks,
                'business_name': first_business.name,  # Pass the business name to the template
                'members': members,
                'user_profile': user_profile
            }
        else:
            # If the user is not activated, don't show projects and tasks
            members = first_business.members.select_related(
                'profile', 'userprofile'
            ).all()

            context = {
                'business_name': first_business.name,  # Pass the business name to the template
                'members': members
            }
        
        return render(request, 'members_dashboard.html', context)
    else:
        # Redirect to a different page if the user is not a member of any business
        return redirect('welcome:dashboard')  # Replace with your desired route



@login_required
def user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'user_detail.html', {'user': user})

import json
@business_required
def help(request):
    response = None  # Initialize response variable
    query = None  # Initialize query variable for display in the template
    
    if request.method == "POST":
        query = request.POST.get('query')
        if not query:
            return render(request, 'help.html', {'error': 'Query cannot be empty'})
        
        # Construct the URL with the query parameter
        base_url = "https://www.ibrahimfakhry.com/handle_query"
        params = {'query': query}
        
        try:
            # Make a GET request to the external URL
            external_response = requests.get(base_url, params=params, timeout=20)
            external_response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            
            # Parse the JSON response and extract the "query_response" key
            response_json = external_response.json()
            response = response_json.get('query_response', 'No response available')
            
        except requests.exceptions.RequestException as e:
            # Handle errors (e.g., network issues, invalid responses)
            response = f"An error occurred while fetching the query response: {e}"
        except json.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            response = "Invalid response format received from the server."
    
    return render(request, 'help.html', {'query': query, 'response': response})

# views.py
@business_required
def generate_terms(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            company_name = data.get('company_name')
            company_description = data.get('company_description')

            if not company_name or not company_description:
                return JsonResponse({"error": "Both company name and description are required."}, status=400)

            # Encode parameters for the API
            encoded_name = quote_plus(company_name)
            encoded_description = quote_plus(company_description)
            api_url = f"https://www.ibrahimfakhry.com/generate_terms_policies?company_name={encoded_name}&company_description={encoded_description}"

            try:
                response = requests.get(api_url)
                response.raise_for_status()

                # Check if the response is valid JSON
                try:
                    data = response.json()
                except ValueError:
                    return JsonResponse({"error": "Invalid JSON response from the API"}, status=500)

                terms_policies = data.get('terms_policies', "No terms generated.")
                return JsonResponse({"terms_policies": terms_policies})
            except requests.RequestException as e:
                return JsonResponse({"error": f"API request failed: {str(e)}"}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@business_required
def generate_agreement(request):
    from businesses.models import Business
    context = {}
    
    user = request.user
    user_businesses = Business.objects.filter(user=user)
    user_business = user_businesses.first() if user_businesses.exists() else None
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'legal_agreement_generator.html', context)
            
        company_name = user_business.name
        agreement_type = request.POST.get('agreement_type')
        parties_involved = request.POST.get('parties_involved')
        
        # Encode parameters
        encoded_name = quote_plus(company_name)
        encoded_type = quote_plus(agreement_type)
        encoded_parties = quote_plus(parties_involved)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_legal_agreement?company_name={encoded_name}&agreement_type={encoded_type}&parties_involved={encoded_parties}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['result'] = data.get('legal_agreement', '')
            context['company_name'] = company_name
    
    context['user_business'] = user_business
    return render(request, 'legal_agreement_generator.html', context)

@business_required
def generate_forecast(request):
    from businesses.models import Business
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'financial_forecast.html', context)
            
        company_name = user_business.name
        current_revenue = request.POST.get('current_revenue')
        growth_rate = request.POST.get('growth_rate')
        
        # Create encoded URL
        encoded_name = quote_plus(company_name)
        encoded_revenue = quote_plus(current_revenue)
        encoded_growth = quote_plus(growth_rate)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_financial_forecast?company_name={encoded_name}&current_revenue={encoded_revenue}&future_growth_rate={encoded_growth}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['forecast'] = data.get('financial_forecast', '')
            context['company_name'] = company_name
    
    context['user_business'] = user_business
    return render(request, 'financial_forecast.html', context)

@business_required
def generate_schedule(request):
    from businesses.models import Business
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'event_schedule.html', context)
            
        event_name = user_business.name
        event_date = request.POST.get('event_date')
        activities = request.POST.get('activities_list')
        
        # Format date
        try:
            formatted_date = datetime.strptime(event_date, '%Y-%m-%d').strftime('%B %d, %Y')
        except:
            context['error'] = "Invalid date format"
            return render(request, 'event_schedule.html', context)
        
        # Create encoded URL
        encoded_name = quote_plus(event_name)
        encoded_date = quote_plus(event_date)
        encoded_activities = quote_plus(activities)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_event_schedule?event_name={encoded_name}&event_date={encoded_date}&activities_list={encoded_activities}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['schedule'] = data.get('event_schedule', '')
            context['event_name'] = event_name
            context['formatted_date'] = formatted_date
    
    context['user_business'] = user_business
    return render(request, 'event_schedule.html', context)

@business_required
def generate_code(request):
    context = {}
    
    if request.method == 'POST':
        language = request.POST.get('language')
        task_description = request.POST.get('task_description')
        
        # Encode parameters
        encoded_lang = quote_plus(language)
        encoded_task = quote_plus(task_description)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_code_snippet?language={encoded_lang}&task_description={encoded_task}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['code_snippet'] = data.get('code_snippet', '')
    
    return render(request, 'code_generator.html', context)

@business_required
def generate_faq(request):
    from businesses.models import Business
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'faq_generator.html', context)
            
        company_name = user_business.name
        product_service = request.POST.get('product_or_service', '')
        common_questions = request.POST.get('common_questions', '')
        
        try:
            # Create encoded URL parameters
            encoded_name = quote_plus(company_name)
            encoded_product = quote_plus(product_service)
            encoded_questions = quote_plus(common_questions)
            
            api_url = f"https://www.ibrahimfakhry.com/generate_faq?company_name={encoded_name}&product_or_service={encoded_product}&common_questions={encoded_questions}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            context['faq'] = data.get('faq', '')
            context['company_name'] = company_name
            context['product_or_service'] = product_service
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'faq_generator.html', context)

@business_required
def generate_social_post(request):
    from businesses.models import Business
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'social_post_generator.html', context)
            
        platform = request.POST.get('platform')
        target_audience = request.POST.get('target_audience')
        campaign_goal = request.POST.get('campaign_goal')
        
        try:
            # Encode parameters
            encoded_platform = quote_plus(platform)
            encoded_audience = quote_plus(target_audience)
            encoded_goal = quote_plus(campaign_goal)
            
            api_url = f"https://www.ibrahimfakhry.com/generate_social_media_post?platform={encoded_platform}&target_audience={encoded_audience}&campaign_goal={encoded_goal}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            context['social_post'] = data.get('social_media_post', '')
            context['platform'] = platform
            context['target_audience'] = target_audience
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'social_post_generator.html', context)

@business_required
def generate_email_campaign(request):
    from businesses.models import Business
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'email_campaign_generator.html', context)
            
        company_name = user_business.name
        campaign_goals = request.POST.get('campaign_goals')
        target_audience = request.POST.get('target_audience')
        
        try:
            # Encode parameters
            encoded_name = quote_plus(company_name)
            encoded_goals = quote_plus(campaign_goals)
            encoded_audience = quote_plus(target_audience)
            
            api_url = f"https://www.ibrahimfakhry.com/generate_email_campaign?company_name={encoded_name}&campaign_goals={encoded_goals}&target_audience={encoded_audience}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            context['email_campaign'] = data.get('email_campaign', '')
            context['company_name'] = company_name
            context['campaign_goals'] = campaign_goals
            context['target_audience'] = target_audience
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'email_campaign_generator.html', context)

@business_required
def generate_blog_ideas(request):
    from businesses.models import Business
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        topic = request.POST.get('topic')
        target_audience = request.POST.get('target_audience')
        
        try:
            # Encode parameters
            encoded_topic = quote_plus(topic)
            encoded_audience = quote_plus(target_audience)
            
            api_url = f"https://www.ibrahimfakhry.com/generate_blog_ideas?topic={encoded_topic}&target_audience={encoded_audience}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            context['blog_ideas'] = data.get('blog_ideas', '')
            context['topic'] = topic
            context['target_audience'] = target_audience
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    return render(request, 'blog_ideas_generator.html', context)

@business_required
def generate_role_steps(request):
    context = {}
    
    if request.method == 'POST':
        user_name = request.POST.get('user_name')
        user_role = request.POST.get('user_role')
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')
        
        # Encode parameters
        encoded_user_name = quote_plus(user_name)
        encoded_user_role = quote_plus(user_role)
        encoded_project_name = quote_plus(project_name)
        encoded_project_description = quote_plus(project_description)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_role_steps?user_name={encoded_user_name}&user_role={encoded_user_role}&project_name={encoded_project_name}&project_description={encoded_project_description}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['role_steps'] = data.get('role_steps', '')
            context['user_name'] = user_name
            context['user_role'] = user_role
            context['project_name'] = project_name
            context['project_description'] = project_description
    
    return render(request, 'role_steps_generator.html', context)

@login_required
@business_required
def generate_onboarding_steps(request):
    from businesses.models import Business
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'onboarding_steps_generator.html', context)
            
        company_name = user_business.name
        platform_type = request.POST.get('platform_type')
        user_role = request.POST.get('user_role')
        
        # Encode parameters
        encoded_company_name = quote_plus(company_name)
        encoded_platform_type = quote_plus(platform_type)
        encoded_user_role = quote_plus(user_role)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_onboarding_steps?company_name={encoded_company_name}&platform_type={encoded_platform_type}&user_role={encoded_user_role}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['onboarding_steps'] = data.get('onboarding_steps', '')
            context['company_name'] = company_name
            context['platform_type'] = platform_type
            context['user_role'] = user_role
    
    context['user_business'] = user_business
    return render(request, 'onboarding_steps_generator.html', context)

@business_required
def generate_marketing_copy(request):
    context = {}
    
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        target_audience = request.POST.get('target_audience')
        ad_goals = request.POST.get('ad_goals')
        
        # Encode parameters
        encoded_product_name = quote_plus(product_name)
        encoded_target_audience = quote_plus(target_audience)
        encoded_ad_goals = quote_plus(ad_goals)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_marketing_copy?product_name={encoded_product_name}&target_audience={encoded_target_audience}&ad_goals={encoded_ad_goals}"
        
        response = requests.get(api_url)
        if response.status_code == 200:  # Fix the unmatched parenthesis
            data = response.json()
            context['marketing_copy'] = data.get('marketing_copy', '')
    
    return render(request, 'marketing_copy_generator.html', context)

@business_required
def generate_product_description(request):
    context = {}
    
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        product_category = request.POST.get('product_category')
        product_features = request.POST.get('product_features')
        
        # Encode parameters
        encoded_product_name = quote_plus(product_name)
        encoded_product_category = quote_plus(product_category)
        encoded_product_features = quote_plus(product_features)
        
        api_url = f"https://www.ibrahimfakhry.com/generate_product_description?product_name={encoded_product_name}&product_category={encoded_product_category}&product_features={encoded_product_features}"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            context['product_description'] = data.get('product_description', '')
    
    return render(request, 'product_description_generator.html', context)

@login_required
@business_required
def generate_content_calendar(request):
    from datetime import datetime
    import json
    import re
    from urllib.parse import quote_plus
    from django.http import JsonResponse
    from django.db import IntegrityError
    from businesses.models import Business
    from .models import CalendarEvent

    try:
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

        # Parse request data
        try:
            data = json.loads(request.body)
            content_type = data.get('content_type', '').strip()
            start_date = data.get('start_date', '').strip()
            end_date = data.get('end_date', '').strip()
            
            print(f"Received data - Content Type: {content_type}, Start: {start_date}, End: {end_date}")
            
            if not all([content_type, start_date, end_date]):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        # Get user business
        try:
            user_business = Business.objects.get(user=request.user)
        except Business.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'No business found for this user'}, status=400)

        # Make API request
        try:
            api_url = (
                f"https://www.ibrahimfakhry.com/generate_content_calendar?"
                f"company_name={quote_plus(user_business.name)}&"
                f"content_type={quote_plus(content_type)}&"
                f"start_date={quote_plus(start_date)}&"
                f"end_date={quote_plus(end_date)}"
            )
            
            print(f"Making API request to: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            api_data = response.json()
            content_calendar = api_data.get('content_calendar', '')
            
            print(f"API Response received. Length: {len(content_calendar)}")
            
            if not content_calendar:
                return JsonResponse({'status': 'error', 'message': 'No content received from API'}, status=400)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'API error: {str(e)}'}, status=500)

        # Process content calendar
        created_count = 0
        max_title_length = CalendarEvent._meta.get_field('title').max_length

        # Extract events using the bullet point format
        event_pattern = r'\*\s*\*\*((?:Morning|Afternoon|Evening)\s*\((\d{1,2}:\d{2}\s*[AP]M)\)):\*\*\s*([^*\n]+)'
        
        # Find all events
        events = re.finditer(event_pattern, content_calendar)
        
        # Extract the current date as we process events
        current_date = None
        date_pattern = r'\*\*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,\s*February\s*(\d{1,2})(?:st|nd|rd|th)'
        
        for line in content_calendar.split('\n'):
            # Check for new date
            date_match = re.search(date_pattern, line)
            if date_match:
                day = int(date_match.group(1))
                current_date = f"2025-02-{day:02d}"
                print(f"Processing date: {current_date}")
                continue
                
            # Try to find event in this line
            event_match = re.search(event_pattern, line)
            if current_date and event_match:
                try:
                    time_str = event_match.group(2).strip()
                    content = event_match.group(3).strip()
                    
                    # Parse the datetime
                    time_str = time_str.replace('AM', ' AM').replace('PM', ' PM').strip()
                    full_datetime = datetime.strptime(f"{current_date} {time_str}", "%Y-%m-%d %I:%M %p")
                    
                    # Split content into title and description if possible
                    parts = content.split(':', 1)
                    if len(parts) > 1:
                        title = parts[0].strip()
                        description = parts[1].strip()
                    else:
                        title = content
                        description = content

                    # Create calendar event
                    event = CalendarEvent.objects.create(
                        user=request.user,
                        title=title[:max_title_length],
                        start_date=full_datetime.date(),
                        end_date=full_datetime.date(),
                        description=description
                    )
                    created_count += 1
                    print(f"Created event: {title[:50]}")
                    
                except Exception as e:
                    print(f"Error processing event: {str(e)}")
                    continue

        if created_count == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'No valid events could be created from the API response.'
            }, status=400)

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully created {created_count} calendar events',
            'created_count': created_count
        })

    except Exception as e:
        print(f"Critical error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

@login_required
@business_required
def ai_tools(request):
    return render(request, 'ai_tools.html')


def plans(request):
    context = {
        'user_plan': request.user.subscription_type.lower() if request.user.is_authenticated else 'basic'
    }
    return render(request, 'plans.html', context)

@login_required
def calendar(request):
    return render(request, "calender.html")

@login_required
def get_events(request):
    """Fetch events for the logged-in user."""
    events = CalendarEvent.objects.filter(user=request.user)
    event_list = [
        {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.strftime('%Y-%m-%d'),
            'end': (event.end_date + timedelta(days=1)).strftime('%Y-%m-%d')  # Add one day to make it inclusive
        }
        for event in events
    ]
    return JsonResponse(event_list, safe=False)

@csrf_exempt
@login_required
def add_event(request):
    """Add a new event for the logged-in user."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            start_date = data.get('start_date')
            end_date = data.get('end_date', start_date)  # Default to start_date if empty

            if not title or not start_date:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

            # Parse and validate dates
            start_date = parse_date(start_date)
            end_date = parse_date(end_date) if end_date else start_date

            if not start_date or (end_date and end_date < start_date):
                return JsonResponse({'status': 'error', 'message': 'Invalid date range'}, status=400)

            # Save the event
            event = CalendarEvent.objects.create(
                user=request.user,
                title=title,
                start_date=start_date,
                end_date=end_date
            )
            return JsonResponse({'status': 'success', 'event_id': event.id})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@csrf_exempt
@login_required
def update_event(request):
    """Update an existing event."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event_id = data.get('id')
            if not event_id:
                return JsonResponse({'status': 'error', 'message': 'Missing event ID'}, status=400)
            
            event = CalendarEvent.objects.get(id=event_id, user=request.user)
            title = data.get('title')
            start_date = data.get('start_date')
            end_date = data.get('end_date', start_date)

            if not title or not start_date:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

            # Parse and validate dates
            start_date = parse_date(start_date)
            end_date = parse_date(end_date) if end_date else start_date

            if not start_date or (end_date and end_date < start_date):
                return JsonResponse({'status': 'error', 'message': 'Invalid date range'}, status=400)

            # Update the event
            event.title = title
            event.start_date = start_date
            event.end_date = end_date
            event.save()
            return JsonResponse({'status': 'success', 'event_id': event.id})
        except CalendarEvent.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def delete_event(request):
    """Delete an event."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event_id = data.get('id')
            if not event_id:
                return JsonResponse({'status': 'error', 'message': 'Missing event ID'}, status=400)
                
            event = CalendarEvent.objects.get(id=event_id, user=request.user)
            event.delete()
            return JsonResponse({'status': 'success'})
        except CalendarEvent.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@csrf_exempt
@login_required
def delete_event(request, event_id):
    """Delete an event."""
    if request.method == 'POST':
        try:
            event = CalendarEvent.objects.get(id=event_id, user=request.user)
            event.delete()
            return JsonResponse({'status': 'success'})
        except CalendarEvent.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)



@business_required
def ai_tools(request):
    # Define the AI tools with their descriptions, valid icons, and URLs
    app_name = 'welcome'  # Replace 'welcome' with your actual app name if different
    tools = [
        {'name': 'Generate Terms', 'icon': 'file-contract', 'url': f'{app_name}:generate_terms'},
        {'name': 'Generate Agreement', 'icon': 'file-signature', 'url': f'{app_name}:generate_agreement'},
        {'name': 'Generate Forecast', 'icon': 'chart-line', 'url': f'{app_name}:generate_forecast'},
        {'name': 'Generate Schedule', 'icon': 'calendar-alt', 'url': f'{app_name}:generate_schedule'},
        {'name': 'Generate Code', 'icon': 'code', 'url': f'{app_name}:generate_code'},
        {'name': 'Generate FAQ', 'icon': 'question-circle', 'url': f'{app_name}:generate_faq'},
        {'name': 'Generate Social Post', 'icon': 'share-square', 'url': f'{app_name}:generate_social_post'},
        {'name': 'Generate Email Campaign', 'icon': 'envelope', 'url': f'{app_name}:generate_email_campaign'},
        {'name': 'Generate Blog Ideas', 'icon': 'pen-nib', 'url': f'{app_name}:generate_blog_ideas'},
        {'name': 'Generate Role Steps', 'icon': 'tasks', 'url': f'{app_name}:generate_role_steps'},
        {'name': 'Generate Onboarding Steps', 'icon': 'user-check', 'url': f'{app_name}:generate_onboarding_steps'},
        {'name': 'Generate Marketing Copy', 'icon': 'pen-fancy', 'url': f'{app_name}:generate_marketing_copy'},
        {'name': 'Generate Product Description', 'icon': 'box-open', 'url': f'{app_name}:generate_product_description'},
        {'name': 'Generate Content Calendar', 'icon': 'calendar-day', 'url': f'{app_name}:generate_content_calendar'},
        {'name': 'Help', 'icon': 'question-circle', 'url': f'{app_name}:help'},  # Add Help Tool
    ]

    # Render the template with the tools data
    return render(request, 'ai_tools.html', {'tools': tools})


def notification_list(request):
    """View to display all notifications for the current user."""
    if request.user.is_authenticated:
        # Get all notifications for the user, both read and unread
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        # Count unread notifications
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return render(request, 'notifications.html', {
            'notifications': notifications,
            'unread_count': unread_count
        })
    return redirect('users:login')



from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q  # Import Q for complex queries

@login_required
def search_suggestions(request):
    from welcome.models import CustomUser, ProUserTask
    from businesses.models import Business
    from projects.models import Project

    query = request.GET.get('query', '').strip()
    user = request.user
    suggestions = []

    print(f"Search query received: {query}")  # Debug log
    if query:
        try:
            # Users
            user_results = CustomUser.objects.filter(username__icontains=query)[:5]
            print(f"Found {len(user_results)} user results")  # Debug log
            for user_item in user_results:
                suggestions.append({
                    'name': user_item.username,
                    'url': f'/profile/{user_item.id}'
                })

            # Projects
            project_results = Project.objects.filter(name__icontains=query)[:5]
            print(f"Found {len(project_results)} project results")  # Debug log
            for project_item in project_results:
                suggestions.append({
                    'name': project_item.name,
                    'url': f'/project/{project_item.id}'
                })

            # Businesses
            business_results = Business.objects.filter(name__icontains=query)[:5]
            print(f"Found {len(business_results)} business results")  # Debug log
            for business_item in business_results:
                suggestions.append({
                    'name': business_item.name,
                    'url': f'/business/{business_item.id}'  # Updated URL
                })

            # Tasks
            task_results = ProUserTask.objects.filter(task_name__icontains=query)[:5]
            print(f"Found {len(task_results)} task results")  # Debug log
            for task_item in task_results:
                suggestions.append({
                    'name': task_item.task_name,
                    'url': f'/task/{task_item.id}'
                })
        except Exception as e:
            print(f"Error in search_suggestions: {str(e)}")  # Debug log

    print(f"Returning suggestions: {suggestions}")  # Debug log
    return JsonResponse({'suggestions': suggestions})

def faq_view(request):
    from .models import FAQ
    faqs = FAQ.objects.all().order_by('created_at')
    return render(request, 'faq.html', {'faqs': faqs})


@login_required
@require_POST
def update_ui_settings(request):
    try:
        data = json.loads(request.body)
        setting = data.get('setting')
        value = data.get('value')
        
        if not setting:
            return JsonResponse({'success': False, 'error': 'No setting specified'})
            
        ui_settings = request.user.ui_settings
        
        if setting == 'sidebar_color':
            if value in dict(UISettings._meta.get_field('sidebar_color').choices):
                ui_settings.sidebar_color = value
                
        elif setting == 'sidenav_type':
            if value in dict(UISettings._meta.get_field('sidenav_type').choices):
                ui_settings.sidenav_type = value
                
        elif setting == 'navbar_fixed':
            ui_settings.navbar_fixed = bool(value)
            
        elif setting == 'dark_mode':
            ui_settings.dark_mode = bool(value)
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid setting'})
            
        ui_settings.save()
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def mark_notification_read(request):
    """Marks a notification as read."""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return JsonResponse({'success': False, 'error': 'No notification ID specified'})
        
        # Check if we're marking a single notification or all as read
        if notification_id == 'all':
            # Mark all user's notifications as read
            Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).update(is_read=True)
            return JsonResponse({'success': True, 'message': 'All notifications marked as read'})
        else:
            # Mark single notification as read
            try:
                notification = Notification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
                return JsonResponse({'success': True})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})