from django.urls import path, include
urlpatterns = [
    path('', include('timesheet_app.urls.auth_urls')),
    path('projects/', include('timesheet_app.urls.project_urls')),
    path('teams/', include('timesheet_app.urls.team_urls')),
    path('tasks/', include('timesheet_app.urls.task_urls')),
    path('', include('timesheet_app.urls.user_urls')),
    path('timesheets/', include('timesheet_app.urls.timesheet_urls')),
    path('',include('timesheet_app.urls.message_url')),
    path('',include('timesheet_app.urls.notification_urls'))
]
