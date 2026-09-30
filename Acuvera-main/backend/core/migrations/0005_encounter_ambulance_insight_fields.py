from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_encounter_bed_number_encounter_floor_and_more'),
    ]

    operations = [
        # Ambulance pre-triage fields
        migrations.AddField(
            model_name='encounter',
            name='eta_minutes',
            field=models.IntegerField(null=True, blank=True, help_text='Ambulance ETA in minutes'),
        ),
        migrations.AddField(
            model_name='encounter',
            name='eta_set_at',
            field=models.DateTimeField(null=True, blank=True, help_text='When ETA was recorded'),
        ),
        # AI insight caching
        migrations.AddField(
            model_name='encounter',
            name='ai_insight_json',
            field=models.JSONField(null=True, blank=True, help_text='Cached AI clinical insight'),
        ),
        # 'incoming' status for ambulance pre-registration
        migrations.AlterField(
            model_name='encounter',
            name='status',
            field=models.CharField(
                max_length=20,
                default='waiting',
                choices=[
                    ('incoming', 'Incoming Ambulance'),
                    ('waiting', 'Waiting'),
                    ('assigned', 'Assigned'),
                    ('in_progress', 'In Progress'),
                    ('completed', 'Completed'),
                    ('escalated', 'Escalated'),
                    ('cancelled', 'Cancelled'),
                ],
            ),
        ),
    ]
