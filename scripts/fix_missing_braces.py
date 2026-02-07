#!/usr/bin/env python3
"""
Fix missing closing braces in Vue script sections
"""
import re

files = [
    r"d:\provemaps_beta\frontend\src\components\Configuration\BulkMessageModal.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactGroupManager.vue",
    r"d:\provemaps_beta\frontend\src\components\Configuration\ContactImportModal.vue"
]

def fix_script_braces(filepath):
    """Find and fix missing } before </ pattern"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: Find lines ending with } followed by empty line then </script or // comment
    # Add missing } before </script or before watch/Methods sections
    
    # Fix pattern 1: } followed by blank line then comment or </script
    content = re.sub(
        r'(\s*}\s*\n)\n((?:  )?(?://|</script))',
        r'\1}\n\n\2',
        content
    )
    
    return content

for filepath in files:
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find <script section
    script_start = -1
    script_end = -1
    
    for i, line in enumerate(lines):
        if '<script' in line:
            script_start = i
        if '</script>' in line and script_start >= 0:
            script_end = i
            break
    
    if script_start < 0:
        print(f"  No <script> found, skipping")
        continue
    
    # Analyze braces in script section
    brace_depth = 0
    for i in range(script_start+1, script_end):
        line = lines[i]
        brace_depth += line.count('{') - line.count('}')
        
        # If we hit depth 0 and next non-empty line is // or </script, check previous line
        if brace_depth == 0 and i < script_end - 1:
            next_line = lines[i+1].strip()
            if next_line == '' and i < script_end - 2:
                next_next = lines[i+2].strip()
                if next_next.startswith('//') or next_next.startswith('</script'):
                    # Current line should end with }, check if it does
                    if not lines[i].rstrip().endswith('}'):
                        print(f"  Line {i+1}: Adding missing }} after: {lines[i].strip()[:50]}")
                        lines[i] = lines[i].rstrip() + '\n}\n'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✓ Fixed {filepath}")

print("\n✅ Done!")
