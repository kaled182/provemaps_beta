"""
User management API endpoints.
"""
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
import urllib.parse

from core.models import UserProfile, Department


PROFILE_FIELDS = {
    "phone_number",
    "telegram_chat_id",
    "notify_via_email",
    "notify_via_whatsapp",
    "notify_via_telegram",
    "receive_critical_alerts",
    "receive_warning_alerts",
    "department",
}


def _get_or_create_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create(user=user)


def _serialize_profile(profile, request=None):
    avatar_url = None
    if profile.avatar and profile.avatar.name:
        try:
            avatar_url = profile.avatar.url
        except Exception:
            media_base = settings.MEDIA_URL or "/media/"
            avatar_path = profile.avatar.name.lstrip("/")
            avatar_url = f"{media_base}{avatar_path}"

        if request is not None and avatar_url:
            avatar_url = request.build_absolute_uri(avatar_url)

    departments = list(profile.departments.order_by("name").values("id", "name"))
    department_name = profile.department
    if not department_name and departments:
        department_name = departments[0]["name"]

    return {
        "avatar_url": avatar_url,
        "phone_number": profile.phone_number,
        "telegram_chat_id": profile.telegram_chat_id,
        "notify_via_email": profile.notify_via_email,
        "notify_via_whatsapp": profile.notify_via_whatsapp,
        "notify_via_telegram": profile.notify_via_telegram,
        "receive_critical_alerts": profile.receive_critical_alerts,
        "receive_warning_alerts": profile.receive_warning_alerts,
        "department": department_name or "",
        "departments": departments,
        "totp_enabled": profile.totp_enabled,
        "totp_configured": bool(profile.totp_secret),
    }


def _apply_profile_updates(profile, data):
    departments_data = None
    if "departments" in data:
        departments_data = data.pop("departments")
    for field in PROFILE_FIELDS:
        if field in data:
            setattr(profile, field, data[field])
    profile.save()

    if departments_data is not None:
        if departments_data is None:
            departments_data = []
        if not isinstance(departments_data, (list, tuple)):
            departments_data = []
        department_ids = [value for value in departments_data if isinstance(value, int)]
        departments = list(Department.objects.filter(id__in=department_ids))
        profile.departments.set(departments)
        if departments:
            profile.department = departments[0].name
        elif "department" in data:
            profile.department = (data.get("department") or "").strip()
        else:
            profile.department = ""
        profile.save()
    elif "department" in data:
        department_name = (data.get("department") or "").strip()
        if department_name:
            dept = Department.objects.filter(name__iexact=department_name).first()
            if dept:
                profile.departments.set([dept])
            else:
                profile.departments.clear()
        else:
            profile.departments.clear()


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return value


def _extract_profile_data(raw_data):
    profile_data = {}

    if isinstance(raw_data, dict) and isinstance(raw_data.get("profile"), dict):
        profile_data.update(raw_data.get("profile", {}))

    for key, value in raw_data.items():
        if key.startswith("profile."):
            profile_data[key.replace("profile.", "", 1)] = value

    for key in list(profile_data.keys()):
        if key in {
            "notify_via_email",
            "notify_via_whatsapp",
            "notify_via_telegram",
            "receive_critical_alerts",
            "receive_warning_alerts",
        }:
            profile_data[key] = _coerce_bool(profile_data[key])

    return profile_data


