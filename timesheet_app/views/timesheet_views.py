from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import Timesheet,Department,TimesheetReview,Notification
from timesheet_app.serializers import TimesheetSerializer,DepartmentSerializer
from rest_framework.response import Response
from timesheet_app.utils import send_telegram_message
from django.utils.dateparse import parse_date
from datetime import date,datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
from timesheet_app.notification_ws import send_notification_to_user



"""
                                Department Views
"""
# --------------------- FETCH DEPARTMENTS ---------------------
class FetchDepartmentsView(APIView):
    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)
        return Response({'departments': serializer.data}, status=status.HTTP_200_OK)

# --------------------- CREATE DEPARTMENT ---------------------
class CreateDepartmentView(APIView):
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Department added successfully', 'department': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --------------------- UPDATE DEPARTMENT ---------------------
class UpdateDepartmentView(APIView):
    def patch(self, request, pk):
        try:
            department = Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Department renamed successfully', 'department': serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --------------------- DELETE DEPARTMENT ---------------------
class DeleteDepartmentView(APIView):
    def delete(self, request, pk):
        try:
            department = Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

        department.delete()
        return Response({'message': 'Department deleted successfully'}, status=status.HTTP_200_OK)



"""
                                Timesheet  Views                             
"""

# --------------------- CREATE TIMESHEETS ---------------------
class CreateTimesheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        timesheets_data = request.data.get('timesheets', None)
        if not timesheets_data:
            
            return Response(
                {"status": "error", "message": "No timesheets provided under 'timesheets' key."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = TimesheetSerializer(
            data=timesheets_data,
            many=True,
            context={'request': request}
        )
        if serializer.is_valid():
            
            serializer.save()
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Timesheet table saved successfully!"
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": "error",
            "errors": serializer.errors,
            "message": "Failed to save timesheet table!"
        }, status=status.HTTP_400_BAD_REQUEST)

# --------------------- FETCH TIMESHEETS ---------------------
class TimesheetListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        date_str = request.query_params.get('date')

        if date_str:
            date_obj = parse_date(date_str)
            if not date_obj:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            date_obj = date.today()

        # Get all timesheets for the user and date
        timesheets = Timesheet.objects.filter(created_by=user, date=date_obj)
        serializer = TimesheetSerializer(timesheets, many=True)
        return Response({
            "status": "success",
            "timesheet_table": {
                "date": date_obj,
                "timesheets": serializer.data
            }
        }, status=status.HTTP_200_OK)

