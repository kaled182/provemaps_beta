"""API endpoints for FiberCable photo management."""
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

from integrations.zabbix.decorators import api_login_required, handle_api_errors
from inventory.models import FiberCable, FiberCablePhoto


@require_http_methods(["GET", "POST"])
@api_login_required
@handle_api_errors
def api_cable_photos(request: HttpRequest, cable_id: int) -> JsonResponse:
    """
    GET  /api/v1/inventory/fibers/<cable_id>/photos/  — list photos
    POST /api/v1/inventory/fibers/<cable_id>/photos/  — upload photo
    """
    cable = FiberCable.objects.get(pk=cable_id)

    if request.method == "GET":
        photos = cable.photos.select_related("uploaded_by").order_by("-uploaded_at")
        return JsonResponse(
            {
                "photos": [
                    {
                        "id": p.id,
                        "url": request.build_absolute_uri(p.image.url),
                        "caption": p.caption,
                        "uploaded_by": p.uploaded_by.get_full_name() or p.uploaded_by.username
                        if p.uploaded_by
                        else None,
                        "uploaded_at": p.uploaded_at.isoformat(),
                    }
                    for p in photos
                ]
            }
        )

    # POST — upload
    image_file = request.FILES.get("image")
    if not image_file:
        return JsonResponse({"error": "Nenhuma imagem enviada."}, status=400)

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if image_file.content_type not in allowed_types:
        return JsonResponse({"error": "Formato não suportado. Use JPG, PNG ou WEBP."}, status=400)

    max_size_mb = 10
    if image_file.size > max_size_mb * 1024 * 1024:
        return JsonResponse({"error": f"Arquivo muito grande. Máximo {max_size_mb} MB."}, status=400)

    caption = request.POST.get("caption", "").strip()[:200]

    photo = FiberCablePhoto.objects.create(
        cable=cable,
        image=image_file,
        caption=caption,
        uploaded_by=request.user,
    )

    return JsonResponse(
        {
            "id": photo.id,
            "url": request.build_absolute_uri(photo.image.url),
            "caption": photo.caption,
            "uploaded_by": request.user.get_full_name() or request.user.username,
            "uploaded_at": photo.uploaded_at.isoformat(),
        },
        status=201,
    )


@require_http_methods(["DELETE"])
@api_login_required
@handle_api_errors
def api_cable_photo_delete(request: HttpRequest, cable_id: int, photo_id: int) -> JsonResponse:
    """DELETE /api/v1/inventory/fibers/<cable_id>/photos/<photo_id>/"""
    photo = FiberCablePhoto.objects.get(pk=photo_id, cable_id=cable_id)

    # Only uploader or staff can delete
    if photo.uploaded_by_id != request.user.pk and not request.user.is_staff:
        return JsonResponse({"error": "Sem permissão para excluir esta foto."}, status=403)

    # Remove file from disk
    storage = photo.image.storage
    path = photo.image.name
    photo.delete()
    if storage.exists(path):
        storage.delete(path)

    return JsonResponse({"ok": True})