def _generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def _base32_decode(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(f"{secret.upper()}{padding}")


def _totp_at(secret: str, counter: int, digits: int = 6) -> int:
    msg = struct.pack(">Q", counter)
    digest = hmac.new(_base32_decode(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return truncated % (10 ** digits)


def _verify_totp(secret: str, code: str, step: int = 30, window: int = 1) -> bool:
    if not code or not code.isdigit():
        return False
    counter = int(time.time() / step)
    expected = int(code)
    for offset in range(-window, window + 1):
        if _totp_at(secret, counter + offset) == expected:
            return True
    return False


def _build_otpauth_url(secret: str, username: str, issuer: str) -> str:
    label = urllib.parse.quote(f"{issuer}:{username}")
    issuer_value = urllib.parse.quote(issuer)
    return (
        f"otpauth://totp/{label}"
        f"?secret={secret}&issuer={issuer_value}&algorithm=SHA1&digits=6&period=30"
    )

def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


def _department_user_qs(department):
    return UserProfile.objects.filter(
        Q(departments=department) | Q(department__iexact=department.name)
    ).distinct()


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET", "POST"])
def list_departments(request):
    if request.method == "GET":
        departments = Department.objects.order_by("name")
        return JsonResponse({
            "success": True,
            "departments": [
                {
                    "id": dept.id,
                    "name": dept.name,
                    "description": dept.description,
                    "is_active": dept.is_active,
                    "created_at": dept.created_at.isoformat(),
                }
                for dept in departments
            ],
        })

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    if not name:
        return JsonResponse({"success": False, "error": "Nome obrigatorio"}, status=400)

    try:
        department = Department.objects.create(
            name=name,
            description=description,
            is_active=bool(data.get("is_active", True)),
        )
    except IntegrityError:
        return JsonResponse({"success": False, "error": "Departamento ja existe"}, status=400)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    return JsonResponse({
        "success": True,
        "department": {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "is_active": department.is_active,
            "created_at": department.created_at.isoformat(),
        },
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["PATCH", "DELETE"])
def department_detail(request, department_id):
    try:
        department = Department.objects.get(id=department_id)
    except Department.DoesNotExist:
        return JsonResponse({"success": False, "error": "Departamento nao encontrado"}, status=404)

    if request.method == "DELETE":
        if _department_user_qs(department).exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": "Departamento possui usuarios",
                },
                status=400,
            )
        department.delete()
        return JsonResponse({"success": True, "message": "Departamento removido"})

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "Nome obrigatorio"}, status=400)
        department.name = name

    if "description" in data:
        department.description = (data.get("description") or "").strip()

    if "is_active" in data:
        department.is_active = bool(data.get("is_active"))

    try:
        department.save()
    except IntegrityError:
        return JsonResponse({"success": False, "error": "Departamento ja existe"}, status=400)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    return JsonResponse({
        "success": True,
        "department": {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "is_active": department.is_active,
            "created_at": department.created_at.isoformat(),
        },
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def remove_department(request, department_id):
    try:
        department = Department.objects.get(id=department_id)
    except Department.DoesNotExist:
        return JsonResponse({"success": False, "error": "Departamento nao encontrado"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    users_qs = _department_user_qs(department)
    users_count = users_qs.count()
    move_to = data.get("move_to", "__missing__")
    if users_count > 0 and move_to == "__missing__":
        return JsonResponse(
            {
                "success": False,
                "error": "Informe o destino para os usuarios antes de remover.",
                "users": users_count,
            },
            status=400,
        )

    new_department_name = ""
    target = None
    if move_to not in (None, ""):
        try:
            target = Department.objects.get(id=move_to)
        except Department.DoesNotExist:
            return JsonResponse({"success": False, "error": "Departamento destino nao encontrado"}, status=404)
        new_department_name = target.name

    if users_count > 0:
        for profile in users_qs:
            if target:
                if profile.departments.filter(id=department.id).exists():
                    profile.departments.remove(department)
                    profile.departments.add(target)
                if profile.department.strip().lower() == department.name.lower():
                    profile.department = new_department_name
                elif profile.departments.exists() and not profile.department:
                    profile.department = profile.departments.order_by("name").first().name
            else:
                if profile.departments.filter(id=department.id).exists():
                    profile.departments.remove(department)
                if profile.department.strip().lower() == department.name.lower():
                    profile.department = ""
                elif profile.departments.exists() and not profile.department:
                    profile.department = profile.departments.order_by("name").first().name
            profile.save()

    department.delete()
    return JsonResponse(
        {
            "success": True,
            "message": "Departamento removido",
            "moved_users": users_count,
            "target_department": new_department_name,
        }
    )


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def list_users(request):
    """
    List all users with their details.
    
    Query parameters:
        - search: Search by name, email, or username
        - is_active: Filter by active status (true/false)
        - group: Filter by group name
    """
    users = User.objects.all().select_related().prefetch_related('groups')
    
    # Apply filters
    search = request.GET.get('search', '').strip()
    if search:
        users = users.filter(
            username__icontains=search
        ) | users.filter(
            email__icontains=search
        ) | users.filter(
            first_name__icontains=search
        ) | users.filter(
            last_name__icontains=search
        )
    
    is_active = request.GET.get('is_active')
    if is_active is not None:
        users = users.filter(is_active=is_active.lower() == 'true')
    
    group_name = request.GET.get('group')
    if group_name:
        users = users.filter(groups__name=group_name)
    
    # Serialize users
    users_data = []
    for user in users.distinct():
        profile = _get_or_create_profile(user)
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
            'last_login': (
                user.last_login.isoformat() if user.last_login else None
            ),
            'groups': [
                {'id': g.id, 'name': g.name} for g in user.groups.all()
            ],
            'profile': _serialize_profile(profile, request=request),
        })
    
    return JsonResponse({
        'success': True,
        'users': users_data,
        'count': len(users_data),
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_user(request, user_id):
    """Get detailed information about a specific user."""
    try:
        user = User.objects.prefetch_related('groups').get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    profile = _get_or_create_profile(user)

    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
            'last_login': (
                user.last_login.isoformat() if user.last_login else None
            ),
            'groups': [
                {'id': g.id, 'name': g.name} for g in user.groups.all()
            ],
            'profile': _serialize_profile(profile, request=request),
        }
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def create_user(request):
    """
    Create a new user.
    
    Required fields:
        - username
        - email
        - password
        
    Optional fields:
        - first_name
        - last_name
        - is_active
        - is_staff
        - groups (list of group IDs)
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    # Validate required fields
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not username:
        return JsonResponse({
            'success': False,
            'error': 'Username is required'
        }, status=400)
    
    if not email:
        return JsonResponse({
            'success': False,
            'error': 'Email is required'
        }, status=400)
    
    if not password:
        return JsonResponse({
            'success': False,
            'error': 'Password is required'
        }, status=400)
    
    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid email format'
        }, status=400)
    
    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'success': False,
            'error': 'Username already exists'
        }, status=400)
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return JsonResponse({
            'success': False,
            'error': 'Email already exists'
        }, status=400)
    
    try:
        with transaction.atomic():
            is_superuser = False
            is_staff = data.get('is_staff', False)
            if request.user.is_superuser:
                is_superuser = bool(data.get('is_superuser', False))
                is_staff = bool(is_staff) or is_superuser

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                is_active=data.get('is_active', True),
                is_staff=is_staff,
                is_superuser=is_superuser,
            )
            
            # Assign groups
            group_ids = data.get('groups', [])
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)

            profile = _get_or_create_profile(user)
            profile_data = data.get('profile', {})
            if isinstance(profile_data, dict):
                _apply_profile_updates(profile, profile_data)
            
            return JsonResponse({
                'success': True,
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name() or user.username,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                'profile': _serialize_profile(profile, request=request),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["PUT", "PATCH"])
def update_user(request, user_id):
    """
    Update user information.
    
    Allowed fields:
        - email
        - first_name
        - last_name
        - is_active
        - is_staff
        - groups (list of group IDs)
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    # Prevent users from editing superusers
    if user.is_superuser and not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Cannot edit superuser account'
        }, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    try:
        with transaction.atomic():
            # Update allowed fields
            if 'email' in data:
                email = data['email'].strip()
                if email != user.email:
                    # Validate email
                    try:
                        validate_email(email)
                    except ValidationError:
                        return JsonResponse({
                            'success': False,
                            'error': 'Invalid email format'
                        }, status=400)
                    
                    # Check if email already exists
                    if User.objects.filter(email=email).exists():
                        return JsonResponse({
                            'success': False,
                            'error': 'Email already exists'
                        }, status=400)
                    
                    user.email = email
            
            if 'first_name' in data:
                user.first_name = data['first_name'].strip()
            
            if 'last_name' in data:
                user.last_name = data['last_name'].strip()
            
            if 'is_active' in data and request.user.is_superuser:
                user.is_active = data['is_active']
            
            if 'is_staff' in data and request.user.is_superuser:
                user.is_staff = data['is_staff']

            if 'is_superuser' in data and request.user.is_superuser:
                user.is_superuser = data['is_superuser']
                if user.is_superuser:
                    user.is_staff = True

            if 'password' in data:
                if request.user.is_superuser or request.user.id == user.id:
                    if data['password']:
                        user.set_password(data['password'])
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Cannot update password for this user'
                    }, status=403)
            
            user.save()
            
            # Update groups
            if 'groups' in data:
                group_ids = data['groups']
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)

            if 'profile' in data and isinstance(data['profile'], dict):
                profile = _get_or_create_profile(user)
                _apply_profile_updates(profile, data['profile'])
            else:
                profile = _get_or_create_profile(user)
            
            return JsonResponse({
                'success': True,
                'message': 'User updated successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name() or user.username,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'groups': [
                        {'id': g.id, 'name': g.name}
                        for g in user.groups.all()
                    ],
                    'profile': _serialize_profile(profile, request=request),
                }
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["DELETE"])
def delete_user(request, user_id):
    """Delete a user (only superusers can delete)."""
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Only superusers can delete users'
        }, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    # Prevent deleting superusers
    if user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Cannot delete superuser account'
        }, status=403)
    
    # Prevent self-deletion
    if user.id == request.user.id:
        return JsonResponse({
            'success': False,
            'error': 'Cannot delete your own account'
        }, status=403)
    
    username = user.username
    user.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'User {username} deleted successfully'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def list_groups(request):
    """List all available groups."""
    groups = Group.objects.all().prefetch_related('user_set')
    
    groups_data = []
    for group in groups:
        groups_data.append({
            'id': group.id,
            'name': group.name,
            'user_count': group.user_set.count(),
        })
    
    return JsonResponse({
        'success': True,
        'groups': groups_data,
    })


