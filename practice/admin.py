from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["message_preview", "position", "created_at"]
    list_editable = ["position"]
    search_fields = ["message"]
    readonly_fields = ["id", "created_at"]

    @admin.display(description="Message")
    def message_preview(self, obj):
        return str(obj)
