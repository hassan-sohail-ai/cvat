from django.urls import path
from .views import ClassWiseImageView

urlpatterns = [
    path('class-wise-counts/', ClassWiseImageView.as_view(), name='class-wise-counts'),
]