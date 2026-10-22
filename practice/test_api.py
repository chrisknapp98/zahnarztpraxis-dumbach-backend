import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from .models import Announcement


class AnnouncementAPITests(TestCase):
    def setUp(self):
        self.url = reverse("practice:announcements")
        self.admin = get_user_model().objects.create_superuser(username="test-admin", password="test-password")

    def test_public_list_preserves_contract_and_issues_csrf_cookie(self):
        item = Announcement.objects.create(message="News")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{"id": str(item.id), "message": "News", "date": item.created_at.isoformat()}])
        self.assertIn("csrftoken", response.cookies)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_writes_require_login_and_staff_permission(self):
        item = Announcement.objects.create(message="News")
        cases = [("post", self.url, {"message": "New"}), ("put", self.url, {"orderedIds": []}), ("delete", f"{self.url}?id={item.id}", {})]
        for method, url, payload in cases:
            self.assertEqual(getattr(self.client, method)(url, payload, content_type="application/json").status_code, 401)
        staff = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.url, {"message": "New"}, content_type="application/json").status_code, 403)
        group = Group.objects.get(name="Practice editors")
        group.permissions.clear()
        staff.groups.add(group)
        staff.user_permissions.add(Permission.objects.get(codename="add_announcement"))
        self.assertEqual(self.client.post(self.url, {"message": "New"}, content_type="application/json").status_code, 201)
        self.assertEqual(self.client.put(self.url, {"orderedIds": []}, content_type="application/json").status_code, 403)

    def test_create_prepends_to_manually_ordered_list(self):
        old = Announcement.objects.create(message="Old", position=4)
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"message": "New\nhttps://example.com"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual([row["message"] for row in response.json()], ["New\nhttps://example.com", "Old"])
        self.assertEqual(response.json()[1]["id"], str(old.id))

    def test_invalid_payloads_do_not_create_announcements(self):
        self.client.force_login(self.admin)
        for payload in ["{", "[]", "null", '{"message":42}', '{"message":"   "}']:
            self.assertEqual(self.client.post(self.url, payload, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(self.url, {"message": "News"}).status_code, 415)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_partial_reorder_appends_omitted_items(self):
        first = Announcement.objects.create(message="First", position=0)
        second = Announcement.objects.create(message="Second", position=1)
        third = Announcement.objects.create(message="Third", position=2)
        self.client.force_login(self.admin)
        response = self.client.put(self.url, {"orderedIds": [str(third.id)]}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()], list(map(str, [third.id, first.id, second.id])))
        self.assertEqual(list(Announcement.objects.values_list("position", flat=True)), [0, 1, 2])

    def test_invalid_reorder_is_atomic(self):
        item = Announcement.objects.create(message="News", position=7)
        self.client.force_login(self.admin)
        for ids in [None, [str(item.id), str(item.id)], [str(uuid.uuid4())], ["invalid"], [42]]:
            response = self.client.put(self.url, {"orderedIds": ids}, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            item.refresh_from_db()
            self.assertEqual(item.position, 7)

    def test_delete_and_missing_ids(self):
        item = Announcement.objects.create(message="News")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete(self.url).status_code, 400)
        self.assertEqual(self.client.delete(f"{self.url}?id=invalid").status_code, 400)
        self.assertEqual(self.client.delete(f"{self.url}?id={uuid.uuid4()}").status_code, 404)
        response = self.client.delete(f"{self.url}?id={item.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_session_writes_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        token = client.get(self.url).cookies["csrftoken"].value
        payload = {"message": "News"}
        self.assertEqual(client.post(self.url, payload, content_type="application/json").status_code, 403)
        self.assertEqual(client.post(self.url, payload, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_unsupported_method(self):
        self.assertEqual(self.client.patch(self.url).status_code, 405)
