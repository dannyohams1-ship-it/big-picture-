from django.urls import path
from . import views

urlpatterns = [
    path("ping/", views.ping, name="assistant_ping"),
    
    path("chat/", views.chat_api, name="chat_api"),

    path("analytics/", views.analytics_dashboard, name="assistant_analytics"),
]
