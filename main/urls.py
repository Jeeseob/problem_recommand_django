
from django.urls import path
from . import views

# 해당앱 내부의 url패턴
urlpatterns =[
    path('', views.main),
    path('learning', views.learning),
    path('search/<str:user_id>', views.search),
]