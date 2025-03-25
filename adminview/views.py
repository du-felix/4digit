from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import UserEditForm
from users.forms import Sign_Up_Form
from users.models import CustomUser
from users.views import signup


User = get_user_model()

# Add this validator function at the top
def validate_afra_email(email):
    """Validate that email ends with @afra.lernsax.de"""
    if not email.endswith('@afra.lernsax.de'):
        raise ValidationError('Only email addresses ending with @afra.lernsax.de are allowed.')
    return email

@login_required
def adminview(request, user_id=None):
    users = User.objects.all().order_by('email')
    
    if user_id:
        edit_user = get_object_or_404(User, id=user_id)
        if request.method == 'POST':
            form = UserEditForm(request.POST, instance=edit_user)
            if form.is_valid():
                # Validate email format before saving
                try:
                    validate_afra_email(form.cleaned_data['email'])
                    form.save()
                    messages.success(request, f"User {edit_user.email} updated successfully")
                    return redirect('adminview-home')
                except ValidationError as e:
                    form.add_error('email', e)
        else:
            form = UserEditForm(instance=edit_user)
    else:
        edit_user = None
        form = Sign_Up_Form()

    if request.method == 'POST' and 'delete_user' in request.POST:
        user_id_to_delete = request.POST.get('delete_user')
        user_to_delete = get_object_or_404(User, id=user_id_to_delete)
        user_to_delete.delete()
        messages.success(request, f'User {user_to_delete.email} deleted successfully')
        return redirect('adminview-home')
    
    context = {
        'users': users,
        'edit_user': edit_user,
        'form': form
    }
    
    return render(request, 'adminview/home.html', context)

def adding(request):
    if request.method == 'POST':
        form = Sign_Up_Form(request.POST)
        if form.is_valid():
            # Validate email format before saving
            try:
                validate_afra_email(form.cleaned_data['email'])
                form.save()
                return redirect('adminview-home')
            except ValidationError as e:
                form.add_error('email', e)
    else:
        form = Sign_Up_Form()
    
    return render(request, 'adminview/add_user.html', {'form': form})

def csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Check if file is CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('adminview-csv')
                
            # Process CSV file
            try:
                csv_data = csv_file.read().decode('utf-8')
                import io
                import csv
                from datetime import datetime
                
                io_string = io.StringIO(csv_data)
                reader = csv.reader(io_string, delimiter=';')
                next(reader)  # Skip header row
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row in reader:
                    try:
                        # Assuming CSV columns: email, password, first_name, last_name, birth_date
                        if len(row) >= 5:
                            email = row[0].strip()
                            password = row[1].strip()
                            first_name = row[2].strip()
                            last_name = row[3].strip()
                            birth_date_str = row[4].strip()
                            
                            # Validate email format
                            try:
                                validate_afra_email(email)
                            except ValidationError as e:
                                errors.append(f"Invalid email for row {email}: {str(e)}")
                                error_count += 1
                                continue
                            
                            # Parse birth date with multiple format support
                            birth_date = None
                            if birth_date_str:
                                # Try multiple date formats
                                date_formats = [
                                    '%Y-%m-%d',  # YYYY-MM-DD
                                    '%d.%m.%Y',  # DD.MM.YYYY
                                    '%d.%m.%y',  # DD.MM.YY (Excel default)
                                    '%m/%d/%Y',  # MM/DD/YYYY
                                    '%m/%d/%y',  # MM/DD/YY
                                ]
                                
                                for date_format in date_formats:
                                    try:
                                        birth_date = datetime.strptime(birth_date_str, date_format).date()
                                        break  # Exit the loop if successful
                                    except ValueError:
                                        continue
                                
                                if birth_date is None:
                                    errors.append(f"Invalid date format for {email}: {birth_date_str}")
                                    error_count += 1
                                    continue
                            
                            # Check if user already exists
                            if not CustomUser.objects.filter(email=email).exists():
                                user = CustomUser(
                                    email=email,
                                    first_name=first_name,
                                    last_name=last_name,
                                    birth_date=birth_date
                                )
                                user.set_password(password)
                                user.save()
                                success_count += 1
                            else:
                                errors.append(f"User with email {email} already exists")
                                error_count += 1
                        else:
                            errors.append(f"Row has insufficient data: {row}")
                            error_count += 1
                    except Exception as e:
                        errors.append(f"Error processing row: {row}. Error: {str(e)}")
                        error_count += 1
                
                # Show results
                if success_count > 0:
                    messages.success(request, f'Successfully created {success_count} user(s)')
                if error_count > 0:
                    messages.warning(request, f'Failed to create {error_count} user(s)')
                    for error in errors[:10]:  # Show only first 10 errors
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors")
                        
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
            
            return redirect('adminview-home')
    
    return render(request, 'adminview/csv.html')