@login_required
@require_http_methods(["GET", "POST", "PATCH", "PUT"])
def me_user(request):
    user = request.user
    profile = _get_or_create_profile(user)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.get_full_name() or user.username,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "groups": [
                    {"id": g.id, "name": g.name} for g in user.groups.all()
                ],
                "profile": _serialize_profile(profile),
            },
        })

    data = {}
    body = request.body or b""

    if request.content_type and request.content_type.startswith("application/json"):
        try:
            data.update(json.loads(body or "{}"))
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON"
            }, status=400)
    elif body:
        try:
            data.update(json.loads(body))
        except json.JSONDecodeError:
            pass

    if request.POST:
        data.update(dict(request.POST.items()))

    profile_data = _extract_profile_data(data)
    avatar_file = request.FILES.get("avatar") or request.FILES.get("profile.avatar")

    if "first_name" in data:
        user.first_name = data.get("first_name", "").strip()
    if "last_name" in data:
        user.last_name = data.get("last_name", "").strip()

    if "email" in data:
        email = data.get("email", "").strip()
        if email and email != user.email:
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({
                    "success": False,
                    "error": "Invalid email format"
                }, status=400)

            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return JsonResponse({
                    "success": False,
                    "error": "Email already exists"
                }, status=400)
            user.email = email

    user.save()

    if profile_data:
        _apply_profile_updates(profile, profile_data)

    if avatar_file:
        profile.avatar = avatar_file
        profile.save()

    return JsonResponse({
        "success": True,
        "message": "Profile updated",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.get_full_name() or user.username,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "groups": [
                {"id": g.id, "name": g.name} for g in user.groups.all()
            ],
            "profile": _serialize_profile(profile, request=request),
        },
    })


