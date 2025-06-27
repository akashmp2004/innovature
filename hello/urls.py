from django.urls import path
from hello import views
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.views.generic.base import RedirectView
from django.views.generic import View
from django.contrib.auth import logout
from django.shortcuts import redirect





urlpatterns = [
    path("", views.first_page, name="first_page"),
    path("login", views.login, name="login"),
    path("front_page", views.first_page, name="first_page"),
    path("signup", views.signup, name="signup"),
    path('admin/', admin.site.urls),
    path("dashboard", views.dashboard, name="dashboard"),
    path('dashboard/create/', views.create_group, name='create_group'),
    path('dashboard/create/<int:group_id>/add-members/', views.add_members, name='add_members'),
    path('dashboard/groups/', views.list_groups, name='list_groups'),
    path('dashboard/groups/<int:group_id>/', views.view_group, name='view_group'),
    path('groups/<int:group_id>/add-expense/', views.add_expense, name='add_expense'),
    path('splits/<int:split_id>/mark-paid/', views.mark_paid, name='mark_paid'),
    path('dashboard/amounts-owed/', views.amounts_owed, name='amounts_owed'),
    path('dashboard/amounts-to-receive/', views.amounts_to_receive, name='amounts_to_receive'),
    path('groups/<int:group_id>/soft-delete/', views.soft_delete_group, name='soft_delete_group'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('groups/<int:group_id>/remove-member/<int:user_id>/', 
         views.remove_member, 
     name='remove_member'),
]