from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

<<<<<<< HEAD
def adminview(request):
    return render(request, "adminview/home.html")
=======
User = get_user_model()

def is_app_admin(user):
    return user.is_authenticated and user-is_app_admin

@login_required
def admin_dashboard(request):
    if not is_app_admin(request.user):
        return redirect ('login')
    
    return render(request, 'adminview.html')

def adminview(request):
    return render(request, 'adminview.html')
>>>>>>> 57f056b (adminview_first)
