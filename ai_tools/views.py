from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from urllib.parse import quote_plus
import json
import requests
from datetime import datetime, timedelta
from django.contrib import messages
from django.db import transaction
from businesses.models import Business
from .models import FAQ, LegalDocument, ContentCalendarEvent, SocialMediaPost, EmailCampaign, CodeSnippet
from welcome.utils import business_required



@login_required
@business_required
def ai_tools_dashboard(request):
    """Main dashboard for AI tools"""
    # Define the AI tools with their descriptions, icons, and URLs
    tools = [
        {'name': 'Generate Terms', 'icon': 'file-contract', 'url': 'ai_tools:generate_terms'},
        {'name': 'Generate Agreement', 'icon': 'file-signature', 'url': 'ai_tools:generate_agreement'},
        {'name': 'Generate Forecast', 'icon': 'chart-line', 'url': 'ai_tools:generate_forecast'},
        {'name': 'Generate Schedule', 'icon': 'calendar-alt', 'url': 'ai_tools:generate_schedule'},
        {'name': 'Generate Code', 'icon': 'code', 'url': 'ai_tools:generate_code'},
        {'name': 'Generate FAQ', 'icon': 'question-circle', 'url': 'ai_tools:generate_faq'},
        {'name': 'Generate Social Post', 'icon': 'share-square', 'url': 'ai_tools:generate_social_post'},
        {'name': 'Generate Email Campaign', 'icon': 'envelope', 'url': 'ai_tools:generate_email_campaign'},
        {'name': 'Generate Blog Ideas', 'icon': 'pen-nib', 'url': 'ai_tools:generate_blog_ideas'},
        {'name': 'Generate Role Steps', 'icon': 'tasks', 'url': 'ai_tools:generate_role_steps'},
        {'name': 'Generate Onboarding Steps', 'icon': 'user-check', 'url': 'ai_tools:generate_onboarding_steps'},
        {'name': 'Generate Marketing Copy', 'icon': 'pen-fancy', 'url': 'ai_tools:generate_marketing_copy'},
        {'name': 'Generate Product Description', 'icon': 'box-open', 'url': 'ai_tools:generate_product_description'},
        {'name': 'Generate Content Calendar', 'icon': 'calendar-day', 'url': 'ai_tools:generate_content_calendar'},
        {'name': 'Help', 'icon': 'question-circle', 'url': 'ai_tools:help'},
    ]

    return render(request, 'ai_tools/ai_tools.html', {'tools': tools})

@business_required
def help(request):
    response = None
    query = None
    
    if request.method == "POST":
        query = request.POST.get('query')
        if not query:
            return render(request, 'ai_tools/help.html', {'error': 'Query cannot be empty'})
        
        # Construct the URL with the query parameter
        base_url = "https://www.ibrahimfakhry.com/handle_query"
        params = {'query': query}
        
        try:
            # Make a GET request to the external URL
            external_response = requests.get(base_url, params=params, timeout=20)
            external_response.raise_for_status()
            
            # Parse the JSON response and extract the "query_response" key
            response_json = external_response.json()
            response = response_json.get('query_response', 'No response available')
            
        except requests.exceptions.RequestException as e:
            response = f"An error occurred while fetching the query response: {e}"
        except json.JSONDecodeError:
            response = "Invalid response format received from the server."
    
    return render(request, 'ai_tools/help.html', {'query': query, 'response': response})

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
                
                # Save to database
                if request.user.is_authenticated:
                    LegalDocument.objects.create(
                        user=request.user,
                        company_name=company_name,
                        document_type='terms',
                        content=terms_policies
                    )
                
                return JsonResponse({"terms_policies": terms_policies})
            except requests.RequestException as e:
                return JsonResponse({"error": f"API request failed: {str(e)}"}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@business_required
def generate_agreement(request):
    context = {}
    
    user = request.user
    user_businesses = Business.objects.filter(user=user)
    user_business = user_businesses.first() if user_businesses.exists() else None
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'ai_tools/legal_agreement_generator.html', context)
            
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
            result = data.get('legal_agreement', '')
            context['result'] = result
            context['company_name'] = company_name
            
            # Save to database
            LegalDocument.objects.create(
                user=request.user,
                company_name=company_name,
                document_type='agreement',
                content=result
            )
    
    context['user_business'] = user_business
    return render(request, 'ai_tools/legal_agreement_generator.html', context)

@business_required
def generate_forecast(request):
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'ai_tools/financial_forecast.html', context)
            
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
    return render(request, 'ai_tools/financial_forecast.html', context)

