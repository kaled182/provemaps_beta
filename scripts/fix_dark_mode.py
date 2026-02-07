#!/usr/bin/env python3
"""
Remove @media (prefers-color-scheme: dark) blocks and replace hardcoded colors with CSS variables
"""
import re

files = [
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactEditModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\BulkMessageModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactGroupManager.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactImportModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactList.vue"
]

# Color replacements
REPLACEMENTS = {
    r'background:\s*white;': 'background: var(--surface-card);',
    r'background:\s*#1e293b;': 'background: var(--surface-card);',
    r'background:\s*#f8f9fa;': 'background: var(--bg-secondary);',
    r'background:\s*#0f172a;': 'background: var(--bg-secondary);',
    r'background:\s*#e7f3ff;': 'background: var(--accent-info-light);',
    r'background:\s*#1e3a5f;': 'background: var(--accent-info-light);',
    r'border:\s*1px solid #ddd;': 'border: 1px solid var(--border-secondary);',
    r'border:\s*1px solid #dee2e6;': 'border: 1px solid var(--border-secondary);',
    r'border-bottom:\s*1px solid #dee2e6;': 'border-bottom: 1px solid var(--border-secondary);',
    r'border-top:\s*1px solid #dee2e6;': 'border-top: 1px solid var(--border-secondary);',
    r'border-color:\s*#475569;': 'border-color: var(--border-primary);',
    r'border-color:\s*#334155;': 'border-color: var(--border-primary);',
    r'color:\s*#333;': 'color: var(--text-primary);',
    r'color:\s*#e2e8f0;': 'color: var(--text-primary);',
    r'color:\s*#cbd5e1;': 'color: var(--text-secondary);',
    r'color:\s*#495057;': 'color: var(--text-secondary);',
    r'color:\s*#999;': 'color: var(--text-tertiary);',
    r'color:\s*#64748b;': 'color: var(--text-tertiary);',
    r'color:\s*#94a3b8;': 'color: var(--text-tertiary);',
}

def remove_media_queries(content):
    """Remove all @media (prefers-color-scheme: dark) blocks PROPERLY"""
    # Pattern to match @media block with proper brace counting
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a media query
        if '@media' in line and 'prefers-color-scheme' in line and 'dark' in line:
            # Find the opening brace
            brace_count = line.count('{') - line.count('}')
            i += 1
            
            # Skip until braces are balanced
            while i < len(lines) and brace_count > 0:
                brace_count += lines[i].count('{') - lines[i].count('}')
                i += 1
            
            # Don't append the media query lines
            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

def apply_replacements(content):
    """Replace hardcoded colors with CSS variables"""
    for pattern, replacement in REPLACEMENTS.items():
        content = re.sub(pattern, replacement, content)
    return content

def clean_empty_lines(content):
    """Remove excessive empty lines"""
    return re.sub(r'\n{3,}', '\n\n', content)

def remove_orphan_braces(content):
    """Remove NOTHING - braces are needed for CSS"""
    return content

for filepath in files:
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply transformations
    content = remove_media_queries(content)
    content = apply_replacements(content)
    content = remove_orphan_braces(content)
    content = clean_empty_lines(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated {filepath}")

print("\n✅ All files processed!")
