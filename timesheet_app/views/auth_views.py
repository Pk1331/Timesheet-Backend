from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken  
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse
from datetime import timedelta
from django.utils.timezone import localtime
import random

from timesheet_app.models import CustomUser, Notification
from timesheet_app.utils import send_telegram_message
from timesheet_app.authentication import CookieJWTAuthentication


# --------------------- LOGIN ---------------------
class CustomTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = request.data.get("username")
        password = request.data.get("password")

        user = self.get_user(identifier)
        if not user or not check_password(password, user.password):
            return Response({
                "message": "Invalid username/email or password",
                "status": "failure"
            }, status=status.HTTP_401_UNAUTHORIZED)

        return self.generate_token_response(user)

    def get_user(self, identifier):
        try:
            return CustomUser.objects.get(username=identifier)
        except CustomUser.DoesNotExist:
            try:
                return CustomUser.objects.get(email=identifier)
            except CustomUser.DoesNotExist:
                return None

    def generate_token_response(self, user):
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access.set_exp(lifetime=timedelta(minutes=60))

        # Convert to IST
        access_token_expiry = (localtime(timezone.now()) + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")

        response = JsonResponse({
            "message": "Login successful",
            "status": "success",
            "firstname": user.firstname,
            "username": user.username,
            "usertype": user.usertype,
            "email": user.email,
            "user_id": user.id,
            "access_token_expiry": access_token_expiry,
            "access_token": str(access)
        })

        cookie_settings = {
            "httponly": True,
            "secure": True,  # Set to True on production with HTTPS
            "samesite": "None", # Use "None" for cross-site requests, "Lax" for same-site
            "max_age": 60 * 60,
        }

        response.set_cookie("access_token", str(access), **cookie_settings)
        response.set_cookie(
            "refresh_token",
            str(refresh),
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            secure=True, # Set to True on production with HTTPS
            samesite="None"  # Use "None" for cross-site requests, "Lax" for same-site
            # samesite="Lax" if you want to restrict to same-site requests
        )

        return response

# --------------------- REFRESH TOKEN ---------------------
class RefreshTokenView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
            access.set_exp(lifetime=timedelta(minutes=60))

            # Convert to IST
            access_token_expiry = (localtime(timezone.now()) + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")

            response = Response({
                "message": "Access token refreshed",
                "access_token_expiry": access_token_expiry,
                "access_token": str(access)
            })

            response.set_cookie(
                "access_token",
                str(access),
                httponly=True,
                max_age=60 * 60,
                secure=True,
                samesite="None"  # Use "None" for cross-site requests, "Lax" for same-site
            )
            return response
        except Exception:
            return Response({"error": "Refresh token expired or invalid"}, status=401)
        
# --------------------- LOGOUT ---------------------
class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if not refresh_token:
                raise Exception("No refresh token provided")

            token = RefreshToken(refresh_token)
            token.blacklist()

            response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        except Exception:
            return Response({"error": "Invalid token or already logged out"}, status=status.HTTP_400_BAD_REQUEST)
        
# --------------------- CHECK AUTH ---------------------
class AuthCheckView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Authenticated",
            "status": "success",
            "username": request.user.username
        })


# --------------------- PASSWORD RESET REQUEST ---------------------
class RequestPasswordResetCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username_or_email")
        user = CustomUser.objects.filter(username=username_or_email).first() or \
               CustomUser.objects.filter(email=username_or_email).first()

        if not user:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        code = str(random.randint(100000, 999999))
        cache.set(f"reset_code_{user.id}", code, timeout=600)

        message = f"Your password reset verification code is: {code}"
        send_telegram_message(user.chat_id, message)

        return Response({"code": code, "message": "Verification code sent", "status": "success"}, status=status.HTTP_200_OK)


# --------------------- CHANGE PASSWORD / RESET PASSWORD ---------------------
class ChangePasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            user = request.user
            current_password = request.data.get("current_password")
            new_password = request.data.get("new_password")
            confirm_password = request.data.get("confirm_password")

            if not check_password(current_password, user.password):
                return Response({"message": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
            if new_password != confirm_password:
                return Response({"message": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)

            message = "Your password has been changed successfully."
            send_telegram_message(user.chat_id, message)
            Notification.objects.create(user=user, message=message)

            return Response({"message": "Password changed successfully", "status": "success"}, status=status.HTTP_200_OK)

        # Anonymous user (reset via code)
        username_or_email = request.data.get("username_or_email")
        verification_code = request.data.get("verification_code")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        user = CustomUser.objects.filter(email=username_or_email).first() or \
               CustomUser.objects.filter(username=username_or_email).first()

        if not user:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        stored_code = cache.get(f"reset_code_{user.id}")
        if not stored_code or str(stored_code) != str(verification_code):
            return Response({"message": "Invalid or expired verification code"}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"message": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        cache.delete(f"reset_code_{user.id}")

        message = "Your password has been successfully reset."
        send_telegram_message(user.chat_id, message)
        Notification.objects.create(user=user, message=message)

        return Response({"message": "Password reset successfully", "status": "success"}, status=status.HTTP_200_OK)


# --------------------- USER REGISTRATION ---------------------
class RegisterUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        email = data.get('email')
        password = data.get('password')
        usertype = data.get('usertype')
        team = data.get('team')
        subteam = data.get('subteam')
        chat_id = data.get('chat_id')

        username = firstname

        if CustomUser.objects.filter(email=email).exists():
            return Response({
                "message": "Registration failed",
                "status": "failure",
                "error": "Email is already registered."
            }, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username=username).exists():
            return Response({
                "message": "Registration failed",
                "status": "failure",
                "error": "Username is already taken."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                usertype=usertype,
                firstname=firstname,
                lastname=lastname,
                team=team,
                subteam=subteam,
                chat_id=chat_id
            )

            message = f"Welcome to the Timesheet App! Your username is {username}, and your password is {password}. Please change it after login."
            send_telegram_message(chat_id, message)
            Notification.objects.create(user=user, message=message)

            return Response({
                "message": "User registered successfully",
                "status": "success",
                "username": user.username,
                "usertype": user.usertype,
                "email": user.email,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "message": "Registration failed",
                "status": "failure",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

