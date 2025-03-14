from django.shortcuts import render

def adminview(request):
    render(request, "adminview/home.html")
