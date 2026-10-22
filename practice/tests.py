from datetime import timedelta
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.contrib import admin
from django.test import RequestFactory
from .admin import AnnouncementAdmin
from django.test import TestCase
from django.utils import timezone

from .models import Announcement


class AnnouncementTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="author")

    def test_manual_order_takes_priority_over_creation_date(self):
        now = timezone.now()
        older = Announcement.objects.create(author=self.author, message="Older", created_at=now - timedelta(days=1))
        newer = Announcement.objects.create(author=self.author, message="Newer", created_at=now)
        last = Announcement.objects.create(author=self.author, message="Last", position=1, created_at=now)
        self.assertEqual(list(Announcement.objects.all()), [newer, older, last])
        older.position = 2
        older.save(update_fields=["position"])
        self.assertEqual(list(Announcement.objects.all()), [newer, last, older])

    def test_existing_uuid_and_date_can_be_preserved_for_import(self):
        existing_id = uuid.uuid4()
        existing_date = timezone.now() - timedelta(days=30)
        announcement = Announcement.objects.create(author=self.author,
            id=existing_id, message="Practice closed\nCall https://example.com", created_at=existing_date
        )
        announcement.refresh_from_db()
        self.assertEqual(announcement.id, existing_id)
        self.assertEqual(announcement.created_at, existing_date)
        self.assertIn("\n", announcement.message)

    def test_rejects_empty_message_and_negative_position(self):
        for fields in [{"message": ""}, {"message": "Announcement", "position": -1}]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                Announcement(author=self.author, **fields).full_clean()

    def test_author_is_required_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Announcement.objects.create(message="Missing author")

    def test_author_cannot_be_deleted_but_can_be_deactivated(self):
        item = Announcement.objects.create(author=self.author, message="News")
        with self.assertRaises(ProtectedError):
            self.author.delete()
        self.author.is_active = False
        self.author.save(update_fields=["is_active"])
        item.refresh_from_db()
        self.assertEqual(item.author_id, self.author.pk)

    def test_admin_sets_author_on_creation_and_preserves_it_on_edit(self):
        model_admin = AnnouncementAdmin(Announcement, admin.site)
        request = RequestFactory().post("/admin/practice/announcement/add/")
        request.user = self.author
        item = Announcement(message="News")
        model_admin.save_model(request, item, form=None, change=False)
        self.assertEqual(item.author, self.author)
        request.user = get_user_model().objects.create_user(username="another-editor")
        item.message = "Changed"
        model_admin.save_model(request, item, form=None, change=True)
        item.refresh_from_db()
        self.assertEqual(item.author, self.author)
