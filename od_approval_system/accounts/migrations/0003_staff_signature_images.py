# Generated for digital signature support on OD letters.
from django.db import migrations, models
import accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_studentprofile_staff_upload'),
    ]

    operations = [
        migrations.AddField(
            model_name='deanprofile',
            name='signature_image',
            field=models.FileField(blank=True, help_text='Digital signature image used on approved OD letters.', upload_to=accounts.models.secure_signature_path),
        ),
        migrations.AddField(
            model_name='facultyprofile',
            name='signature_image',
            field=models.FileField(blank=True, help_text='Digital signature image used on approved OD letters.', upload_to=accounts.models.secure_signature_path),
        ),
    ]
