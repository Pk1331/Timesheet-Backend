from django.urls import path
from timesheet_app.views.notification_views import NotificationListView, MarkNotificationAsReadView,DeleteReadNotificationsView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="user-notifications"),
    path("notifications/<int:pk>/mark-as-read/", MarkNotificationAsReadView.as_view(), name="mark-notification-read"),
    path('notifications/delete-read/', DeleteReadNotificationsView.as_view(), name='delete-read-notifications'),
]