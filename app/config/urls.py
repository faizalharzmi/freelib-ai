from django.contrib import admin
from django.urls import include, path
from analytics.views import dashboard
from discovery import web

urlpatterns = [
    path('admin/analytics/', dashboard, name='analytics_dashboard'),
    path('admin/', admin.site.urls),
    path('', web.home, name='home'),
    path('search/', web.search, name='search'),
    path('book/', web.detail, name='book_detail'),
    path('api/search/', web.api_search, name='ai_search'),
    path('api/', include('discovery.urls')),
]
