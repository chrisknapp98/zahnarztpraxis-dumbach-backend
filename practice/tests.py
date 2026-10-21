from datetime import timedelta
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Announcement


class AnnouncementTests(TestCase):
    def test_manual_order_takes_priority_over_creation_date(self):
        now = timezone.now()
        older = Announcement.objects.create(message="Older", created_at=now - timedelta(days=1))
        newer = Announcement.objects.create(message="Newer", created_at=now)
        last = Announcement.objects.create(message="Last", position=1, created_at=now)
        self.assertEqual(list(Announcement.objects.all()), [newer, older, last])
        older.position = 2
        older.save(update_fields=["position"])
        self.assertEqual(list(Announcement.objects.all()), [newer, last, older])

    def test_existing_uuid_and_date_can_be_preserved_for_import(self):
        existing_id = uuid.uuid4()
        existing_date = timezone.now() - timedelta(days=30)
        announcement = Announcement.objects.create(
            id=existing_id, message="Practice closed\nCall https://example.com", created_at=existing_date
        )
        announcement.refresh_from_db()
        self.assertEqual(announcement.id, existing_id)
        self.assertEqual(announcement.created_at, existing_date)
        self.assertIn("\n", announcement.message)

    def test_rejects_empty_message_and_negative_position(self):
        for fields in [{"message": ""}, {"message": "Announcement", "position": -1}]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                Announcement(**fields).full_clean()
