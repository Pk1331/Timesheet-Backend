# timesheet_app/views.py
from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import Notification
from timesheet_app.serializers import NotificationSerializer
from rest_framework.response import Response

# --------------------- Fetch Notifications ---------------------
class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
# --------------------- Mark Read  Notifications ---------------------
class MarkNotificationAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({"message": "Marked as read"})
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
  
# --------------------- Delete Read Notifications ---------------------      
class DeleteReadNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        read_notifications = Notification.objects.filter(user=request.user, is_read=True)
        count = read_notifications.count()
        read_notifications.delete()
        return Response(
            {"message": f"{count} read notifications deleted."},
            status=status.HTTP_200_OK
        )
