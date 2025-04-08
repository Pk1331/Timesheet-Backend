from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from timesheet_app.models import CustomUser
from timesheet_app.utils import send_telegram_message
import logging
import json

logger = logging.getLogger(__name__)

class CustomMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("Received a request to send a Telegram message.")
        data = request.data
        file = request.FILES.get("file") 

        user_ids = data.get("users", [])
        message = data.get("message", "").strip()

        # Convert string users to a list if needed
        if isinstance(user_ids, str):  
            try:
                user_ids = json.loads(user_ids)
            except json.JSONDecodeError:
                return Response({
                    "message": "Invalid format for 'users'. It should be a list of integers.",
                    "status": "failure"
                }, status=status.HTTP_400_BAD_REQUEST)

        if not user_ids or not message:
            return Response({
                "message": "Message sending failed",
                "status": "failure",
                "error": "Please select users and enter a message."
            }, status=status.HTTP_400_BAD_REQUEST)

        users = CustomUser.objects.filter(id__in=user_ids)
        if not users.exists():
            return Response({
                "message": "Message sending failed",
                "status": "failure",
                "error": "Selected users do not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        failed_users = []
        for user in users:
            try:
                chat_id = user.chat_id
                if not chat_id:
                    failed_users.append(user.username)
                    continue
                
                send_telegram_message(chat_id, message, file)
            except Exception as e:
                logger.error(f"Failed to send message to {user.username}: {str(e)}", exc_info=True)
                failed_users.append(user.username)

        if failed_users:
            return Response({
                "message": "Message sent partially",
                "status": "partial_success",
                "failed_users": failed_users
            }, status=status.HTTP_207_MULTI_STATUS)

        return Response({
            "message": "Message sent successfully",
            "status": "success"
        }, status=status.HTTP_200_OK)
