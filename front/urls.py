from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('query-gemini/', views.query_gemini, name='query_gemini'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),

]
