"""
User management API endpoints.
"""
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import json


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


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
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                is_active=data.get('is_active', True),
                is_staff=data.get('is_staff', False),
            )
            
            # Assign groups
            group_ids = data.get('groups', [])
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)
            
            return JsonResponse({
                'success': True,
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name() or user.username,
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
            
            user.save()
            
            # Update groups
            if 'groups' in data:
                group_ids = data['groups']
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)
            
            return JsonResponse({
                'success': True,
                'message': 'User updated successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name() or user.username,
                    'is_active': user.is_active,
                    'groups': [
                        {'id': g.id, 'name': g.name}
                        for g in user.groups.all()
                    ],
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
