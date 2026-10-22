from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase


class SessionAPITests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_superuser(username="test-admin", password="test-password")

    def token(self):
        return self.client.get("/api/auth/validate").json()["csrfToken"]

    def test_login_write_logout_and_revocation(self):
        self.assertFalse(self.client.get("/api/auth/validate").json()["valid"])
        response = self.client.post("/api/auth", {"username": "test-admin", "password": "test-password"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token())
        self.assertEqual(response.status_code, 200)
        token = response.json()["csrfToken"]
        session = self.client.cookies["sessionid"].value
        self.assertTrue(self.client.get("/api/auth/validate").json()["valid"])
        self.assertEqual(self.client.post("/api/announcements", {"message": "News"}, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assertEqual(self.client.post("/api/auth/logout", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.client.cookies["sessionid"] = session
        self.assertEqual(self.client.get("/api/auth/validate").status_code, 401)

    def test_login_and_logout_require_csrf(self):
        self.assertEqual(self.client.post("/api/auth", {}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 403)

    def test_invalid_credentials_and_nonstaff_rejected(self):
        get_user_model().objects.create_user(username="reader", password="test-password")
        for username, password in [("test-admin", "wrong"), ("reader", "test-password")]:
            response = self.client.post("/api/auth", {"username": username, "password": password}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token())
            self.assertEqual(response.status_code, 401)

    def test_invalid_payload_and_untrusted_origin(self):
        token = self.token()
        self.assertEqual(self.client.post("/api/auth", "[]", content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(self.client.post("/api/auth", {}, content_type="application/json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://untrusted.example").status_code, 403)

    def test_editor_can_login_and_manage_without_django_admin_access(self):
        editor = get_user_model().objects.create_user(username="editor", password="editor-password")
        editor.groups.add(Group.objects.get(name="Practice editors"))
        response = self.client.post("/api/auth", {"username": "editor", "password": "editor-password"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(editor.is_staff)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        token = response.json()["csrfToken"]
        response = self.client.post("/api/announcements", {"message": "Editor news"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
        item_id = response.json()[0]["id"]
        self.assertEqual(self.client.put("/api/announcements", {"orderedIds": [item_id]}, content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/announcements?id={item_id}", HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_staff_alone_does_not_grant_frontend_access(self):
        staff = get_user_model().objects.create_user(username="staff", password="staff-password", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="add_announcement"))
        response = self.client.post("/api/auth", {"username": "staff", "password": "staff-password"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token())
        self.assertEqual(response.status_code, 401)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/api/auth/validate").status_code, 401)
        self.assertEqual(self.client.post("/api/announcements", {"message": "No"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token()).status_code, 403)

    def test_membership_revocation_and_model_permissions_are_enforced(self):
        editor = get_user_model().objects.create_user(username="editor")
        group = Group.objects.get(name="Practice editors")
        editor.groups.add(group)
        self.client.force_login(editor)
        group.permissions.remove(Permission.objects.get(codename="add_announcement"))
        self.assertEqual(self.client.post("/api/announcements", {"message": "No"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token()).status_code, 403)
        editor.groups.clear()
        self.assertEqual(self.client.get("/api/auth/validate").status_code, 401)
        self.assertEqual(self.client.post("/api/announcements", {"message": "No"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token()).status_code, 403)

    def test_disabled_editor_cannot_access_frontend(self):
        editor = get_user_model().objects.create_user(username="disabled", password="editor-password", is_active=False)
        editor.groups.add(Group.objects.get(name="Practice editors"))
        response = self.client.post("/api/auth", {"username": "disabled", "password": "editor-password"}, content_type="application/json", HTTP_X_CSRFTOKEN=self.token())
        self.assertEqual(response.status_code, 401)

    def test_session_exposes_username_only_to_authorized_user(self):
        self.assertIsNone(self.client.get("/api/auth/validate").json()["username"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/auth/validate").json()["username"], "test-admin")
        reader = get_user_model().objects.create_user(username="reader")
        self.client.force_login(reader)
        self.assertIsNone(self.client.get("/api/auth/validate").json()["username"])
