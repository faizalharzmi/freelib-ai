from django.urls import path
from .views import search_books

urlpatterns = [
    path("books/", search_books, name="search_books"),
]