import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .access import can_access_practice


@never_cache
@require_GET
def session_status(request):
    valid = can_access_practice(request.user)
    return JsonResponse({"valid": bool(valid), "csrfToken": get_token(request)}, status=200 if valid else 401)


@never_cache
@require_POST
def session_login(request):
    if request.content_type != "application/json":
        return JsonResponse({"error": "JSON required"}, status=415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "JSON object required"}, status=400)
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password or len(username) > 150 or len(password) > 1024:
        return JsonResponse({"error": "Invalid credentials"}, status=400)
    user = authenticate(request, username=username, password=password)
    if not can_access_practice(user):
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"success": True, "csrfToken": get_token(request)})


@never_cache
@require_POST
def session_logout(request):
    logout(request)
    return JsonResponse({"success": True})
