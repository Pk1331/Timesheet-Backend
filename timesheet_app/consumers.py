from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", None)
        user_id_from_path = self.scope["url_route"]["kwargs"].get("user_id")
        if user and user.is_authenticated and str(user.id) == user_id_from_path:
            self.user_id = str(user.id)
            self.group_name = f"user_{self.user_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        await self.send(text_data=json.dumps({"ack": "Message received"}))

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["notification"]))
