import json
from uuid import UUID

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .access import can_access_practice
from .models import Announcement


def announcement_list(status=200):
    return JsonResponse([
        {"id": str(item.id), "message": item.message, "date": item.created_at.isoformat()}
        for item in Announcement.objects.all()
    ], safe=False, status=status)


def parse_uuid(value):
    if not isinstance(value, str):
        raise ValueError("ID must be a UUID string")
    return UUID(value)


@never_cache
@ensure_csrf_cookie
@require_http_methods(["GET", "POST", "DELETE", "PUT"])
def announcements(request):
    if request.method == "GET":
        return announcement_list()

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    permission = {"POST": "add", "DELETE": "delete", "PUT": "change"}[request.method]
    if not can_access_practice(request.user) or not request.user.has_perm(
        f"practice.{permission}_announcement"
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    if request.method == "DELETE":
        try:
            item_id = parse_uuid(request.GET.get("id"))
        except ValueError:
            return JsonResponse({"error": "A valid UUID id is required"}, status=400)
        deleted, _ = Announcement.objects.filter(id=item_id).delete()
        if not deleted:
            return JsonResponse({"error": "Announcement not found"}, status=404)
        return announcement_list()

    if request.content_type != "application/json":
        return JsonResponse({"error": "Content-Type must be application/json"}, status=415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "A JSON object is required"}, status=400)

    if request.method == "POST":
        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return JsonResponse({"error": "A non-empty message is required"}, status=400)
        with transaction.atomic():
            # Make room at the front without losing the current manual ordering.
            Announcement.objects.update(position=F("position") + 1)
            Announcement.objects.create(message=message, position=0, author=request.user)
            return announcement_list(status=201)

    ordered_ids = data.get("orderedIds")
    if not isinstance(ordered_ids, list):
        return JsonResponse({"error": "orderedIds must be an array"}, status=400)
    try:
        ordered_ids = [parse_uuid(value) for value in ordered_ids]
    except ValueError:
        return JsonResponse({"error": "orderedIds must contain UUID strings"}, status=400)
    if len(set(ordered_ids)) != len(ordered_ids):
        return JsonResponse({"error": "orderedIds must not contain duplicates"}, status=400)
    with transaction.atomic():
        items = list(Announcement.objects.select_for_update().all())
        by_id = {item.id: item for item in items}
        missing = [str(item_id) for item_id in ordered_ids if item_id not in by_id]
        if missing:
            return JsonResponse({"error": "Some ids do not exist", "missing": missing}, status=400)
        requested = set(ordered_ids)
        ordered = [by_id[item_id] for item_id in ordered_ids]
        ordered.extend(item for item in items if item.id not in requested)
        for position, item in enumerate(ordered):
            item.position = position
        Announcement.objects.bulk_update(ordered, ["position"])
        return announcement_list()
