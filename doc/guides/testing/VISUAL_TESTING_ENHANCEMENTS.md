# Device Import Enhancements - Visual Testing Guide

**Quick 5-Minute Test** | **Date**: 2025-11-22

---

## 🚀 Access the System

1. Open browser: `http://localhost:8000`
2. Log in with your credentials
3. Navigate to **Device Import** section

---

## ✅ Test 1: Skeleton Loader (30 seconds)

**What to Look For**: Animated loading placeholder instead of spinner

### Steps:
1. Refresh page (F5 or Ctrl+R)
2. Observe loading animation

### Expected Result:
- ✅ See **gray animated bars** (skeleton) while data loads
- ✅ Smooth transition to actual device table
- ❌ NO simple spinner animation

### Screenshot:
```
┌─────────────────────────────────┐
│  Loading...                     │
│  ▓▓▓▓▓▓▓░░░░░░░ (animated)     │
│  ▓▓▓▓░░░░░░░░░░                │
│  ▓▓▓▓▓▓░░░░░░░░                │
└─────────────────────────────────┘
```

---

## ✅ Test 2: Frontend Validation (2 minutes)

**What to Look For**: Error messages for invalid data

### Steps:
1. Click "➕ Novo Dispositivo" or "Importar Selecionados"
2. In the modal, enter:
   - **Nome**: `AB` (too short)
   - **IP**: `999.999.999.999` (invalid format)
3. Click "Salvar"

### Expected Result:
- ✅ **Red toast notification** appears (top-right corner)
- ✅ Message: "Validação Falhou" with error details
- ✅ Modal **stays open** (not saved)
- ❌ NO data sent to backend

### Valid Data Test:
1. Change to valid data:
   - **Nome**: `Router-Test-01`
   - **IP**: `192.168.1.100`
2. Click "Salvar"

### Expected Result:
- ✅ **Green toast notification**: "Importação Concluída"
- ✅ Modal closes
- ✅ Device appears in inventory table

---

## ✅ Test 3: Delete Confirmation (1 minute)

**What to Look For**: Confirmation dialog before deletion

### Steps:
1. In the **Inventário** tab, find any device
2. Click the **🗑️ Trash icon** (red button on the right)

### Expected Result:
- ✅ **Confirmation modal** appears
- ✅ Title: "Confirmar Exclusão"
- ✅ Message includes device name: `Tem certeza que deseja excluir "Router-Test-01"?`
- ✅ Two buttons: **"Cancelar"** (gray) and **"Excluir"** (red)

### Test Cancel:
1. Click **"Cancelar"**

### Expected Result:
- ✅ Modal closes
- ✅ Device **still exists** in table

### Test Confirm:
1. Click trash icon again
2. Click **"Excluir"** (red button)

### Expected Result:
- ✅ **Green toast**: "Dispositivo Excluído"
- ✅ Device **disappears** from table
- ✅ Table refreshes automatically

---

## ✅ Test 4: CSV Export (1 minute)

**What to Look For**: Downloaded CSV file with correct data

### Steps:
1. In the **Inventário** tab (make sure you have some devices)
2. Click **"📄 Exportar CSV"** button (green button in header)

