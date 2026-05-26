from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view),
    path('records/', views.records_view),
    path('records/<int:record_id>/', views.record_detail_view),
    path('records/<int:record_id>/approve/', views.approve_view),
    path('records/<int:record_id>/reject/', views.reject_view),
    path('records/<int:record_id>/flag/', views.flag_view),
    path('sources/', views.sources_view),
    path('seed-demo/', views.seed_demo_view),
]
