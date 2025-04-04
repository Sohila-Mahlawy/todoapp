from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import MessageForm
from .models import Messages  # Correct import for Messages model
from welcome.models import CustomUser,Notification
from businesses.models import Business
from django.db.models import Q
from django.http import JsonResponse
import requests
from welcome.utils import business_required

@business_required
@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            # Save the message instance without committing to the database
            message = form.save(commit=False)
            message.sender = request.user  # Set the sender to the current user
            message.save()  # Save the message to the database

            # Add recipients to the message
            recipients = form.cleaned_data['recipients']
            message.recipients.set(recipients)

            # Create a notification for each recipient
            for recipient in recipients:
                Notification.objects.create(
                    user=recipient,
                    notification_type='message',
                    message=f"from {request.user.username}: {message.subject}",
                )

            # Redirect to the view_messages page after successful submission
            return redirect('messagn:view_messages')
    else:
        form = MessageForm()

    return render(request, 'send_message.html', {'form': form})

@business_required
def autocomplete_users(request):
    query = request.GET.get('term', '')
    exact_matches = CustomUser.objects.filter(email__startswith=query).values_list('email', flat=True)
    partial_matches = CustomUser.objects.filter(email__icontains=query).exclude(email__startswith=query).values_list('email', flat=True)
    users = list(exact_matches) + list(partial_matches)
    return JsonResponse(users, safe=False)

@login_required
@business_required
def view_messages(request):
    user = request.user
    received_messages = Messages.objects.filter(recipients=user).order_by('-created_at')
    sent_messages = Messages.objects.filter(sender=user).order_by('-created_at')
    return render(request, 'view_messages.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages
    })

@login_required
@business_required
def search_users(request):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        if query:
            users = CustomUser.objects.filter(Q(email__icontains=query) | Q(username__icontains(query)))
            results = [{'id': user.id, 'email': user.email} for user in users]
            return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

@business_required
def generate_email(request):
    receiver_name = request.GET.get('receiver_name')
    sender_name = request.user.username
    topic = request.GET.get('topic')

    url = f'https://www.ibrahimfakhry.com/generate_email?receiver_name={receiver_name}&sender_name={sender_name}&topic={topic}'

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Extract email text from JSON
        email_content = response.json().get("email", "")

        # Remove the subject and only keep the body
        if "Subject:" in email_content:
            email_content = email_content.split("\n", 1)[-1].strip()

        return JsonResponse({'email_content': email_content})
    except requests.exceptions.RequestException:
        return JsonResponse({'error': 'Error occurred while generating the email.'}, status=500)