@business_required
def generate_schedule(request):
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'ai_tools/event_schedule.html', context)
            
        event_name = user_business.name
        event_date = request.POST.get('event_date')
        activities = request.POST.get('activities_list')
        
        # Format date
        try:
            formatted_date = datetime.strptime(event_date, '%Y-%m-%d').strftime('%B %d, %Y')
        except:
            context['error'] = "Invalid date format"
            return render(request, 'ai_tools/event_schedule.html', context)
        
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
    return render(request, 'ai_tools/event_schedule.html', context)

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
            code_snippet = data.get('code_snippet', '')
            context['code_snippet'] = code_snippet
            
            # Save to database
            CodeSnippet.objects.create(
                user=request.user,
                language=language,
                task_description=task_description,
                code=code_snippet
            )
    
    return render(request, 'ai_tools/code_generator.html', context)

@business_required
def generate_faq(request):
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'ai_tools/faq_generator.html', context)
            
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
            faq_content = data.get('faq', '')
            context['faq'] = faq_content
            context['company_name'] = company_name
            context['product_or_service'] = product_service
            
            # Save to database
            FAQ.objects.create(
                user=request.user,
                company_name=company_name,
                product_or_service=product_service,
                common_questions=common_questions,
                generated_faq=faq_content
            )
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'ai_tools/faq_generator.html', context)

@business_required
def generate_social_post(request):
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'ai_tools/social_post_generator.html', context)
            
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
            post_content = data.get('social_media_post', '')
            context['social_post'] = post_content
            context['platform'] = platform
            context['target_audience'] = target_audience
            
            # Save to database
            SocialMediaPost.objects.create(
                user=request.user,
                platform=platform,
                target_audience=target_audience,
                campaign_goal=campaign_goal,
                content=post_content
            )
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'ai_tools/social_post_generator.html', context)

@business_required
def generate_email_campaign(request):
    context = {}
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            messages.error(request, "No business associated with this account")
            return render(request, 'ai_tools/email_campaign_generator.html', context)
            
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
            campaign_content = data.get('email_campaign', '')
            context['email_campaign'] = campaign_content
            context['company_name'] = company_name
            context['campaign_goals'] = campaign_goals
            context['target_audience'] = target_audience
            
            # Save to database
            EmailCampaign.objects.create(
                user=request.user,
                company_name=company_name,
                campaign_goals=campaign_goals,
                target_audience=target_audience,
                content=campaign_content
            )
            
        except requests.exceptions.RequestException as e:
            messages.error(request, f"API Error: {str(e)}")
        except ValueError:
            messages.error(request, "Invalid response from API")
    
    context['user_business'] = user_business
    return render(request, 'ai_tools/email_campaign_generator.html', context)

@business_required
def generate_blog_ideas(request):
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
    
    return render(request, 'ai_tools/blog_ideas_generator.html', context)

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
    
    return render(request, 'ai_tools/role_steps_generator.html', context)

@login_required
@business_required
def generate_onboarding_steps(request):
    context = {}
    
    user = request.user
    user_business = Business.objects.filter(user=user).first()
    
    if request.method == 'POST':
        if not user_business:
            context['error'] = "No business associated with this account"
            return render(request, 'ai_tools/onboarding_steps_generator.html', context)
            
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
    return render(request, 'ai_tools/onboarding_steps_generator.html', context)

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
        if response.status_code == 200:
            data = response.json()
            context['marketing_copy'] = data.get('marketing_copy', '')
    
    return render(request, 'ai_tools/marketing_copy_generator.html', context)

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
    
    return render(request, 'ai_tools/product_description_generator.html', context)

@login_required
@business_required
def generate_content_calendar(request):
    import re
    from urllib.parse import quote_plus
    from django.http import JsonResponse
    from django.db import IntegrityError
    from businesses.models import Business

    try:
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

        # Parse request data
        try:
            data = json.loads(request.body)
            content_type = data.get('content_type', '').strip()
            start_date = data.get('start_date', '').strip()
            end_date = data.get('end_date', '').strip()
            
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
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            api_data = response.json()
            content_calendar = api_data.get('content_calendar', '')
            
            if not content_calendar:
                return JsonResponse({'status': 'error', 'message': 'No content received from API'}, status=400)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'API error: {str(e)}'}, status=500)

        # Process content calendar
        created_count = 0
        max_title_length = 255  # ContentCalendarEvent title max length

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
                    event = ContentCalendarEvent.objects.create(
                        user=request.user,
                        title=title[:max_title_length],
                        description=description,
                        start_date=full_datetime.date(),
                        end_date=full_datetime.date(),
                        content_type=content_type
                    )
                    created_count += 1
                    
                except Exception as e:
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
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)