@login_required
@require_http_methods(["POST"])
def me_avatar(request):
    profile = _get_or_create_profile(request.user)
    avatar_file = request.FILES.get("avatar")
    if not avatar_file:
        return JsonResponse({
            "success": False,
            "error": "Avatar file is required"
        }, status=400)

    profile.avatar = avatar_file
    profile.save()

    return JsonResponse({
        "success": True,
        "message": "Avatar updated",
        "avatar_url": _serialize_profile(profile, request=request).get("avatar_url"),
    })


@login_required
@require_http_methods(["GET"])
def me_totp(request):
    profile = _get_or_create_profile(request.user)
    setup = request.GET.get("setup", "").lower() in {"1", "true", "yes"}
    reset = request.GET.get("reset", "").lower() in {"1", "true", "yes"}
    issuer = getattr(settings, "TOTP_ISSUER", "ProveMaps")

    if setup:
        if reset or not profile.totp_secret:
            profile.totp_secret = _generate_totp_secret()
            profile.totp_enabled = False
            profile.save()

        secret = profile.totp_secret
        return JsonResponse({
            "success": True,
            "enabled": profile.totp_enabled,
            "configured": bool(secret),
            "issuer": issuer,
            "secret": secret,
            "otpauth_url": _build_otpauth_url(
                secret,
                request.user.email or request.user.username,
                issuer,
            ) if secret else "",
        })

    return JsonResponse({
        "success": True,
        "enabled": profile.totp_enabled,
        "configured": bool(profile.totp_secret),
    })


@login_required
@require_http_methods(["POST"])
def me_totp_verify(request):
    profile = _get_or_create_profile(request.user)
    if not profile.totp_secret:
        return JsonResponse({
            "success": False,
            "error": "TOTP not configured"
        }, status=400)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON"
            }, status=400)

    code = str(data.get("code", "")).strip()
    if not _verify_totp(profile.totp_secret, code):
        return JsonResponse({
            "success": False,
            "error": "Invalid code"
        }, status=400)

    profile.totp_enabled = True
    profile.save()

    return JsonResponse({
        "success": True,
        "message": "TOTP enabled",
        "enabled": True,
    })


@login_required
@require_http_methods(["POST"])
def me_totp_disable(request):
    profile = _get_or_create_profile(request.user)
    data = {}
    if request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            data = {}

    reset = str(data.get("reset", "")).lower() in {"1", "true", "yes"}
    profile.totp_enabled = False
    if reset:
        profile.totp_secret = None
    profile.save()

    return JsonResponse({
        "success": True,
        "message": "TOTP disabled",
        "enabled": False,
        "configured": bool(profile.totp_secret),
    })
