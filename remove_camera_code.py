#!/usr/bin/env python3
"""Remove legacy camera code from SiteDetailsModal.vue"""

import re

# Read the file
with open(r'd:\provemaps_beta\frontend\src\components\SiteDetailsModal.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove legacy refs (13 refs)
legacy_refs = [
    "const showCameraModal = ref(false)\n",
    "const cameras = ref([])\n",
    "const loadingCameras = ref(false)\n",
    "const cameraVideoRefs = ref({})\n",
    "const cameraConnections = ref({})\n",
    "const cameraCount = ref(0)\n",
    "const showMosaicModal = ref(false)\n",
    "const currentMosaic = ref(null)\n",
    "const mosaicCameras = ref([])\n",
    "const loadingMosaic = ref(false)\n",
    "const mosaicVideoRefs = ref({})\n",
    "const mosaicConnections = ref({})\n",
    "const hasConnectedMosaic = ref(false)\n",
]

for ref in legacy_refs:
    content = content.replace(ref, "")

# Remove imports
content = content.replace("import { useWebRTC } from '@/composables/useWebRTC'\n", "")
content = content.replace("import CameraPlayer from '@/components/Video/CameraPlayer.vue'\n", "")

# Find and remove all camera functions (from resolveConnectionKey to connectCameraWithFallback)
# Pattern: from "const resolveConnectionKey" to just before "const isDark"
pattern = r'const resolveConnectionKey = \(cameraLike, fallback\) => \{.*?^const isDark = computed'
content = re.sub(pattern, 'const isDark = computed', content, flags=re.MULTILINE | re.DOTALL)

print("✅ Removed legacy refs and imports")
print("✅ Removed camera functions")

# Remove camera functions after loadDevices
pattern2 = r'const openCameraModal = async.*?^const saveDevice = async'
content = re.sub(pattern2, 'const saveDevice = async', content, flags=re.MULTILINE | re.DOTALL)

print("✅ Removed openCameraModal and related functions")

# Remove computeds
content = re.sub(r'const getCameraGridClass = computed\(\(\) => \{[^}]+\}\)\n\n', '', content, flags=re.MULTILINE)
content = re.sub(r'const getMosaicGridClass = computed\(\(\) => \{[^}]+\}\)\n\n', '', content, flags=re.MULTILINE)

print("✅ Removed computed properties")

# Remove old camera modal from template
pattern3 = r'<!-- Camera Modal -->.*?</Teleport>\n\n  <!-- Mosaic Viewer Modal -->'
content = re.sub(pattern3, '<!-- Mosaic Viewer Modal -->', content, flags=re.DOTALL)

print("✅ Removed camera modal from template")

# Remove mosaic modal from template  
pattern4 = r'<!-- Mosaic Viewer Modal -->.*?</Teleport>\n\n  <!-- Cameras Tab Modal -->'
content = re.sub(pattern4, '<!-- Cameras Tab Modal -->', content, flags=re.DOTALL)

print("✅ Removed mosaic modal from template")

# Fix watch statement - remove loadCameraCount and close modal calls
pattern5 = r"watch\(\(\) => props\.isOpen, \(newVal\) => \{.*?\}\)"
replacement5 = """watch(() => props.isOpen, (newVal) => {
  if (newVal && props.site) {
    loadDevices()
  }
})"""
content = re.sub(pattern5, replacement5, content, flags=re.DOTALL)

print("✅ Fixed watch statement")

# Write back
with open(r'd:\provemaps_beta\frontend\src\components\SiteDetailsModal.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ All legacy camera code removed successfully!")
print(f"File size reduced from 2839 to approximately {len(content.splitlines())} lines")
