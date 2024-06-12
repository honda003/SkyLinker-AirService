from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponseRedirect

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # Get the 'next' parameter from the request
            next_url = request.GET.get('next', None)

            # Redirect to 'operations_dashboard' if 'next' is not provided or if it's the airlineoperations URL
            if not next_url or next_url == '/airlineoperations':
                return redirect('operations_dashboard')
            else:
                return HttpResponseRedirect(next_url)

        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'pages/login_operations.html')  # Path to your login template