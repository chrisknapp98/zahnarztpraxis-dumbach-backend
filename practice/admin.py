from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["message_preview", "author", "position", "created_at"]
    list_editable = ["position"]
    search_fields = ["message", "author__username"]
    readonly_fields = ["id", "author", "created_at"]
    list_select_related = ["author"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Message")
    def message_preview(self, obj):
        return str(obj)
