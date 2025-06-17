from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import Project,CustomUser, Team,Notification
from rest_framework.response import Response
from timesheet_app.utils import send_telegram_message
from timesheet_app.notification_ws import send_notification_to_user

# --------------------- CREATE PROJECT ---------------------
class CreateProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        name = data.get('name')
        description = data.get('description')
        project_status = data.get('status')
        start_date = data.get('start_date')
        deadline = data.get('deadline')
        created_by = request.user  
       
        try:
            project = Project.objects.create(
                name=name,
                description=description,
                status=project_status,
                start_date=start_date,
                deadline=deadline,
                created_by=created_by  
            )
            
            return Response({
                "message": "Project created successfully",
                "status": "success",
                "project_id": project.id,
            }, status=status.HTTP_201_CREATED)
        except CustomUser.DoesNotExist as e:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to create project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- FETCH PROJECTS ---------------------
class FetchProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.usertype == 'SuperAdmin':
            projects = Project.objects.all()
        elif user.usertype == 'Admin':
            projects = Project.objects.filter(created_by=user)
        else:
            projects = Project.objects.none()

        project_data = self.serialize_projects(projects)
        return Response({"projects": project_data}, status=status.HTTP_200_OK)

    def serialize_projects(self, projects):
        return [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,  
                "start_date": project.start_date,
                "deadline": project.deadline,
                "created_by": project.created_by.username,
                "teams": [
                        {
                            "id": team.id,
                            "name": team.name,
                            "account_managers": [
                                {"id": manager.id, "username": manager.username}
                                for manager in team.account_managers.all()
                            ],
                            "team_leader_search": {
                                "id": team.team_leader_search.id,
                                "username": team.team_leader_search.username
                            } if team.team_leader_search else None,
                            "team_leader_creative": {
                                "id": team.team_leader_creative.id,
                                "username": team.team_leader_creative.username
                            } if team.team_leader_creative else None,
                            "team_leader_development": {
                                "id": team.team_leader_development.id,
                                "username": team.team_leader_development.username
                            } if team.team_leader_development else None,
                            "subteams": [
                                {
                                    "id": member.id,
                                    "username": member.username,
                                    "subteam": member.subteam,
                                } for member in team.members.all()
                            ]
                        }
                        for team in project.teams_assigned.all()  
                ],
            }
            for project in projects
        ]

# --------------------- FETCH ASSIGNED PROJECTS ---------------------
class FetchAssignedProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.usertype in ['Admin', 'TeamLeader', 'User']:
            if user.usertype == 'Admin':
                created_projects = Project.objects.filter(created_by=user)
                assigned_projects = Project.objects.filter(teams_assigned__account_managers__id=user.id)
                projects = (created_projects | assigned_projects).distinct()  
            elif user.usertype == 'TeamLeader':
                teams = Team.objects.filter(
                    team_leader_search=user
                ) | Team.objects.filter(
                    team_leader_development=user
                ) | Team.objects.filter(
                    team_leader_creative=user
                )
                projects = Project.objects.filter(teams_assigned__in=teams).distinct()
            elif user.usertype == 'User':
                teams = Team.objects.filter(members=user)
                projects = Project.objects.filter(teams_assigned__in=teams).distinct()
            project_data = [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "start_date": project.start_date,
                    "deadline": project.deadline,
                    "created_by": project.created_by.username,
                    "teams": [
                        {
                            "id": team.id,
                            "name": team.name,
                            "account_managers": [
                                {"id": manager.id, "username": manager.username}
                                for manager in team.account_managers.all()
                            ],
                            "team_leader_search": {
                                "id": team.team_leader_search.id,
                                "username": team.team_leader_search.username
                            } if team.team_leader_search else None,
                            "team_leader_creative": {
                                "id": team.team_leader_creative.id,
                                "username": team.team_leader_creative.username
                            } if team.team_leader_creative else None,
                            "team_leader_development": {
                                "id": team.team_leader_development.id,
                                "username": team.team_leader_development.username
                            } if team.team_leader_development else None,
                            "subteams": [
                                {
                                    "id": member.id,
                                    "username": member.username,
                                    "subteam": member.subteam,
                                    "team":member.team
                                } for member in team.members.all()
                            ]
                        }
                        for team in project.teams_assigned.all()  
                    ],
                }
                for project in projects
            ]
            return Response({"projects": project_data}, status=status.HTTP_200_OK)

        return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

# --------------------- EDIT PROJECT ---------------------
class EditProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, project_id, *args, **kwargs):
        data = request.data
        try:
            project = Project.objects.get(id=project_id)
            project.name = data.get('name', project.name)
            project.description = data.get('description', project.description)
            project.status = data.get('status', project.status)
            project.start_date = data.get('start_date', project.start_date)
            project.deadline = data.get('deadline', project.deadline)
            project.save()

            return Response({
                "message": "Project updated successfully",
                "status": "success",
                "project_id": project.id,
            }, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- DELETE PROJECT ---------------------
class DeleteProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, project_id, *args, **kwargs):
        try:
            user = request.user
            project = Project.objects.get(id=project_id)
            users_to_notify = set()
            teams = project.teams.all()
    
            for team in teams:
                members = team.members.all()
                users_to_notify.update(members)

                # Handle account_managers (ManyToManyField)
                for manager in team.account_managers.all():
                    users_to_notify.add(manager)

                # Handle team leads (ForeignKey fields)
                for role in ["team_leader_search", "team_leader_development", "team_leader_creative"]:
                    role_user = getattr(team, role, None)
                    if role_user:
                        users_to_notify.add(role_user)

            for user in users_to_notify:
                message = f"The project <b>{project.name}</b> has been deleted. You have been removed from this project."
                send_telegram_message(user.chat_id, message)
                notification  = Notification.objects.create(user=user, message=message)
                send_notification_to_user(notification)
                
            project.delete()
            return Response(
                {"message": "Project deleted successfully", "status": "success"},
                status=status.HTTP_200_OK,
            )

        except Project.DoesNotExist:
            return Response(
                {"message": "Project not found", "status": "failure"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {"message": "Failed to delete project", "status": "failure"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


"""
 Un used
"""
# Fetch Team Leaders for a Specific Project and Team
class FetchProjectTeamLeadersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id, *args, **kwargs):
        team = request.query_params.get('team')
        if team not in ['Search', 'Creative', 'Development']:
            return Response({"message": "Invalid team"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            team_leaders = []
            if team == 'Search' and project.team and project.team.team_leader_search:
                team_leaders.append(project.team.team_leader_search)
            elif team == 'Creative' and project.team and project.team.team_leader_creative:
                team_leaders.append(project.team.team_leader_creative)
            elif team == 'Development' and project.team and project.team.team_leader_development:
                team_leaders.append(project.team.team_leader_development)

            team_leader_data = [
                {"id": leader.id, "username": leader.username}
                for leader in team_leaders
            ]
            return Response({"team_leaders": team_leader_data}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
