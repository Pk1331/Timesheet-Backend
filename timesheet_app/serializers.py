from rest_framework import serializers
from .models import CustomUser, Timesheet,  Project, Team, Department,TimesheetReview,Notification


# CustomUserSerializer is used to serialize the CustomUser model
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'usertype', 'team', 'subteam', 'chat_id']

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']
        

class TimesheetSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Project.objects.all()
    )
    department = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Department.objects.all()
    )
    submitted_to = serializers.SlugRelatedField(
        slug_field='username',
        queryset=CustomUser.objects.all(),
        allow_null=True,
        required=False
    )
    rejection_feedback = serializers.SerializerMethodField()
    created_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = Timesheet
        fields = [
            'id',
            'date',
            'project',
            'task',
            'description',
            'department',
            'hours',
            'status',
            'submitted_to',
            'submitted_at',
            'submission_date_group',
            'created_by',
            'rejection_feedback', 
        ]
        read_only_fields = ['status', 'submitted_at', 'submission_date_group', 'created_by']
        
    def get_rejection_feedback(self, obj):
        if obj.status == "Rejected":
            review = TimesheetReview.objects.filter(
                reviewed_user=obj.created_by,
                review_date=obj.date,
                action="reject"
            ).first()
            return review.feedback if review else ""
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data) 
   
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read', 'created_at']