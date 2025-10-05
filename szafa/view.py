from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "home.html")
    
class UserLoginView(LoginView):
    template_name = "auth/login.html"


class UserLogoutView(LogoutView):
    pass