# --------------------- EDIT TIMESHEETS ---------------------
class EditTimesheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Remove 'id' parameter since you're updating multiple timesheets at once
    def put(self, request):  
        timesheets_data = request.data.get("timesheets", [])
        if not timesheets_data:
            return Response({
                "status": "error",
                "message": "No timesheets data provided!"
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_timesheets = []

        for item in timesheets_data:
            timesheet_id = item.get('id', None)
            if timesheet_id:
                timesheet = get_object_or_404(Timesheet, id=timesheet_id, created_by=request.user)
                serializer = TimesheetSerializer(timesheet, data=item, partial=True, context={'request': request})
            else:
                serializer = TimesheetSerializer(data=item, context={'request': request})

            if serializer.is_valid():
                serializer.save()
                updated_timesheets.append(serializer.data)
            else:
                return Response({
                    "status": "error",
                    "message": f"Error in timesheet: {serializer.errors}"
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "message": "Timesheet table updated successfully!",
            "data": updated_timesheets
        }, status=status.HTTP_200_OK)

# --------------------- DELETE TIMESHEETS ---------------------
class BulkDeleteTimesheetsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({
                "status": "error",
                "message": "No IDs provided."
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = Timesheet.objects.filter(id__in=ids, created_by=request.user).delete()

        return Response({
            "status": "success",
            "message": f"Deleted {deleted_count} timesheets."
        }, status=status.HTTP_200_OK)

# --------------------- SEND TIMESHEETS FOR REVIEW ---------------------
class SendTimesheetsForReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        timesheet_ids = request.data.get("timesheet_ids", [])

        if not timesheet_ids:
            return Response({"status": "error", "message": "No timesheet IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        updated = []
        notified_users = set()

        for ts_id in timesheet_ids:
            timesheet = get_object_or_404(Timesheet, id=ts_id, created_by=request.user)
            
           
            if not timesheet.submitted_to:
                continue  

            timesheet.status = "Submitted"
            timesheet.submitted_at = timezone.now()
            timesheet.save()
            updated.append(ts_id)

            admin = timesheet.submitted_to
            if admin.chat_id and admin.id not in notified_users:
                message = (
                    f"📝 {request.user.username} submitted a timesheet for {timesheet.project.name} "
                    f"on {timesheet.date}."
                )
                send_telegram_message(admin.chat_id, message)
                notification = Notification.objects.create(user=admin, message=message)
                send_notification_to_user(notification)
                
                
                notified_users.add(admin.id)

        return Response({
            "status": "success",
            "message": "Timesheets submitted for review and respective admins notified.",
            "updated_ids": updated
        }, status=status.HTTP_200_OK)

# --------------------- PENDING REVIEW TIMESHEETS LIST FOR ADMINS ---------------------
class TimesheetsPendingReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        admin = request.user

        if admin.usertype != 'Admin':
            return Response({"detail": "Only Admins can review timesheets."}, status=status.HTTP_403_FORBIDDEN)

        timesheets = Timesheet.objects.filter(
            submitted_to=admin,
            status='Submitted'
        ).select_related('created_by', 'project').order_by('-date', 'submitted_at')

        data = {}
        for ts in timesheets:
            date_str = ts.date.strftime('%Y-%m-%d')
            username = ts.created_by.username

            if date_str not in data:
                data[date_str] = {}

            if username not in data[date_str]:
                data[date_str][username] = []

            data[date_str][username].append({
                "id": ts.id,
                "date": ts.date.strftime('%Y-%m-%d'),
                "project": ts.project.name,
                "task": ts.task,
                "description": ts.description,
                "department": ts.department.name if ts.department else "",
                "hours": ts.hours,
                "status": ts.status,
                "submitted_at": ts.submitted_at,
            })

        return Response({"status": "success", "grouped_timesheets": data})

# --------------------- ADMIN REVIEW TIMESHEETS ---------------------
class AdminReviewTimesheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        timesheet_ids = request.data.get("timesheet_ids", [])
        action = request.data.get("action")
        feedback = request.data.get("feedback", "")

        if not timesheet_ids or action not in ["approve", "reject"]:
            return Response({"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch timesheets
        timesheets = Timesheet.objects.filter(id__in=timesheet_ids)
        if not timesheets:
            return Response({"error": "No matching timesheets found."}, status=status.HTTP_404_NOT_FOUND)

        # Assume all timesheets are for same user and date
        reviewed_user = timesheets.first().created_by
        review_date = timesheets.first().date

        # Update each timesheet
        for ts in timesheets:
            if action == "approve":
                ts.status = "Approved"
                ts.approved_at = timezone.now()
                ts.rejected_at = None
            else:
                ts.status = "Rejected"
                ts.rejected_at = timezone.now()
                ts.approved_at = None
            ts.save()

        # Save single review record
        TimesheetReview.objects.update_or_create(
            reviewed_user=reviewed_user,
            review_date=review_date,
            defaults={
                "reviewed_by": request.user,
                "action": action,
                "feedback": feedback if action == "reject" else ""
            }
        )

        # Notify user once
        if reviewed_user.chat_id:
            if action == "approve":
                msg = f"✅ Your timesheets for {review_date} have been approved by the {request.user}."
            else:
                msg = f"❌ Your timesheets for {review_date} were rejected by the {request.user}.\nFeedback: {feedback}"
            send_telegram_message(reviewed_user.chat_id, msg)
            notification  = Notification.objects.create(user=reviewed_user, message=msg)
            send_notification_to_user(notification)
            
            

        return Response({
            "status": "success",
            "message": f"Timesheets {action}d successfully.",
            "reviewed_user": reviewed_user.username,
            "date": str(review_date),
        })
     
     
# --------------------- APPROVED TIMESHEETS ---------------------
class ApprovedTimesheetsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.query_params.get('user')
        project = request.query_params.get('project')
        date_str = request.query_params.get('date')
        month_str = request.query_params.get('month')
        timesheets = Timesheet.objects.filter(status='Approved')

        if user:
            timesheets = timesheets.filter(created_by__id=user)

        if project:
            timesheets = timesheets.filter(project__id=project)

        if date_str:
            date_obj = parse_date(date_str)
            if not date_obj:
                return Response(
                    {"error": "Invalid date format, use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            timesheets = timesheets.filter(date=date_obj)

        elif month_str:
            try:
                month_date = datetime.strptime(month_str, "%Y-%m")
                timesheets = timesheets.filter(
                    date__year=month_date.year,
                    date__month=month_date.month
                )
            except ValueError:
                return Response(
                    {"error": "Invalid month format, use YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Order timesheets by date (ascending)
        timesheets = timesheets.order_by("date")

        serializer = TimesheetSerializer(timesheets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

