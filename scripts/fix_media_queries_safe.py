#!/usr/bin/env python3
"""
Fix Vue files: Remove @media dark mode blocks SAFELY by tracking braces correctly
"""

def fix_vue_file(filepath):
    """Remove @media dark blocks while preserving all other code"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    result = []
    skip_mode = False
    brace_depth = 0
    media_start_line = -1
    
    for i, line in enumerate(lines):
        # Check if we're starting a media query
        if '@media' in line and 'prefers-color-scheme' in line and 'dark' in line:
            skip_mode = True
            media_start_line = i
            # Count braces in this line
            brace_depth = line.count('{') - line.count('}')
            print(f"  Line {i+1}: Found @media dark start, depth={brace_depth}")
            continue  # Skip this line
        
        if skip_mode:
            # Count braces
            brace_depth += line.count('{') - line.count('}')
            print(f"  Line {i+1}: Skipping (depth={brace_depth}): {line.strip()[:50]}")
            
            # If depth reaches 0, we've closed the media block
            if brace_depth == 0:
                skip_mode = False
                print(f"  Line {i+1}: Media block ended")
            continue  # Skip all lines inside media block
        
        # Normal line - keep it
        result.append(line)
    
    return result

files = [
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactList.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactEditModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\BulkMessageModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactGroupManager.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactImportModal.vue"
]

for filepath in files:
    print(f"\nProcessing {filepath}...")
    try:
        fixed_lines = fix_vue_file(filepath)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        
        print(f"✓ Fixed {filepath}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n✅ Done!")
