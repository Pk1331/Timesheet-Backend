from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import CustomUser, Task, Project,Notification
from rest_framework.response import Response
from timesheet_app.utils import send_telegram_message
from timesheet_app.notification_ws import send_notification_to_user
from django.db.models import Q
import logging
logger  = logging.getLogger(__name__)


# --------------------- CREATE TASKS---------------------
class CreateTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        title = data.get('title')
        description = data.get('description')
        project_id = data.get('project')
        task_status = data.get('status', 'To Do')
        priority = data.get('priority', 'Medium')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        created_by = request.user
        assigned_to_id = data.get('assigned_to')

        try:
            project = Project.objects.get(id=project_id)
            assigned_to = CustomUser.objects.get(id=assigned_to_id) if assigned_to_id else None

            if created_by.usertype == 'SuperAdmin':
                valid_users = []

                for team in project.teams.all():
                    valid_users.extend(team.account_managers.all())
                    if team.team_leader_search:
                        valid_users.append(team.team_leader_search)
                    if team.team_leader_development:
                        valid_users.append(team.team_leader_development)
                    if team.team_leader_creative:
                        valid_users.append(team.team_leader_creative)
                    valid_users.extend(team.members.all())

                if assigned_to not in valid_users:
                    return Response(
                        {"message": "SuperAdmin can only assign tasks within the selected project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            elif created_by.usertype == 'Admin':
                valid_users = []

                for team in project.teams.all():
                    if team.team_leader_search:
                        valid_users.append(team.team_leader_search)
                    if team.team_leader_development:
                        valid_users.append(team.team_leader_development)
                    if team.team_leader_creative:
                        valid_users.append(team.team_leader_creative)
                    valid_users.extend(team.members.all())

                if assigned_to not in valid_users or assigned_to.usertype in ['Admin', 'SuperAdmin']:
                    return Response(
                        {"message": "Admin can assign tasks only to TeamLeaders or Users in the selected project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            elif created_by.usertype == 'TeamLeader':
                is_valid = False
                for team in project.teams.all():
                    if (
                        (team.team_leader_search == created_by and assigned_to in team.members.filter(team='Search')) or
                        (team.team_leader_development == created_by and assigned_to in team.members.filter(team='Development')) or
                        (team.team_leader_creative == created_by and assigned_to in team.members.filter(team='Creative'))
                    ):
                        is_valid = True
                        break

                if not is_valid:
                    return Response(
                        {"message": "TeamLeader can only assign tasks to their own team members"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Create task
            task = Task.objects.create(
                title=title,
                description=description,
                project=project,
                status=task_status,
                priority=priority,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by,
            )

            if created_by.usertype == 'SuperAdmin':
                task.superadmin_assigned_to = assigned_to
            elif created_by.usertype == 'Admin':
                task.admin_assigned_to = assigned_to
            elif created_by.usertype == 'TeamLeader':
                task.teamleader_assigned_to = assigned_to

            task.save()

            if assigned_to and assigned_to.chat_id:
                message = (
                    f"📢 <b>New Task Assigned</b>\n\n"
                    f"🔹 <b>Title:</b> {task.title}\n"
                    f"🏗 <b>Project:</b> {task.project.name}\n"
                    f"📝 <b>Description:</b> {task.description}\n"
                    f"📌 <b>Priority:</b> {task.priority}\n"
                    f"📅 <b>Deadline:</b> {task.end_date}\n"
                    f"👤 <b>Assigned By:</b> {created_by.username}"
                )
                send_telegram_message(assigned_to.chat_id, message)
                notification = Notification.objects.create(user=assigned_to, message=message)
                send_notification_to_user(notification)

            return Response(
                {"message": "Task created successfully", "task_id": task.id},
                status=status.HTTP_201_CREATED,
            )

        except Project.DoesNotExist:
            return Response({"message": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"message": "Assigned user not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --------------------- FETCH TASKS---------------------
class FetchTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        created_tasks = Task.objects.filter(created_by=user)
        assigned_tasks = Task.objects.filter(
            Q(superadmin_assigned_to=user) |
            Q(admin_assigned_to=user) |
            Q(teamleader_assigned_to=user) 
        )
        def serialize_task(task):
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date,
                "end_date": task.end_date,
               "project": {
                    "id": task.project.id,
                    "name": task.project.name  
                } if task.project else None,
                "assigned_to": {
                    "superadmin": {
                        "id": task.superadmin_assigned_to.id,
                        "username": task.superadmin_assigned_to.username
                    } if task.superadmin_assigned_to else None,
                    "admin": {
                        "id": task.admin_assigned_to.id,
                        "username": task.admin_assigned_to.username
                    } if task.admin_assigned_to else None,
                    "teamleader": {
                        "id": task.teamleader_assigned_to.id,
                        "username": task.teamleader_assigned_to.username
                    } if task.teamleader_assigned_to else None,
                },
                "created_by": {
                    "id": task.created_by.id,
                    "username": task.created_by.username,
                    "usertype":task.created_by.usertype
                }
            }

        return Response(
            {
                "created_tasks": [serialize_task(task) for task in created_tasks],
                "assigned_tasks": [serialize_task(task) for task in assigned_tasks],
            },
            status=status.HTTP_200_OK,
        )

# --------------------- EDIT TASKS---------------------
class EditTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, task_id, *args, **kwargs):
        data = request.data
        try:
            task = Task.objects.get(id=task_id)
            logger.debug(f"Task found: {task.id}, Title: {task.title}")
            old_assigned_to = (
                task.superadmin_assigned_to
                or task.admin_assigned_to
                or task.teamleader_assigned_to
            )  
            logger.debug(f"Old Assigned To: {old_assigned_to.username if old_assigned_to else None}")
            
            task.title = data.get("title", task.title)
            task.description = data.get("description", task.description)
            task.status = data.get("status", task.status)
            task.priority = data.get("priority", task.priority)
            task.start_date = data.get("start_date", task.start_date)
            task.end_date = data.get("end_date", task.end_date)
            logger.debug(f"Updated Task: {task.title}, Status: {task.status}, Priority: {task.priority}")
            
            new_assigned_id = data.get("assigned_to")
            new_assigned_to = None

            if new_assigned_id:
                try:
                    new_assigned_to = CustomUser.objects.get(id=new_assigned_id)
                    logger.debug(f"New Assigned To: {new_assigned_to.username}")
                except CustomUser.DoesNotExist:
                    logger.error(f"Assigned user with ID {new_assigned_id} not found.")
                    return Response(
                        {"message": "Assigned user not found", "status": "failure"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            created_by = request.user
            logger.debug(f"Request made by: {created_by.username} ({created_by.usertype})")
            if created_by.usertype == "SuperAdmin" and new_assigned_to and new_assigned_to.usertype != "Admin":
                logger.warning(f"SuperAdmin {created_by.username} tried to assign task to a non-Admin user.")
                return Response(
                    {"message": "SuperAdmin can only assign tasks to Admins"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if created_by.usertype == "Admin" and new_assigned_to and new_assigned_to.usertype != "TeamLeader":
                logger.warning(f"Admin {created_by.username} tried to assign task to a non-TeamLeader user.")
                return Response(
                    {"message": "Admin can only assign tasks to TeamLeaders"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if created_by.usertype == "TeamLeader" and new_assigned_to and new_assigned_to.usertype != "User":
                logger.warning(f"TeamLeader {created_by.username} tried to assign task to a non-User.")
                return Response(
                    {"message": "TeamLeader can only assign tasks to Users"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_assigned_to:
                if created_by.usertype == "SuperAdmin":
                    task.superadmin_assigned_to = new_assigned_to
                elif created_by.usertype == "Admin":
                    task.admin_assigned_to = new_assigned_to
                elif created_by.usertype == "TeamLeader":
                    task.teamleader_assigned_to = new_assigned_to
            task.save()
            logger.debug(f"Task updated successfully, Assigned To: {new_assigned_to.username if new_assigned_to else None}")
            if old_assigned_to and old_assigned_to != new_assigned_to:
                if old_assigned_to.chat_id:
                    message_old = (
                        f"⚠️ <b>Task Unassigned</b>\n\n"
                        f"🔹 <b>Title:</b> {task.title}\n"
                        f"❌ <b>Removed By:</b> {request.user.username}\n"
                        f"📅 <b>Project:</b> {task.project.name}\n\n"
                        f"You have been unassigned from this task."
                    )
                    send_telegram_message(old_assigned_to.chat_id, message_old)
                    notification = Notification.objects.create(user=old_assigned_to, message=message_old)
                    send_notification_to_user(notification)

            if new_assigned_to and old_assigned_to != new_assigned_to:
                if new_assigned_to.chat_id:
                    message_new = (
                        f"✅ <b>New Task Assigned</b>\n\n"
                        f"🔹 <b>Title:</b> {task.title}\n"
                        f"📅 <b>Project:</b> {task.project.name}\n"
                        f"🔄 <b>Assigned By:</b> {request.user.username}\n\n"
                        f"Please check your task list for details."
                    )
                    send_telegram_message(new_assigned_to.chat_id, message_new)
                    notification = Notification.objects.create(user=new_assigned_to, message=message_new)
                    send_notification_to_user(notification)

            return Response(
                {
                    "message": "Task updated successfully",
                    "status": "success",
                    "task_id": task.id,
                },
                status=status.HTTP_200_OK,
            )

        except Task.DoesNotExist:
            logger.error(f"Task with ID {task_id} not found.")
            return Response(
                {"message": "Task not found", "status": "failure"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            return Response(
                {"message": f"Failed to update task: {str(e)}", "status": "failure"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# --------------------- DELETE TASKS---------------------
class DeleteTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, task_id, *args, **kwargs):
        try:
            task = Task.objects.get(id=task_id)
            assigned_user = (
                task.superadmin_assigned_to
                or task.admin_assigned_to
                or task.teamleader_assigned_to
            )
            if assigned_user and assigned_user.chat_id:
                message = (
                    f"⚠️ <b>Task Deleted</b>\n\n"
                    f"🔹 <b>Title:</b> {task.title}\n"
                    f"❌ <b>Deleted By:</b> {request.user.username}\n"
                    f"📅 <b>Project:</b> {task.project.name}\n\n"
                    f"Please contact {request.user.username} for further details."
                )
                send_telegram_message(assigned_user.chat_id, message)  
                notification = Notification.objects.create(user=assigned_user, message=message)
                send_notification_to_user(notification)

            task.delete()
            return Response(
                {"message": "Task deleted successfully", "status": "success"},
                status=status.HTTP_200_OK
            )

        except Task.DoesNotExist:
            return Response(
                {"message": "Task not found", "status": "failure"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": f"Failed to delete task: {str(e)}", "status": "failure"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --------------------- ASSIGN TASKS---------------------
class AssignTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id, *args, **kwargs):
        try:
            task = Task.objects.get(id=task_id)
            assigned_to_id = request.data.get("assigned_to")
            assigned_to = CustomUser.objects.get(id=assigned_to_id)

            old_assigned_to = task.admin_assigned_to or task.teamleader_assigned_to

            if request.user.usertype == "Admin":
                if assigned_to.usertype != "TeamLeader":
                    return Response(
                        {"message": "Admin can only assign tasks to TeamLeaders", "status": "failure"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                task.admin_assigned_to = assigned_to  
            elif request.user.usertype == "TeamLeader":
                if assigned_to.usertype != "User":
                    return Response(
                        {"message": "TeamLeader can only assign tasks to Users", "status": "failure"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                task.teamleader_assigned_to = assigned_to  

            else:
                return Response(
                    {"message": "Invalid role for task assignment", "status": "failure"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            task.save()

            assigned_by_text = request.user.username if request.user else "N/A"

            if old_assigned_to and old_assigned_to != assigned_to:
                if old_assigned_to.chat_id:
                    message_old = (
                        f"⚠️ <b>Task Unassigned</b>\n\n"
                        f"🔹 <b>Title:</b> {task.title}\n"
                        f"❌ <b>Removed By:</b> {assigned_by_text}\n"
                        f"📅 <b>Project:</b> {task.project.name}\n\n"
                        f"You have been unassigned from this task."
                    )
                    send_telegram_message(old_assigned_to.chat_id, message_old)
                    notification = Notification.objects.create(user=old_assigned_to, message=message_old)
                    send_notification_to_user(notification)

            if assigned_to and old_assigned_to != assigned_to:
                if assigned_to.chat_id:
                    message_new = (
                        f"✅ <b>New Task Assigned</b>\n\n"
                        f"🔹 <b>Title:</b> {task.title}\n"
                        f"🏗 <b>Project:</b> {task.project.name}\n"
                        f"📝 <b>Description:</b> {task.description}\n"
                        f"📌 <b>Priority:</b> {task.priority}\n"
                        f"📅 <b>Deadline:</b> <span style='color:red;'>{task.end_date}</span>\n"
                        f"👤 <b>Assigned By:</b> {assigned_by_text}"
                    )
                    send_telegram_message(assigned_to.chat_id, message_new)
                    notification = Notification.objects.create(user=assigned_to, message=message_new)
                    send_notification_to_user(notification)

            return Response(
                {"message": "Task assigned successfully", "status": "success"},
                status=status.HTTP_200_OK,
            )

        except Task.DoesNotExist:
            return Response({"message": "Task not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"message": "Assigned user not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"message": f"Failed to assign task: {str(e)}", "status": "failure"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

