from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import MessageForm
from .models import Messages  # Correct import for Messages model
from welcome.models import CustomUser
from django.db.models import Q
from django.http import JsonResponse

# Create your views here.
@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            recipients_emails = [email.strip() for email in form.cleaned_data['recipients'].split(',') if email.strip()]
            recipients = CustomUser.objects.filter(email__in=recipients_emails)
            if recipients.count() != len(recipients_emails):
                form.add_error('recipients', 'Some of the entered emails do not correspond to existing users.')
                return render(request, 'send_message.html', {'form': form})
            message.save()
            message.recipients.set(recipients)
            return redirect('view_messages')
    else:
        form = MessageForm()
    return render(request, 'send_message.html', {'form': form})


def autocomplete_users(request):
    query = request.GET.get('term', '')
    exact_matches = CustomUser.objects.filter(email__startswith=query).values_list('email', flat=True)
    partial_matches = CustomUser.objects.filter(email__icontains=query).exclude(email__startswith=query).values_list('email', flat=True)
    users = list(exact_matches) + list(partial_matches)
    return JsonResponse(users, safe=False)

@login_required
def view_messages(request):
    user = request.user
    received_messages = Messages.objects.filter(recipients=user).order_by('-created_at')
    sent_messages = Messages.objects.filter(sender=user).order_by('-created_at')
    return render(request, 'view_messages.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages
    })

@login_required
def search_users(request):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        if query:
            users = CustomUser.objects.filter(Q(email__icontains=query) | Q(username__icontains(query)))
            results = [{'id': user.id, 'email': user.email} for user in users]
            return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)