"""
URL configuration for kgl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.Login, name='login'),  # Login page
    path('logout/',views.Logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    #global search for the dashboard
    path('search/', views.global_search, name='global_search'),
    path('dashboard3/', views.admin, name='dashboard3'),  # Owner
    path('dashboard2/', views.branch, name='dashboard2'),  # Manager and Sales agent
    #This is the path for the home page
    #path('home/', views.index, name='home'),

    #This is the path for the products page
    path('products/', views.products_list, name='products_list'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),


    #This is the path for inventory
    path('inventory-status/', views.inventory_status, name='inventory_status'),

    #This is the procurement path
    path('procurement/', views.procurement_list, name='procurement_list'),
    path('procurement/add/', views.add_procurement, name='add_procurement'),
    path('procurement/edit/<int:pk>/', views.edit_procurement, name='edit_procurement'),
    path('procurement/delete/<int:pk>/', views.delete_procurement, name='delete_procurement'),
    path('procurement/view/<int:pk>/', views.view_procurement, name='view_procurement'),
    path('procurement/receipt/<int:pk>/', views.receipt_procurement, name='receipt_procurement'),

    #This is the path for stock
    path('inventory/', views.viewstock, name='viewstock'),

    #this is path for payments
    path('payments/', views.payments_list, name='payments_list'),
    path('payments/edit/<int:pk>/', views.edit_payments, name='edit_payments'),
    path('payments/view/<int:pk>/', views.payment_details, name='payment_details'),
    path('payments/receipt/<int:pk>/', views.pay_receipt, name='pay_receipt'),

    #This is the path for sales
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/add/', views.add_sale, name='add_sale'),
    path('sales/delete/<int:pk>/', views.delete_sale, name='delete_sale'),
    path('sales/edit/<int:pk>/', views.edit_sale, name='edit_sale'),
    path('sales/view/<int:pk>/', views.view_sale, name='view_sale'),
    path('sales/receipt/<int:pk>/', views.sale_receipt, name='sale_receipt'),
    

    #path for users
    path('users/', views.userspage, name='userspage'),
    path('deleteuser/<int:pk>/', views.deleteuser, name='deleteuser'),
    path('viewuser/<int:pk>/', views.viewuser, name='viewuser'),
    path('edituser/<int:pk>/', views.edituser, name='edituser'),

    #health check
    path('ping/', views.health_check, name='ping'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


