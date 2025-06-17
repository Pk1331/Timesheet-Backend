from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import CustomUser,Timesheet
from rest_framework.response import Response
from django.db.models import Q,Sum

# --------------------- FETCH PROFILE INFO ---------------------
class FetchUserDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user.id,
                "username": user.username,
                "first_name": user.firstname,
                "last_name": user.lastname,
                "usertype": user.usertype,
                "email": user.email,
                "team": user.team,
                "subteam": user.subteam,
            }
            return Response(user_data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

# --------------------- UPDATE PROFILE INFO ---------------------
class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, user_id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.email = request.data.get('email', user.email)
            user.save()
            return Response({"message": "Profile updated successfully", "status": "success"}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update profile", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Users Based on the User Type 
class FetchUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        usertype = request.query_params.get('usertype')
        subteam = request.query_params.get('subteam')
        
        if user.usertype == 'SuperAdmin':
            users = CustomUser.objects.filter(
                Q(usertype='Admin') | Q(usertype='TeamLeader') | Q(usertype='User')
            ).exclude(username='Narayan')
        elif user.usertype == 'Admin':
            users = CustomUser.objects.filter(
                Q(usertype='TeamLeader') | Q(usertype='User')
            )
        elif user.usertype == 'TeamLeader':
            users = CustomUser.objects.filter(team=user.team).exclude(id=user.id)
        else:
            users = CustomUser.objects.none()

        if usertype:
            users = users.filter(usertype__in=usertype.split(','))
        if subteam:
            users = users.filter(subteam=subteam)
        
        user_data = [{"id": user.id, "username": user.username, "team": user.team} for user in users]
        return Response({"users": user_data}, status=status.HTTP_200_OK)
    
# Fetch Team Leaders for a Specific Team
class FetchTeamLeadersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        team = request.query_params.get('team')
        if team not in ['Search', 'Creative', 'Development']:
            return Response({"message": "Invalid team"}, status=status.HTTP_400_BAD_REQUEST)

        team_leaders = CustomUser.objects.filter(
            usertype='TeamLeader',
            team=team
        )
        team_leader_data = [
            {"id": leader.id, "username": leader.username}
            for leader in team_leaders
        ]
        return Response({"team_leaders": team_leader_data}, status=status.HTTP_200_OK)

# Fetch Working Hours Data
class FetchWorkingHoursView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        usertype = user.usertype
        user_id = user.id

        if usertype == 'SuperAdmin' or usertype == 'Admin':
            users = CustomUser.objects.all()
        elif usertype == 'TeamLeader':
            users = CustomUser.objects.filter(team=user.team)
        elif usertype == 'User':
            users = CustomUser.objects.filter(id=user.id)
        else:
            users = CustomUser.objects.none()

        working_hours = Timesheet.objects.values('created_by__id').annotate(hours=Sum('hours'))
        working_hours_dict = {item['created_by__id']: item['hours'] for item in working_hours}

        working_hours_data = [
            {"name": user.username, "hours": working_hours_dict.get(user.id, 0)}
            for user in users
        ]

        return Response({"working_hours": working_hours_data}, status=status.HTTP_200_OK)

# --------------------- Fetch ALL USERS FOR TELEGRAM  ---------------------
class FetchAllUsers(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        users = CustomUser.objects.exclude(id=request.user.id) \
                                  .exclude(is_superuser=True) \
                                  .exclude(usertype="SuperAdmin")  

        user_data = [
            {"id": user.id, "username": user.username, "team": user.team}
            for user in users
        ]
        return Response({"users": user_data}, status=status.HTTP_200_OK)