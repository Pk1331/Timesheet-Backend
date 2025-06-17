from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from jwt import decode as jwt_decode 

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        validated_token = UntypedToken(token)
        user_id = validated_token['user_id']
        user = User.objects.get(id=user_id)
        return user
    except (User.DoesNotExist, InvalidToken, TokenError) as e:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()

        token = parse_qs(query_string).get("token", [None])[0]
       
        if token:
            user = await get_user_from_token(token)
        else:
            user = AnonymousUser()

        scope['user'] = user
        return await super().__call__(scope, receive, send)
