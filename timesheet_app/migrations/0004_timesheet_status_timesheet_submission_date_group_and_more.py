# Generated by Django 4.2.20 on 2025-05-16 09:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet_app', '0003_department_remove_timesheet_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='timesheet',
            name='status',
            field=models.CharField(choices=[('Draft', 'Draft'), ('Submitted', 'Submitted for Review'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Draft', max_length=20),
        ),
        migrations.AddField(
            model_name='timesheet',
            name='submission_date_group',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='timesheet',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timesheets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='timesheet_app.department'),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='timesheet_app.project'),
        ),
        migrations.AlterField(
            model_name='timesheet',
            name='submitted_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_timesheets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='TimesheetTable',
        ),
    ]
