from django.shortcuts import render,redirect,get_object_or_404
from .models import Business,CallCenter,Complaint,ProjectResult,FinanceRecord
from welcome.models import CustomUser,UserProfile,MemberProfile
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings
from django.contrib import messages
from .forms import CallCenterForm
import re
from datetime import datetime, timedelta
import pandas as pd
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from openai import OpenAI
from django.http import JsonResponse
from django.core.cache import cache
import pandas as pd
import string
import random
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import os
from pathlib import Path
from django.http import HttpResponseForbidden
from django.core.files.storage import FileSystemStorage
from urllib.parse import quote_plus
import requests
from welcome.utils import business_required,has_business_required
from django.views.decorators.csrf import csrf_exempt
import jwt
import time
import base64
from django.core.files.base import ContentFile


@business_required
def add_business(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        description = request.POST.get('description')
        icon = request.FILES['icon']
        employee_file = request.FILES['employee_file']
        category = request.POST.get('category')

        # Save the icon and employee file
        icon_fs = FileSystemStorage(location='media/uploaded_icons')
        icon_name = icon_fs.save(icon.name, icon)

        excel_fs = FileSystemStorage(location='media/uploaded_excel')
        employee_file_name = excel_fs.save(employee_file.name, employee_file)

        # Generate Terms and Conditions
        encoded_name = quote_plus(company_name)
        encoded_description = quote_plus(description)
        api_url = f"https://www.ibrahimfakhry.com/generate_terms_policies?company_name={encoded_name}&company_description={encoded_description}"

        response = requests.get(api_url)
        generated_terms = response.json().get('terms_policies', '') if response.status_code == 200 else ''

        # Create a new Business instance
        business = Business.objects.create(
            name=company_name,
            icon=f'uploaded_icons/{icon_name}',
            employee_file=f'uploaded_excel/{employee_file_name}',
            user=request.user,
            category=category,
            terms=generated_terms  # Save generated terms in the database
        )

        # Process the Excel file and get the parsed data
        employee_file_path = excel_fs.path(employee_file_name)
        parsed_data = process_excel(request, employee_file_path)

        # Render the review template with all necessary context
        return render(request, 'businesses/review_business_data.html', {
            'company_name': company_name,
            'icon_name': icon_name,
            'data': parsed_data,
            'business_id': business.id,
            'terms': generated_terms  # Pass the terms to the review page
        })

    return render(request, 'businesses/add_business.html')


@has_business_required
def business_members_view(request):
    # Get the business associated with the current user
    user_business = get_object_or_404(Business, user=request.user)
    
    # Get the business members with their related details
    members = user_business.members.select_related(
        'profile', 'userprofile'
    ).all()
    
    context = {
        'business': user_business,
        'members': members
    }
    return render(request, 'businesses/business_members.html', context)

@business_required
@has_business_required
def process_business_data(request):

    if request.method == 'POST':
        try:
            business_id = request.POST.get('business_id')
            business = get_object_or_404(Business, id=business_id)
            
            # Get the absolute file path
            employee_file_path = os.path.join(settings.MEDIA_ROOT, str(business.employee_file))
            
            print(f"Processing file: {employee_file_path}")  # Debug print
            
            if not os.path.exists(employee_file_path):
                raise FileNotFoundError(f"Excel file not found at {employee_file_path}")

            # Create the accounts
            members_data = create_accounts_from_excel(employee_file_path, business)
            
            if members_data:
                messages.success(request, f"Successfully created {len(members_data)} user accounts!")
            else:
                messages.warning(request, "No new user accounts were created.")

            return redirect('welcome:dashboard')

        except Exception as e:
            print(f"Error in process_business_data: {str(e)}")  # Debug print
            messages.error(request, f"Error processing business data: {str(e)}")
            return redirect('businesses:add_business')

    return redirect('businesses:add_business')


@has_business_required
def upload_call_center(request):
    if request.method == 'POST':
        form = CallCenterForm(request.POST, request.FILES)
        if form.is_valid():
            # Automatically set the business to the user's first business
            business = get_object_or_404(Business, user=request.user)
            call_center = form.save(commit=False)  # Do not save yet
            call_center.business = business  # Set the business
            call_center.save()  # Now save the instance
            return redirect('dashboard_view')  # Replace with your success URL
    else:
        form = CallCenterForm()
    return render(request, 'businesses/upload_call_center.html', {'form': form})


@has_business_required
def upload_finance(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)

        # Retrieve the Business instance associated with the logged-in user
        try:
            business = Business.objects.get(user=request.user)
        except Business.DoesNotExist:
            return render(request, 'businesses/upload_call_center.html', {'error': 'No business associated with this user.'})

        # Assuming the Excel file has columns: 'Sold Piece', 'Sold To', 'Date', 'Total Price', 'Paid Price'
        for index, row in df.iterrows():
            try:
                # Convert the date to the correct format
                date_str = row['Date']
                date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()  # Adjust the format as needed

                # Clean and convert price fields to decimal
                total_price = float(re.sub(r'[^\d.]', '', str(row['Total Price'])))
                paid_price = float(re.sub(r'[^\d.]', '', str(row['Paid Price'])))

                FinanceRecord.objects.create(
                    business=business,
                    sold_piece=row['Sold Piece'],
                    sold_to=row['Sold To'],
                    date=date_obj,
                    total_price=total_price,
                    paid_price=paid_price
                )
            except (ValueError, TypeError) as e:
                # Handle conversion errors
                return render(request, 'businesses/upload_finacne.html', {'error': f'Error in row {index + 1}: {e}'})

        return redirect(reverse('welcome:dashboard'))

    return render(request, 'businesses/upload_finance.html')

@has_business_required
def finance_records_list(request):
    # Retrieve all finance records for the logged-in user's business
    try:
        business = Business.objects.get(user=request.user)
        finance_records = FinanceRecord.objects.filter(business=business)
    except Business.DoesNotExist:
        finance_records = []

    return render(request, 'businesses/finance_records_list.html', {'finance_records': finance_records})



@login_required
def submit_complaint(request):
    user = request.user

    # Try to get the user's business, but don't require it
    business = None
    if user.is_authenticated:
        business = user.businesses.first()  # Get the first owned business if it exists

    if request.method == "POST":
        text = request.POST.get("text")
        voice_base64 = request.POST.get("voice")

        # Validate inputs
        if not text and not voice_base64:
            return render(request, 'businesses/submit_complaint.html', {
                "error": "You must provide either text or voice input."
            })
        if text and voice_base64:
            return render(request, 'businesses//submit_complaint.html', {
                "error": "You can only provide one input: text or voice."
            })

        # Decode and save the voice file if provided
        voice_file = None
        if voice_base64:
            format, audio_str = voice_base64.split(';base64,')
            ext = format.split('/')[-1]
            voice_file = ContentFile(base64.b64decode(audio_str), name=f"complaint_{user.id}.{ext}")

        # Save the complaint, with or without a business
        Complaint.objects.create(
            business=business,  # This will be None if user has no business
            user=user,
            text=text,
            voice=voice_file,
        )

        # Redirect to the desired URL after submission
        return redirect('welcome:dashboard')

    return render(request, 'businesses/submit_complaint.html')


client = OpenAI(api_key="sk-6893bfcc17c640ec8c89de05ac8e2c7b", base_url="https://api.deepseek.com")
@business_required
def api(request, business_id):
    if request.method == "POST":
        # Get form data
        project_name = request.POST.get("project_name")
        project_description = request.POST.get("project_description")

        # Fetch business using business_id from URL
        business = Business.objects.get(id=business_id)

        # Fetch employees from the business
        employees = business.members.all()

        # Prepare employee details
        employee_details = "\n".join(
            f"{emp.userprofile.name}, {emp.userprofile.role}, {emp.userprofile.qualifications}"
            for emp in employees
        )

        # Detect if the input is in Arabic
        is_arabic = any("\u0600" <= char <= "\u06FF" for char in project_description + employee_details)

        # Generate prompt for the model
        prompt = f"""
        Project Name: {project_name}
        Project Description: {project_description}

        Employees:
        {employee_details}

        Break this project into smaller tasks with descriptions. Then, assign each task to the most suitable employee based on their skills and position. Provide a reason for each assignment.
        """

        # Add language instruction to the prompt
        if is_arabic:
            prompt += "\n\nPlease respond in Arabic."

        # Send prompt to DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a project management assistant."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        # Get the generated tasks, assignments, and reasons
        tasks_and_assignments = response.choices[0].message.content

        # Save the result to the database
        ProjectResult.objects.create(
            business_name=business.name,
            tasks_and_assignments=tasks_and_assignments
        )

        # Render results page
        return render(request, "businesses/result.html", {'tasks_and_assignments': tasks_and_assignments})

    # Fetch the business using business_id from URL
    business = Business.objects.get(id=business_id)

    # Render form page with business context
    return render(request, "businesses/api_form.html", {'business': business})


@has_business_required
def change_user_role(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        new_role = request.POST.get('role')

        # Update the user's role
        user.role = new_role
        user.save()

        messages.success(request, f"User role changed to {new_role}.")
        return redirect('welcome:dashboard')  # Redirect to the dashboard or appropriate page

    return redirect('welcome:dashboard')  # Fallback redirect


@business_required
def process_excel(request, file_path):
    try:
        # Construct the full file path
        file_path = Path(file_path)

        # Check if the file exists
        if not file_path.exists():
            messages.error(request, f"The file at '{file_path}' does not exist.")
            return []

        # Read the Excel file
        data = pd.read_excel(file_path)

        # Define expected column names and their possible variations
        column_variations = {
            'Name': ['Full Name', 'Employee Name', 'Employee Names', 'Name'],
            'Email': ['Email Address', 'Email', 'Emails'],
            'Role': ['Role Type', 'User Role', 'Role'],
            'Job_Description': ['Job Title', 'Job Description', 'Description'],
            'Start_Date': ['Start Date', 'Starting Date', 'Date'],
            'Qualifications': ['Qualifications', 'Skills'],
            'Comments': ['Comments', 'Notes'],
            'Penalties': ['Penalties', 'Penalty Points'],
            'Section': ['Section', 'Department', 'Team']
        }

        # Standardize column names
        renamed_columns = {}
        for standard_name, variations in column_variations.items():
            for variant in variations:
                if variant in data.columns:
                    renamed_columns[variant] = standard_name
                    break

        # Rename columns if matches found
        if renamed_columns:
            data = data.rename(columns=renamed_columns)

        # Convert to list of dictionaries and clean the data
        parsed_data = []
        for _, row in data.iterrows():
            cleaned_row = {}
            for col in data.columns:
                value = row[col]
                if pd.isna(value):
                    cleaned_row[col] = ''
                elif isinstance(value, pd.Timestamp):
                    cleaned_row[col] = value.strftime('%Y-%m-%d')
                else:
                    cleaned_row[col] = str(value).strip()
            parsed_data.append(cleaned_row)

        # Print debugging information
        print("Parsed Data:", parsed_data)
        print("Columns:", data.columns.tolist())

        return parsed_data

    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        messages.error(request, f"Error processing Excel file: {str(e)}")
        return []

@business_required
def create_accounts_from_excel(file_path, business):
    try:
        # Read the Excel file
        print(f"Reading file from: {file_path}")  # Debug print
        data = pd.read_excel(file_path)
        
        print("Original columns:", data.columns.tolist())  # Debug print

        # Standardize column names (case-insensitive)
        data.columns = [col.strip().lower() for col in data.columns]
        
        # Required columns check
        required_columns = ['name', 'email']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        total_rows = len(data)
        members_data = []
        created_users = []

        for index, row in data.iterrows():
            try:
                # Extract data (case-insensitive)
                name = str(row.get('name', '')).strip()
                email = str(row.get('email', '')).strip()
                role = str(row.get('role', 'member')).strip()  # Default role is 'member'

                if not email or not name:
                    print(f"Skipping row {index}: Missing name or email")
                    continue

                # Generate username from email
                username = email.split('@')[0]
                
                # Generate random password
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

                # Create or update user
                user, created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': name.split()[0] if ' ' in name else name,
                        'last_name': ' '.join(name.split()[1:]) if ' ' in name else '',
                        'role': role
                    }
                )

                if created:
                    user.set_password(password)
                    user.save()
                    print(f"Created new user: {email}")  # Debug print
                    
                    # Create UserProfile if it doesn't exist
                    UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'status': 'Pending',
                            'logged_in_status': 'Never Logged In'
                        }
                    )

                    # Send credentials email
                    send_user_credentials_email(email, password, name)
                    
                    members_data.append({
                        'Email': email,
                        'Password': password
                    })

                created_users.append(user)

            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue

        # Add users to business
        if created_users:
            business.members.add(*created_users)
            business.save()
            print(f"Added {len(created_users)} users to business {business.name}")

        # Create Excel file with credentials
        if members_data:
            create_members_excel(members_data)

        return members_data

    except Exception as e:
        print(f"Error in create_accounts_from_excel: {str(e)}")
        raise

