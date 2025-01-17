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


@login_required
def add_business(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        icon = request.FILES['icon']
        employee_file = request.FILES['employee_file']
        category = request.POST.get('category')
        # Save the icon to the 'uploaded_icons' directory
        icon_fs = FileSystemStorage(location='media/uploaded_icons')
        icon_name = icon_fs.save(icon.name, icon)

        # Save the employee file to the 'uploaded_excel' directory
        excel_fs = FileSystemStorage(location='media/uploaded_excel')
        employee_file_name = excel_fs.save(employee_file.name, employee_file)

        # Create a new Business instance
        business = Business.objects.create(
            name=company_name,
            icon=f'uploaded_icons/{icon_name}',
            employee_file=f'uploaded_excel/{employee_file_name}',
            user=request.user,
            category=category
        )

        # Process the Excel file and get the parsed data
        employee_file_path = excel_fs.path(employee_file_name)

        parsed_data = process_excel(request, employee_file_path)

        # Render the review template with all necessary context
        return render(request, 'businesses/review_business_data.html', {
            'company_name': company_name,
            'icon_name': icon_name,
            'data': parsed_data,  # Pass the parsed data as 'data'
            'business_id': business.id
        })

    return render(request, 'businesses/add_business.html')


def business_members_view(request, business_id):
    """
    View to render members of a specific business.
    """
    business = get_object_or_404(Business, id=business_id)
    members = business.members.all()  # Get all members associated with the business

    # Collect member details
    member_details = []
    for member in members:
        member_details.append({
            'name': member.username,  # Assuming you want to show the username
            'email': member.email,
            'role': member.role,  # Assuming 'role' is a field in CustomUser
            'job_description': member.profile.job_description if hasattr(member, 'profile') else 'No job description',  # Accessing profile details
            'status': member.profile.status if hasattr(member, 'profile') else 'No status',  # Accessing profile status
        })

    context = {
        'business': business,
        'members': member_details
    }
    return render(request, 'businesses/business_members.html', context)

@login_required
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

            return redirect('dashboard')

        except Exception as e:
            print(f"Error in process_business_data: {str(e)}")  # Debug print
            messages.error(request, f"Error processing business data: {str(e)}")
            return redirect('add_business')

    return redirect('add_business')


@login_required
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


@login_required
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

        return redirect(reverse('dashboard'))

    return render(request, 'businesses/upload_finance.html')

@login_required
def finance_records_list(request):
    # Retrieve all finance records for the logged-in user's business
    try:
        business = Business.objects.get(user=request.user)
        finance_records = FinanceRecord.objects.filter(business=business)
    except Business.DoesNotExist:
        finance_records = []

    return render(request, 'finance_records_list.html', {'finance_records': finance_records})


import base64
from django.core.files.base import ContentFile

@login_required
def submit_complaint(request):
    user = request.user

    # Ensure the user owns a business
    try:
        business = user.businesses.first()  # Get the first owned business
        if not business:
            raise PermissionDenied("You do not own a business.")
    except Business.DoesNotExist:
        raise PermissionDenied("You do not own a business.")

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

        # Save the complaint
        Complaint.objects.create(
            business=business,
            user=user,
            text=text,
            voice=voice_file,
        )

        # Redirect to the desired URL after submission
        return redirect('http://127.0.0.1:8000/')

    return render(request, 'businesses/submit_complaint.html')


client = OpenAI(api_key="sk-6893bfcc17c640ec8c89de05ac8e2c7b", base_url="https://api.deepseek.com")
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

# Function to change user role
@login_required
def change_user_role(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        new_role = request.POST.get('role')

        # Update the user's role
        user.role = new_role
        user.save()

        messages.success(request, f"User role changed to {new_role}.")
        return redirect('dashboard')  # Redirect to the dashboard or appropriate page

    return redirect('dashboard')  # Fallback redirect



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

def create_members_excel(members_data):
    # Create Excel file with member data
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(['Email', 'Password'])  # Add header row

    for member in members_data:
        ws.append([member['Email'], member['Password']])

    wb.save(os.path.join(settings.MEDIA_ROOT, 'created_members.xlsx'))


def get_progress(request):
    # Return current progress from cache
    progress = cache.get('progress', 0)
    return JsonResponse({'progress': progress})

def loading_page(request):
    return render(request, 'businesses/loading_page.html')  # Ensure this is the loading page template

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



@login_required
def member_detail(request, member_id):
    # Get the member object
    member = get_object_or_404(CustomUser, id=member_id)
    
    # Check if the logged-in user owns the business the member belongs to
    if not member.member_of_businesses.filter(user=request.user).exists():
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Render the member detail template
    return render(request, 'businesses/member_detail.html', {'member': member})