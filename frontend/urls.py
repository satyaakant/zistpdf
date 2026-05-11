from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('', views.home, name='home'),  

    # rest api
    path('rest/readpdf/', views.readpdf, name='readpdf'),
    path('rest/generateqa/', views.generateQA, name='generateqa'),
    path('rest/chat/', views.chat, name='chat'),
]