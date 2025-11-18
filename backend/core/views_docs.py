"""
API views for documentation system.
"""
from pathlib import Path
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.http import require_GET


@require_GET
def serve_doc_file(request, doc_path):
    """
    Serve documentation markdown files from the /doc directory.
    
    Args:
        request: Django request object
        doc_path: Path to the markdown file relative to /doc directory
        
    Returns:
        HttpResponse with markdown content
        
    Security:
        - Only allows .md files
        - Prevents directory traversal attacks
        - Only serves files from /doc directory
    """
    # Security: Only allow .md files
    if not doc_path.endswith('.md'):
        raise Http404("Only markdown files are allowed")
    
    # Get the doc directory - it's at /app/doc in Docker
    # BASE_DIR can be /app or /app/backend depending on config
    base_path = Path(settings.BASE_DIR)
    
    # Try to find doc directory
    if (base_path / 'doc').exists():
        doc_dir = base_path / 'doc'
    elif (base_path.parent / 'doc').exists():
        doc_dir = base_path.parent / 'doc'
    else:
        # Fallback to /app/doc for Docker
        doc_dir = Path('/app/doc')
    
    # Resolve the full path and ensure it's within doc_dir
    try:
        requested_file = (doc_dir / doc_path).resolve()
        
        # Security: Prevent directory traversal
        if not str(requested_file).startswith(str(doc_dir.resolve())):
            raise Http404("Access denied")
        
        # Check if file exists
        if not requested_file.is_file():
            raise Http404(f"Documentation file not found: {doc_path}")
        
        # Read and return the file
        with open(requested_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return HttpResponse(
            content,
            content_type='text/markdown; charset=utf-8'
        )
        
    except (ValueError, OSError) as e:
        raise Http404(f"Invalid file path: {str(e)}")
