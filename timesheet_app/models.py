from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password) 
        else:
            user.set_password(self.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('usertype', 'SuperAdmin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    USERTYPE_CHOICES = [
        ('SuperAdmin', 'SuperAdmin'),
        ('Admin', 'Admin'),
        ('TeamLeader', 'TeamLeader'),
        ('User', 'User'),
    ]

    TEAM_CHOICES = [
        ('Search', 'Search Team'),
        ('Creative', 'Creative Team'),
        ('Development', 'Development Team'),
    ]

    SUBTEAM_CHOICES = [
        ('SEO', 'SEO'),
        ('SMO', 'SMO'),
        ('SEM', 'SEM'),
        ('Design', 'Design Team'),
        ('Content Writing', 'Content Writing'),
        ('Python Development', 'Python Development'),
        ('Web Development', 'Web Development'),
    ]

    usertype = models.CharField(max_length=50, choices=USERTYPE_CHOICES)
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    team = models.CharField(max_length=50, choices=TEAM_CHOICES, null=True, blank=True)
    subteam = models.CharField(max_length=50, choices=SUBTEAM_CHOICES, null=True, blank=True)
    chat_id = models.CharField(max_length=50, default='1234567890')

    objects = CustomUserManager()
    
    class Meta:
        verbose_name = "System User"
        verbose_name_plural = "System Users"

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  

    def __str__(self):
        return self.firstname

# Admin User
class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'Admin':
            raise ValueError('Cannot assign Admin role to non-Admin user.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# Team Leader User  
class TeamLeader(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'TeamLeader':
            raise ValueError('Cannot assign TeamLeader role to non-TeamLeader user.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# User
class User(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'User':
            raise ValueError('Cannot assign User role to non-User.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# Project Model
class Project(models.Model):
    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Upcoming', 'Upcoming'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    start_date = models.DateField()
    deadline = models.DateField()
    created_by = models.ForeignKey(
        CustomUser,
        related_name='created_projects',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    teams = models.ManyToManyField('Team', related_name='projects_assigned',blank=True)

    def __str__(self):
        return self.name

# Team Model 
class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    account_managers = models.ManyToManyField(CustomUser, related_name='managed_teams')

    team_leader_search = models.ForeignKey(
        CustomUser,
        related_name='led_search_teams',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    team_leader_development = models.ForeignKey(
        CustomUser,
        related_name='led_development_teams',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    team_leader_creative = models.ForeignKey(
        CustomUser,
        related_name='led_creative_teams',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    team = models.CharField(max_length=50, choices=CustomUser.TEAM_CHOICES,blank=True)
    subteam = models.CharField(max_length=50, choices=CustomUser.SUBTEAM_CHOICES, null=True, blank=True)
    members = models.ManyToManyField(CustomUser, related_name='teams',blank=True)

    created_by = models.ForeignKey(
        CustomUser,
        related_name='created_teams',
        on_delete=models.PROTECT  # or models.SET_NULL, null=True, blank=True if you prefer
    )

    projects = models.ManyToManyField(Project, related_name='teams_assigned',blank=True)

    def __str__(self):
        return self.name
  
# Task Model
class Task(models.Model):
    STATUS_CHOICES = [
        ('To Do', 'To Do'),
        ('In Progress', 'In Progress'),
        ('Review', 'Review'),
        ('Completed', 'Completed'),
    ]

    project = models.ForeignKey(
        Project, related_name='tasks', on_delete=models.CASCADE
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='To Do')
    priority = models.CharField(max_length=50, default='Medium')
    start_date = models.DateField()
    end_date = models.DateField()
    
    created_by = models.ForeignKey(
        CustomUser, related_name='created_tasks',
        on_delete=models.PROTECT  
    )

    superadmin_assigned_to = models.ForeignKey(
        CustomUser, related_name='superadmin_tasks',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    admin_assigned_to = models.ForeignKey(
        CustomUser, related_name='admin_tasks',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    teamleader_assigned_to = models.ForeignKey(
        CustomUser, related_name='teamleader_tasks',
        on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.title

    def assign_task(self, assigned_by, assigned_to):
        if assigned_by.usertype == 'SuperAdmin':
            self.superadmin_assigned_to = assigned_to
        elif assigned_by.usertype == 'Admin':
            self.admin_assigned_to = assigned_to
        elif assigned_by.usertype == 'TeamLeader':
            self.teamleader_assigned_to = assigned_to
        self.save()


# Department Model
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Timesheet Model
class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Submitted', 'Submitted for Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    task = models.CharField(max_length=255, blank=True)  
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, related_name='timesheets', on_delete=models.CASCADE)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    hours = models.DecimalField(max_digits=5, decimal_places=1)
    submitted_to = models.ForeignKey(CustomUser, null=True, blank=True, related_name='review_timesheets', on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    submission_date_group = models.DateField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.created_by.username} - {self.task} on {self.date}"


# TimesheetReview Model
class TimesheetReview(models.Model):
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reviewed_timesheets"
    )
    reviewed_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="timesheet_reviews"
    )
    review_date = models.DateField()
    action = models.CharField(
        max_length=10,
        choices=[("approve", "Approve"), ("reject", "Reject")]
    )
    feedback = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reviewed_user", "review_date")

    def __str__(self):
        return f"{self.reviewed_user.username} - {self.review_date} - {self.action}"



# Notification
class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
         return f"Notification for {self.user.username} {self.created_at}"

    
    
# Signals to automatically create role-specific models
@receiver(post_save, sender=CustomUser)
def create_role_specific_model(sender, instance, created, **kwargs):
    if created:
        if instance.usertype == 'Admin':
            Admin.objects.create(user=instance)
        elif instance.usertype == 'TeamLeader':
            TeamLeader.objects.create(user=instance)
        elif instance.usertype == 'User':
            User.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_role_specific_model(sender, instance, **kwargs):
    if instance.usertype == 'Admin' and hasattr(instance, 'admin'):
        instance.admin.save()
    elif instance.usertype == 'TeamLeader' and hasattr(instance, 'teamleader'):
        instance.teamleader.save()
    elif instance.usertype == 'User' and hasattr(instance, 'user'):
        instance.user.save()




