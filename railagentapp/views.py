from django.shortcuts import render

def index(request):
    # This just hands the HTML page to the user. 
    # Once the page loads, the JavaScript inside it takes over.
    return render(request, 'homepage.html')