@business_required
def create_members_excel(members_data):
    # Create Excel file with member data
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(['Email', 'Password'])  # Add header row

    for member in members_data:
        ws.append([member['Email'], member['Password']])

    wb.save(os.path.join(settings.MEDIA_ROOT, 'created_members.xlsx'))

@business_required
def get_progress(request):
    # Return current progress from cache
    progress = cache.get('progress', 0)
    return JsonResponse({'progress': progress})

@business_required
def loading_page(request):
    return render(request, 'businesses/loading_page.html')  # Ensure this is the loading page template

@business_required
def send_user_credentials_email(email, password, name):
    """Sends email with credentials (USE WITH EXTREME CAUTION)."""

    subject = "Your New Account Credentials"
    text_content = f"""
    Dear {name},

    Your account has been created with the following credentials:

    Email: {email}
    Password: {password}

    We *strongly* recommend changing your password immediately after your first login.

    Sincerely,
    The Team
    """

    html_content = f"""
    <p>Dear {name},</p>
    <p>Your account has been created with the following credentials:</p>
    <ul>
        <li>Email: {email}</li>
        <li>Password: {password}</li>
    </ul>
    <p>We <strong>strongly</strong> recommend changing your password immediately after your first login.</p>
    <p>Sincerely,<br>Net Full Team</p>
    """

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send()
    except Exception as e:
        print(f"Error sending email to {email}: {e}")

