"""
Management command: python manage.py seed_analytics
Creates 90 days of realistic encounter history for surge prediction demo.
Pattern: morning surge (9-11am), evening surge (6-8pm), night trough (2-5am).
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed 90 days of analytics encounter data for realistic surge prediction"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90, help="Number of days to seed")
        parser.add_argument("--clear", action="store_true", help="Clear existing seeded data first")

    def handle(self, *args, **options):
        from core.models import Department, Patient, Encounter

        dept = Department.objects.filter(is_active=True).first()
        if not dept:
            self.stderr.write("No active department found. Create one first.")
            return

        days = options["days"]

        if options["clear"]:
            count = Encounter.objects.filter(
                department=dept, notes="[seeded]", is_deleted=False
            ).count()
            Encounter.objects.filter(department=dept, notes="[seeded]").delete()
            self.stdout.write(f"Cleared {count} seeded encounters.")

        # Realistic hour distribution (patients per hour baseline)
        # Morning surge 9-11, afternoon lull, evening surge 6-8, night trough
        HOUR_WEIGHTS = {
            0: 3, 1: 2, 2: 2, 3: 1, 4: 1, 5: 2,
            6: 5, 7: 8, 8: 12, 9: 18, 10: 20, 11: 16,
            12: 14, 13: 13, 14: 12, 15: 11, 16: 13, 17: 16,
            18: 19, 19: 18, 20: 14, 21: 10, 22: 7, 23: 5,
        }

        now = timezone.now()
        total_created = 0

        self.stdout.write(f"Seeding {days} days of data for '{dept.name}'...")

        for day_offset in range(days, 0, -1):
            target_date = now - timedelta(days=day_offset)
            is_weekend = target_date.weekday() >= 5
            day_multiplier = 1.3 if is_weekend else 1.0

            for hour, base_count in HOUR_WEIGHTS.items():
                # Add variance ±40%
                count = max(0, int(base_count * day_multiplier * random.uniform(0.6, 1.4)))

                for _ in range(count):
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    arrival_time = target_date.replace(
                        hour=hour, minute=minute, second=second, microsecond=0
                    )

                    # Create a minimal anonymous patient
                    patient = Patient.objects.create(
                        age=random.randint(18, 85),
                        gender=random.choice(["male", "female"]),
                        is_anonymized=True,
                    )

                    # Create completed encounter backdated to arrival_time
                    enc = Encounter(
                        patient=patient,
                        department=dept,
                        status="completed",
                        priority=random.choices(
                            ["low", "moderate", "high", "critical"],
                            weights=[30, 45, 18, 7]
                        )[0],
                        risk_score=random.randint(0, 85),
                        confidence_score=random.randint(50, 100),
                        notes="[seeded]",
                        is_deleted=False,
                    )
                    enc.save()

                    # Backdate timestamps directly (bypass auto_now_add)
                    Encounter.objects.filter(pk=enc.pk).update(
                        created_at=arrival_time,
                        updated_at=arrival_time + timedelta(minutes=random.randint(15, 120)),
                    )
                    total_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seeded {total_created} encounters over {days} days for '{dept.name}'.\n"
                f"   Run the forecast API to see peak hour predictions."
            )
        )
