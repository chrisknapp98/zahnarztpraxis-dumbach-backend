from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="Original-Password-293!")
        self.user.groups.add(Group.objects.get(name="Practice editors"))
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.token = self.client.get("/api/auth/validate").json()["csrfToken"]
        self.payload = {"old_password": "Original-Password-293!", "new_password1": "Different-Password-781!", "new_password2": "Different-Password-781!"}

    def post(self, payload=None, **headers):
        return self.client.post("/api/auth/password", self.payload if payload is None else payload, content_type="application/json", HTTP_X_CSRFTOKEN=self.token, **headers)

    def test_changes_only_own_password_preserves_current_session_and_revokes_others(self):
        other_session = Client()
        other_session.force_login(self.user)
        other_user = get_user_model().objects.create_user(username="other", password="Other-Password-123!")
        self.assertEqual(self.post({**self.payload, "username": "other"}).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.payload["new_password1"]))
        self.assertFalse(self.user.check_password(self.payload["old_password"]))
        other_user.refresh_from_db()
        self.assertTrue(other_user.check_password("Other-Password-123!"))
        self.assertEqual(self.client.get("/api/auth/validate").status_code, 200)
        self.assertEqual(other_session.get("/api/auth/validate").status_code, 401)

    def test_rejects_wrong_current_password(self):
        response = self.post({**self.payload, "old_password": "wrong"})

        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(set(errors), {"old_password"})
        self.assertEqual(errors["old_password"][0]["code"], "password_incorrect")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.payload["old_password"]))

    def test_rejects_mismatched_new_passwords(self):
        response = self.post({**self.payload, "new_password2": "mismatch"})

        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(set(errors), {"new_password2"})
        self.assertEqual(errors["new_password2"][0]["code"], "password_mismatch")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.payload["old_password"]))

    def test_rejects_weak_new_password(self):
        response = self.post({**self.payload, "new_password1": "123", "new_password2": "123"})

        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(set(errors), {"new_password2"})
        self.assertIn("password_too_short", {error["code"] for error in errors["new_password2"]})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.payload["old_password"]))

    def test_requires_session_editor_access_and_csrf(self):
        self.assertEqual(self.client.post("/api/auth/password", self.payload, content_type="application/json").status_code, 403)
        self.user.groups.clear()
        self.assertEqual(self.post().status_code, 401)
        self.client.logout()
        self.token = self.client.get("/api/auth/validate").json()["csrfToken"]
        self.assertEqual(self.post().status_code, 401)

    def test_rejects_malformed_payloads(self):
        for payload in [[], {}, {**self.payload, "old_password": 42}, {**self.payload, "new_password1": "a" * 1025}]:
            self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.client.get("/api/auth/password").status_code, 405)