@has_business_required
def member_detail(request, member_id):
    # Get the member object
    member = get_object_or_404(CustomUser, id=member_id)
    
    # Check if the logged-in user owns the business the member belongs to
    if not member.member_of_businesses.filter(user=request.user).exists():
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Render the member detail template
    return render(request, 'businesses/member_detail.html', {'member': member})



import os
import zipfile
from django.http import HttpResponse
from django.conf import settings
import ffmpeg

# Define paths relative to the project
BASE_DIR = os.path.join(settings.MEDIA_ROOT, 'call_center_zips')
ZIP_FILE = '1.zip'  # Name of the zip file
OUTPUT_DIR = os.path.join(settings.MEDIA_ROOT, 'unzipped_calls')
@has_business_required
def unzip_and_convert(request):
    """
    A Django view to unzip call center files and convert non-MP3 files to MP3 using ffmpeg-python.
    """
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    def unzip_file(zip_path, output_dir):
        """Unzip the given zip file to the specified output directory."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        return f"Extracted files to {output_dir}"

    def convert_to_mp3(file_path, output_dir):
        """Convert non-MP3 audio files to MP3 format using ffmpeg-python."""
        if not file_path.lower().endswith('.mp3'):
            try:
                # Generate the output file name
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_file = os.path.join(output_dir, f"{base_name}.mp3")

                # Use ffmpeg-python to convert the file
                stream = ffmpeg.input(file_path)
                stream = ffmpeg.output(stream, output_file, codec='libmp3lame', overwrite_output=True)
                ffmpeg.run(stream)

                return f"Converted {file_path} to {output_file}"
            except Exception as e:
                return f"Failed to convert {file_path}: {e}"
        return f"File {file_path} is already MP3."

    def process_files():
        """Main function to unzip and process files."""
        zip_path = os.path.join(BASE_DIR, ZIP_FILE)
        
        # Check if the zip file exists
        if not os.path.exists(zip_path):
            return f"Zip file not found: {zip_path}"
        
        # Unzip the file
        result = unzip_file(zip_path, OUTPUT_DIR)
        
        # Process each file in the unzipped directory
        results = [result]
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                results.append(convert_to_mp3(file_path, OUTPUT_DIR))
        
        return "\n".join(results)

    # Execute the processing
    response_content = process_files()
    return HttpResponse(response_content, content_type="text/plain")

@has_business_required
def online_meeting(request, room_name):
    # Add your OAuth credentials from Google Cloud Console and GitHub
    GOOGLE_CLIENT_ID = "your-google-client-id"
    GITHUB_CLIENT_ID = "your-github-client-id"
    JITSI_APP_ID = settings.JITSI_APP_ID
    
    context = {
        'room_name': room_name,
        'google_client_id': GOOGLE_CLIENT_ID,
        'github_client_id': GITHUB_CLIENT_ID,
    }
    return render(request, 'businesses/meeting.html', context)

@csrf_exempt
def get_jitsi_token(request):
    # Get credentials from settings
    JITSI_APP_ID = settings.JITSI_APP_ID
    JITSI_APP_SECRET = settings.JITSI_APP_SECRET
    
    if request.user.is_authenticated:
        room_name = request.GET.get('room', '*')
        
        payload = {
            "iss": JITSI_APP_ID,
            "aud": "jitsi",
            "sub": "meet.jit.si",
            "exp": int(time.time()) + 3600,
            "room": room_name,
            "context": {
                "user": {
                    "id": str(request.user.id),
                    "name": request.user.get_full_name() or request.user.username,
                    "email": request.user.email,
                    "avatar": request.user.userprofile.avatar.url if hasattr(request.user, 'userprofile') and request.user.userprofile.avatar else "",
                    "moderator": "true" if request.user.is_staff else "false"
                }
            }
        }
        
        token = jwt.encode(payload, JITSI_APP_SECRET, algorithm='HS256')
        return JsonResponse({"token": token})
    
    return JsonResponse({"error": "Authentication required"}, status=401)
