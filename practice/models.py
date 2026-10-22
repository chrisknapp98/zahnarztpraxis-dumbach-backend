import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="announcements",
        editable=False,
    )
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    position = models.PositiveIntegerField(
        default=0,
        help_text="Lower positions appear first; newest announcements win ties.",
    )

    class Meta:
        ordering = ["position", "-created_at", "id"]

    def __str__(self):
        return self.message[:80]
