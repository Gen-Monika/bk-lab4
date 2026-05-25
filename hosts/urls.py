from django.urls import path

from . import views

app_name = "hosts"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/businesses/", views.businesses, name="businesses"),
    path("api/sets/", views.sets, name="sets"),
    path("api/modules/", views.modules, name="modules"),
    path("api/hosts/", views.hosts, name="hosts"),
    path("api/hosts/<int:host_id>/", views.host_detail, name="host_detail"),
]
