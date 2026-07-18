from django.urls import path
from .views import setup

urlpatterns = [path("", setup, name="setup")]
