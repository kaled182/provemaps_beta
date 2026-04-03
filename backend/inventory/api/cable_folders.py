from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from inventory.models import CableFolder, FiberCable

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────

def _folder_to_dict(folder: CableFolder, cable_counts: dict) -> dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "order": folder.order,
        "cable_count": cable_counts.get(folder.id, 0),
        "children": [],
    }


def _build_tree(folders, cable_counts: dict) -> list[dict]:
    """Convert a flat list of CableFolder into a nested tree."""
    nodes = {f.id: _folder_to_dict(f, cable_counts) for f in folders}
    roots = []
    for folder in folders:
        node = nodes[folder.id]
        if folder.parent_id and folder.parent_id in nodes:
            nodes[folder.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


# ── Views ──────────────────────────────────────────────────────────────────

@require_GET
@login_required
def api_list_cable_folders(request: HttpRequest) -> JsonResponse:
    """Return the full folder tree with cable counts."""
    folders = list(CableFolder.objects.select_related("parent").order_by("order", "name"))

    # Cable counts per folder (direct, not recursive)
    from django.db.models import Count
    counts_qs = (
        FiberCable.objects.filter(folder__isnull=False)
        .values("folder_id")
        .annotate(n=Count("id"))
    )
    cable_counts = {row["folder_id"]: row["n"] for row in counts_qs}

    tree = _build_tree(folders, cable_counts)

    # Also report cables with no folder
    no_folder_count = FiberCable.objects.filter(folder__isnull=True).count()

    return JsonResponse({"tree": tree, "no_folder_count": no_folder_count})


@require_POST
@login_required
def api_create_cable_folder(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    parent_id = data.get("parent_id") or None
    parent = None
    if parent_id:
        try:
            parent = CableFolder.objects.get(id=parent_id)
        except CableFolder.DoesNotExist:
            return JsonResponse({"error": f"Parent folder {parent_id} not found"}, status=404)

    if CableFolder.objects.filter(parent=parent, name=name).exists():
        return JsonResponse({"error": "A folder with this name already exists here"}, status=400)

    folder = CableFolder.objects.create(name=name, parent=parent)
    return JsonResponse({"id": folder.id, "name": folder.name, "parent_id": folder.parent_id}, status=201)


@require_http_methods(["PATCH"])
@login_required
def api_update_cable_folder(request: HttpRequest, folder_id: int) -> JsonResponse:
    try:
        folder = CableFolder.objects.get(id=folder_id)
    except CableFolder.DoesNotExist:
        return JsonResponse({"error": "Folder not found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    updated = []
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return JsonResponse({"error": "name cannot be empty"}, status=400)
        folder.name = name
        updated.append("name")

    if "parent_id" in data:
        parent_id = data["parent_id"]
        if parent_id is None:
            folder.parent = None
        else:
            try:
                folder.parent = CableFolder.objects.get(id=parent_id)
            except CableFolder.DoesNotExist:
                return JsonResponse({"error": f"Parent {parent_id} not found"}, status=404)
        updated.append("parent")

    if updated:
        folder.save(update_fields=updated)

    return JsonResponse({"id": folder.id, "name": folder.name, "parent_id": folder.parent_id})


@require_http_methods(["DELETE"])
@login_required
def api_delete_cable_folder(request: HttpRequest, folder_id: int) -> JsonResponse:
    try:
        folder = CableFolder.objects.get(id=folder_id)
    except CableFolder.DoesNotExist:
        return JsonResponse({"error": "Folder not found"}, status=404)

    # Unlink cables before deleting (SET_NULL handles it via DB, but children cascade)
    folder.delete()
    return HttpResponse(status=204)


@require_POST
@login_required
def api_move_cable_to_folder(request: HttpRequest, cable_id: int) -> JsonResponse:
    """Assign a cable to a folder (or remove from folder if folder_id is null)."""
    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return JsonResponse({"error": "Cable not found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    folder_id = data.get("folder_id")
    if folder_id is None:
        cable.folder = None
    else:
        try:
            cable.folder = CableFolder.objects.get(id=folder_id)
        except CableFolder.DoesNotExist:
            return JsonResponse({"error": f"Folder {folder_id} not found"}, status=404)

    cable.save(update_fields=["folder"])
    return JsonResponse({"cable_id": cable.id, "folder_id": cable.folder_id})
