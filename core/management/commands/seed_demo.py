import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.crypto import encrypt_text
from core.models import FoundItem, User
from core.services import record, review_claim, submit_claim


class Command(BaseCommand):
    help = "Create fictional local demonstration data. Never use this against production."

    def handle(self, *args, **options):
        if settings.PRODUCTION:
            raise CommandError("Demo seeding is disabled in production mode.")
        created = []
        for name, role in [("alex", "student"), ("jamie", "student"), ("officer", "officer"), ("admin", "admin")]:
            user, fresh = User.objects.get_or_create(username=name, defaults={"email": f"{name}@claimsafe.example", "role": role})
            if fresh:
                password = secrets.token_urlsafe(15)
                user.set_password(password)
                user.save()
                record(user, "demo.account_created")
                created.append(f"{name} ({role}): {password}")
        if created:
            with (settings.LOCAL_DIR / "demo-accounts.txt").open("a", encoding="utf-8") as stream:
                stream.write("\nFICTIONAL LOCAL DEMO ACCOUNTS - DO NOT COMMIT OR SHARE\n" + "\n".join(created) + "\n")
        officer = User.objects.get(username="officer")
        if not officer.is_officer:
            raise CommandError("The existing officer account is not an officer. No privilege was changed.")
        samples = [
            ("Over-ear headphones", "electronics", "Library, ground floor", "A pair of wireless headphones in a carry case.", "Fictional example: a crescent sticker inside the left ear cup and a blue cable in the case."),
            ("Canvas laptop sleeve", "accessories", "Student common room", "A padded laptop sleeve handed in after the afternoon session.", "Fictional example: the inside pocket contains a violet bookmark with a hand-drawn fox."),
            ("Hardcover notebook", "books", "Engineering block", "A lined notebook with handwritten pages. Personal details are withheld.", "Fictional example: first page has a sketch of a lighthouse and a green ribbon bookmark."),
            ("Everyday tote bag", "other", "Campus cafe", "A fabric tote bag received at the property desk.", "Fictional example: a small embroidered lemon on the inner seam and two wooden pencils."),
            ("Small accessory pouch", "accessories", "Lecture theatre foyer", "A zipped pouch containing a few small belongings.", "Fictional example: the zip pull is shaped like a leaf and the lining has tiny orange dots."),
            ("Pocket sketchbook", "books", "Design studio", "A compact sketchbook found after a studio session.", "Fictional example: page six contains a drawing of three bicycles under an arch."),
        ]
        items = []
        for index, (title, category, location, public, private) in enumerate(samples):
            item, fresh = FoundItem.objects.get_or_create(title=title, defaults={
                "category": category, "location": location, "public_description": public,
                "identifying_details_ciphertext": encrypt_text(private), "recorded_by": officer,
                "found_on": timezone.localdate() - timedelta(days=index),
            })
            if fresh:
                record(officer, "demo.item_recorded", item.id)
            items.append(item)
        alex = User.objects.get(username="alex")
        if not alex.claims.exists():
            submit_claim(alex, items[0].id, "Fictional demo evidence: a crescent sticker inside the left ear cup; my blue charging cable is in the case.")
            claim = submit_claim(alex, items[1].id, "Fictional demo evidence: a violet bookmark with a hand-drawn fox is in the sleeve's inside pocket.")
            review_claim(officer, claim.id, "approve", "Your description matches the withheld record. Please visit the property desk to collect it.")
        self.stdout.write(self.style.SUCCESS("Fictional demo is ready. Credentials are in .local/demo-accounts.txt."))
