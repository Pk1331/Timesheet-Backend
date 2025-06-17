from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from timesheet_app.serializers import NotificationSerializer

def send_notification_to_user(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    user = notification.user
    group_name = f"user_{user.id}"

    serialized_data = NotificationSerializer(notification).data

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send.notification",  
            "notification": serialized_data,
        }
    )