### Expected Result:
- ✅ **Green toast**: "Exportação Concluída"
- ✅ File downloads: `inventario_2025-11-22.csv` (with today's date)

### Verify CSV Content:
1. Open downloaded CSV in Excel or text editor
2. Check columns:

```csv
ID,Nome,IP,Categoria,Grupo,Site,...
1,Router-Core-01,192.168.1.1,backbone,Core Network,Data Center,...
2,OLT-Central,192.168.2.10,gpon,GPON Equipment,Central Office,...
```

### Expected Result:
- ✅ All devices present
- ✅ UTF-8 characters display correctly (ã, é, ç, etc.)
- ✅ Commas in data are properly escaped
- ✅ 10+ columns present

---

## ✅ Test 5: Zabbix Preview CSV Export (30 seconds)

### Steps:
1. Switch to **"Sincronização (Pré)"** tab
2. Click **"📄 Exportar CSV"** button

### Expected Result:
- ✅ **Green toast**: "Exportação Concluída"
- ✅ File downloads: `zabbix_preview_2025-11-22.csv`
- ✅ Contains Zabbix hosts data

---

## 🎨 Visual Indicators to Look For

### Success States:
- ✅ **Green toast** (top-right): Success messages
- ✅ **Green button**: Export CSV
- ✅ **Smooth animations**: Skeleton → Data, Modal fade in/out

### Error States:
- ❌ **Red toast**: Validation errors, deletion errors
- ❌ **Red button**: Delete confirmation
- ❌ **Red border**: Invalid fields (if added to modal in future)

### Loading States:
- ⏳ **Skeleton bars**: Animated gray placeholders
- ⏳ **Spinner in button**: During save/delete API calls

---

## 🐛 Common Issues to Check

### Issue 1: No Skeleton, Just Spinner
**Cause**: Old cached files  
**Fix**: Hard refresh (Ctrl+Shift+R) or clear browser cache

### Issue 2: Validation Not Working
**Symptom**: Invalid data saves successfully  
**Check**: Browser console for JavaScript errors  
**Fix**: Rebuild frontend (`npm run build`) and restart container

### Issue 3: Delete Button Not Appearing
**Symptom**: Only "Configurar" button visible  
**Check**: InventoryManagerTab.vue was updated correctly  
**Fix**: Hard refresh browser

### Issue 4: CSV Download Not Starting
**Symptom**: Click export, nothing happens  
**Check**: Browser console for errors  
**Fix**: Check if browser is blocking downloads (check browser settings)

---

## 📊 Success Criteria

**All Tests Pass**:
- ✅ Skeleton loader appears during load
- ✅ Invalid data shows error notification
- ✅ Valid data saves successfully
- ✅ Delete confirmation works (both cancel and confirm)
- ✅ CSV exports successfully with correct data

**Performance**:
- ✅ No lag when opening modals
- ✅ CSV export completes in < 2 seconds
- ✅ No JavaScript errors in console

**UX**:
- ✅ Toast notifications are clear and helpful
- ✅ Modals have smooth animations
- ✅ Buttons are visually distinct (green=export, red=delete)

---

## 🔍 Browser Console Checks

### No Errors Should Appear:
```javascript
// Open DevTools (F12) → Console tab
// Expected: No red errors

// Warnings are OK (Vue devtools, etc.)
// Errors are NOT OK
```

### Network Tab Checks:
```
Filter: XHR/Fetch
Expected requests:
- GET /api/v1/inventory/devices/grouped/  → 200 OK
- POST /api/v1/inventory/devices/import-batch/ → 200 OK (when saving)
- DELETE /api/v1/inventory/devices/<id>/ → 200 OK (when deleting)
```

---

## 📝 Quick Checklist (Print & Check Off)

```
[ ] Skeleton loader appears during page load
[ ] Invalid device name (AB) shows error
[ ] Invalid IP (999.999.999.999) shows error
[ ] Valid device saves successfully
[ ] Delete button appears on devices
[ ] Delete confirmation modal shows correct device name
[ ] Cancel button works (device not deleted)
[ ] Confirm button deletes device
[ ] Success toast appears after deletion
[ ] Export CSV downloads file
[ ] CSV file opens in Excel correctly
[ ] UTF-8 characters display correctly in CSV
[ ] No JavaScript errors in console
[ ] All buttons are visually distinct
[ ] Toast notifications auto-dismiss after a few seconds
```

---

## 🎯 Expected Time: 5 minutes

**If all tests pass**: ✅ Ready for commit and deployment  
**If any test fails**: See troubleshooting section or check console logs

---

**Happy Testing!** 🚀
