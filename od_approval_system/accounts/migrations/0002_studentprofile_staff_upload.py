# Generated for staff-uploaded student credential enforcement.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='staff_uploaded_login',
            field=models.BooleanField(default=False, help_text='Students can login only after faculty/dean/admin uploads or authorizes their credentials.'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_student_profiles', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='uploaded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
