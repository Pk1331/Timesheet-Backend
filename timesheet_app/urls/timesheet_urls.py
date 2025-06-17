from django.urls import path
from timesheet_app.views.timesheet_views import (
    FetchDepartmentsView,CreateDepartmentView,
    UpdateDepartmentView,DeleteDepartmentView,
    CreateTimesheetView,TimesheetListView,
    EditTimesheetView,BulkDeleteTimesheetsView,
    SendTimesheetsForReviewView,TimesheetsPendingReviewView,
    AdminReviewTimesheetView,ApprovedTimesheetsView,
)

urlpatterns = [
    
    #Department CRUD Operations
    path('departments/', FetchDepartmentsView.as_view(), name='fetch_departments'),
    path('departments/create/', CreateDepartmentView.as_view(), name='create-department'),
    path('departments/<int:pk>/', UpdateDepartmentView.as_view(), name='update-department'),
    path('departments/<int:pk>/delete/', DeleteDepartmentView.as_view(), name='delete-department'),
    
    # Timesheet Tables CRUD Operations
    path('create/', CreateTimesheetView.as_view(), name='create_timesheets'),
    path('view/', TimesheetListView.as_view(), name='fetch_timesheets'),
    path('edit/',EditTimesheetView.as_view(),name='edit-timesheets'),
    path('bulk-delete/',BulkDeleteTimesheetsView.as_view(),name='delete-timsheets'),
    path('send-for-review/',SendTimesheetsForReviewView.as_view(),name='review-timsheets'),
    path('pending-review/',TimesheetsPendingReviewView.as_view(),name='pending-review-timsheets'),
    path('admin-review/',AdminReviewTimesheetView.as_view(),name='admin-review'),
    path('approved-timesheets/',ApprovedTimesheetsView.as_view(),name='approved-timesheets'),
    
    
    
    
]
