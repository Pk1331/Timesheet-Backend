from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import CustomUser, Team, Project,Notification
from rest_framework.response import Response
from timesheet_app.utils import send_telegram_message
from django.db.models import Q
from collections import defaultdict
from timesheet_app.notification_ws import send_notification_to_user



# --------------------- CREATE TEAMS---------------------
class CreateTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        name = data.get('name')
        description = data.get('description')
        account_manager_ids = data.get('account_manager_ids', [])

        if isinstance(account_manager_ids, int):
            account_manager_ids = [account_manager_ids]
        team_leader_search_id = data.get('team_leader_search')
        team_leader_development_id = data.get('team_leader_development')
        team_leader_creative_id = data.get('team_leader_creative')
        team = data.get('team')
        subteam = data.get('subteam')
        member_ids = data.get('member_ids', [])
        project_id = data.get('project_id')
        created_by = request.user

        try:
            account_managers = CustomUser.objects.filter(id__in=account_manager_ids)
            if not account_managers.exists():
                return Response({"message": "Invalid Account Manager(s)", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            team_leader_search = CustomUser.objects.get(id=team_leader_search_id) if team_leader_search_id else None
            team_leader_development = CustomUser.objects.get(id=team_leader_development_id) if team_leader_development_id else None
            team_leader_creative = CustomUser.objects.get(id=team_leader_creative_id) if team_leader_creative_id else None
            project = Project.objects.filter(id=project_id).first()
            if not project:
                return Response({"message": "Invalid Project ID", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            team_instance = Team.objects.create(
                name=name,
                description=description,
                team_leader_search=team_leader_search,
                team_leader_development=team_leader_development,
                team_leader_creative=team_leader_creative,
                team=team,
                subteam=subteam,
                created_by=created_by,
            )

            team_instance.account_managers.set(account_managers)
            team_instance.members.set(member_ids)
            team_instance.projects.set([project])
            
            project.teams.add(team_instance)
            team_instance.save()

            # Notifications
            team_members = list(team_instance.members.all())
            users_to_notify = set(team_members + list(account_managers))
            if team_leader_search:
                users_to_notify.add(team_leader_search)
            if team_leader_development:
                users_to_notify.add(team_leader_development)
            if team_leader_creative:
                users_to_notify.add(team_leader_creative)
                
            users_to_notify.discard(created_by)
            for user in users_to_notify:
                message = f"You have been added to the project: <b>{project.name}</b> as part of team <b>{team_instance.name}</b>."
                send_telegram_message(user.chat_id, message)
                notification = Notification.objects.create(user=user, message=message)
                send_notification_to_user(notification)

            return Response({"message": "Team created successfully", "status": "success"}, status=status.HTTP_201_CREATED)

        except CustomUser.DoesNotExist as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)
        except Project.DoesNotExist as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- FETCH TEAMS---------------------
class FetchTeamsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # SuperAdmin gets all teams
        if user.usertype == "SuperAdmin":
            teams = Team.objects.all()

        # Other users get related teams
        elif user.usertype in ["Admin", "TeamLeader", "User"]:
            teams = Team.objects.filter(
                Q(account_managers=user) |
                Q(team_leader_search=user) |
                Q(team_leader_development=user) |
                Q(team_leader_creative=user) |
                Q(members=user)
            ).distinct()

        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

        if not teams.exists():
            return Response({"teams": []}, status=status.HTTP_200_OK)


        team_data = []
        for team in teams:
            subteam_dict = defaultdict(list)
            all_members = set()

            # Handle team members
            for member in team.members.all():
                subteam_dict[member.subteam or "Uncategorized"].append({
                    "id": member.id,
                    "username": member.username
                })
                all_members.add(member.id)

            # Handle account managers
            account_managers = [
                {"id": manager.id, "username": manager.username}
                for manager in team.account_managers.all()
            ]
            all_members.update(manager["id"] for manager in account_managers)

            # Handle team leaders
            def get_team_leader(leader):
                return {"id": leader.id, "username": leader.username} if leader else None

            team_leader_search = get_team_leader(team.team_leader_search)
            team_leader_development = get_team_leader(team.team_leader_development)
            team_leader_creative = get_team_leader(team.team_leader_creative)

            for leader in [team_leader_search, team_leader_development, team_leader_creative]:
                if leader:
                    all_members.add(leader["id"])

            # Count total unique people in the team
            total_members_count = len(all_members)

            # Fetch projects
            projects = [
                {"id": project.id, "name": project.name}
                for project in team.projects.all()
            ]

            # Build response data
            team_data.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "account_managers": account_managers,
                "team_leader_search": team_leader_search,
                "team_leader_development": team_leader_development,
                "team_leader_creative": team_leader_creative,
                "subteams": [
                    {"subteam": subteam, "members": members}
                    for subteam, members in subteam_dict.items()
                ],
                "created_by": {
                    "id": team.created_by.id,
                    "username": team.created_by.username
                } if team.created_by else None,
                "projects": projects,
                "total_members": total_members_count,
                "has_members": total_members_count > 0  
            })
        return Response({"teams": team_data}, status=status.HTTP_200_OK)
    
# --------------------- FETCH MEMBERS--------------------
class GetAssignedTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.usertype != 'TeamLeader':
            return Response({"message": "User is not a Team Leader", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

        try:
           
            team = Team.objects.filter(
                Q(team_leader_search=user) |
                Q(team_leader_development=user) |
                Q(team_leader_creative=user)
            ).first()

            if not team:
                return Response({"message": "No assigned team found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

            # Determine which subteam the leader manages
            if team.team_leader_search == user:
                team_type = "Search"
            elif team.team_leader_development == user:
                team_type = "Development"
            elif team.team_leader_creative == user:
                team_type = "Creative"
            else:
                team_type = None

            if not team_type:
                return Response({"message": "User is not assigned to a specific subteam", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            
            assigned_team_members = team.members.filter(subteam=team_type).values("id", "username")

            return Response({
                "team": {
                    "team_type": team_type,
                    "members": list(assigned_team_members)  
                },
                "status": "success"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- EDIT TEAMS---------------------
class EditTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, team_id, *args, **kwargs):
        data = request.data
        try:
            team = Team.objects.get(id=team_id)
    
            # Old data for comparison
            old_members = set(team.members.all())
            old_account_managers = set(team.account_managers.all())
            old_team_leaders = {
                "search": team.team_leader_search,
                "development": team.team_leader_development,
                "creative": team.team_leader_creative,
            }
            old_projects = list(team.projects.all())
            old_project = old_projects[0] if old_projects else None
        
            # New data
            name = data.get("name")
            description = data.get("description")
            account_manager_ids = data.get("account_manager_ids", [])
            team_leader_search_id = data.get("team_leader_search")
            team_leader_development_id = data.get("team_leader_development")
            team_leader_creative_id = data.get("team_leader_creative")
            team_type = data.get("team")
            subteam = data.get("subteam")
            member_ids = data.get("member_ids", [])
            project_id = data.get("project_id")

            if isinstance(account_manager_ids, int):
                account_manager_ids = [account_manager_ids]

            # Update basic fields
            team.name = name
            team.description = description
            team.team = team_type
            team.subteam = subteam
            team.team_leader_search = (
                CustomUser.objects.get(id=team_leader_search_id) if team_leader_search_id else None
            )
            team.team_leader_development = (
                CustomUser.objects.get(id=team_leader_development_id) if team_leader_development_id else None
            )
            team.team_leader_creative = (
                CustomUser.objects.get(id=team_leader_creative_id) if team_leader_creative_id else None
            )
            team.save()
           

            # Set members and managers
            team.members.set(member_ids)
            team.account_managers.set(account_manager_ids)
           

            # Handle project assignment
            if project_id:
                new_project = Project.objects.filter(id=project_id).first()
                if not new_project:
                    return Response(
                        {"message": "Invalid project ID", "status": "failure"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                team.projects.clear()
                team.projects.add(new_project)
                new_project.teams.add(team)
                team.save()
            else:
                new_project = None
                team.projects.clear()


            # Determine if project changed
            project_changed = old_project != new_project
            # Collect current team members
            current_members = set(team.members.all())
            current_ams = set(team.account_managers.all())
            current_tls = set(
                filter(
                    None,
                    [
                        team.team_leader_search,
                        team.team_leader_development,
                        team.team_leader_creative,
                    ],
                )
            )

            if project_changed:
                # Notify everyone if project changed
                users_to_notify = current_members.union(current_ams).union(current_tls)
            else:
                # Notify only new additions
                new_members = current_members - old_members
                new_ams = current_ams - old_account_managers
                new_tls = set()
                if team.team_leader_search and team.team_leader_search != old_team_leaders.get("search"):
                    new_tls.add(team.team_leader_search)
                if team.team_leader_development and team.team_leader_development != old_team_leaders.get("development"):
                    new_tls.add(team.team_leader_development)
                if team.team_leader_creative and team.team_leader_creative != old_team_leaders.get("creative"):
                    new_tls.add(team.team_leader_creative)

                users_to_notify = new_members.union(new_ams).union(new_tls)

            users_to_notify.discard(request.user)
            

            for user in users_to_notify:
                if new_project:
                    message = f"You have been assigned to the project: <b>{new_project.name}</b> in team <b>{team.name}</b>."
                else:
                    message = f"You have been assigned to team <b>{team.name}</b>."
                send_telegram_message(user.chat_id, message)
                notification = Notification.objects.create(user=user, message=message)
                send_notification_to_user(notification)

            return Response({"message": "Team updated successfully", "status": "success"}, status=status.HTTP_200_OK)

        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
           
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- DELETE TEAMS---------------------  
class DeleteTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, team_id, *args, **kwargs):
        try:
    
            team = Team.objects.get(id=team_id)
            projects_assigned = team.projects.all() 
            users_to_notify = list(team.members.all()) + list(team.account_managers.all())

            if team.team_leader_search:
                users_to_notify.append(team.team_leader_search)
            if team.team_leader_development:
                users_to_notify.append(team.team_leader_development)
            if team.team_leader_creative:
                users_to_notify.append(team.team_leader_creative)

            # Notify users if the team is associated with any projects
            if projects_assigned.exists():
                for project in projects_assigned:
                    for user in users_to_notify:
                        try:
                            message = f"The team <b>{team.name}</b> has been deleted. You have been removed from the project: <b>{project.name}</b>"
                            send_telegram_message(user.chat_id, message)
                            notification = Notification.objects.create(user=user, message=message)
                            send_notification_to_user(notification)
                        except Exception as notify_error:
                            print(f"Failed to send notification to {user.username}: {notify_error}")
                            
            team.projects.clear()
            # Delete the team
            team.delete()

            return Response({"message": "Team deleted successfully", "status": "success"}, status=status.HTTP_200_OK)

        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"message": f"Failed to delete team: {str(e)}", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


"""
                            unused
"""

# Fetch Users for Submitted To Dropdown
class FetchSubmittedToUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'User':
            users = CustomUser.objects.filter(usertype='TeamLeader', team=user.team)
        elif user.usertype == 'TeamLeader':
            users = CustomUser.objects.filter(usertype='Admin')
        elif user.usertype == 'Admin':
            users = CustomUser.objects.filter(usertype='SuperAdmin')
        else:
            users = CustomUser.objects.none()

        user_data = [{"id": user.id, "username": user.username} for user in users]
        return Response({"users": user_data}, status=status.HTTP_200_OK)

