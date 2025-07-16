"""
URL configuration for bsc_gen project.

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
from django.conf import settings
from django.conf.urls.static import static
from .views import register, login_view, logout_view, dashboard, bsc_data_api, bsc_detailed_view, delete_bsc_data, delete_batch, update_batch, profile_view, add_viewer, delete_viewer, batch_details_api, rename_batch, generate_batch_pdf, forgot_password, password_reset_confirm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile_view, name='profile'),
    path('add-viewer/', add_viewer, name='add_viewer'),
    path('delete-viewer/<int:viewer_id>/', delete_viewer, name='delete_viewer'),
    path('api/bsc-data/', bsc_data_api, name='bsc_data_api'),
    path('bsc-detailed/', bsc_detailed_view, name='bsc_detailed'),
    path('delete-bsc-data/', delete_bsc_data, name='delete_bsc_data'),
    path('delete-batch/<str:batch_id>/', delete_batch, name='delete_batch'),
    path('update-batch/<str:batch_id>/', update_batch, name='update_batch'),
    path('rename-batch/<str:batch_id>/', rename_batch, name='rename_batch'),
    path('batch-report/<str:batch_id>/', generate_batch_pdf, name='batch_report_pdf'),
    path('api/batch-details/', batch_details_api, name='batch_details_api'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('', dashboard, name='home')
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
