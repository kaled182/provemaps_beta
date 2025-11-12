# Sprint 1 QA Testing Checklist
## Filters & Search System - Staging Validation

**Version:** 1.0.0  
**Target Environment:** Staging  
**Test Date:** _______________  
**Tester:** _______________  
**Browser:** _______________  
**OS:** _______________

---

## ✅ Functional Testing

### 1. Filter System (Status)

#### 1.1 Single Selection
- [ ] Click "Status" dropdown opens
- [ ] Shows all status options: Operational, Warning, Critical, Offline, Unknown
- [ ] Each option has emoji icon
- [ ] Click "Operational" filters devices
- [ ] Device count updates
- [ ] URL updates with `?status=operational`
- [ ] Dropdown shows (1) badge

#### 1.2 Multi Selection
- [ ] Click "Operational" + "Warning" both selected
- [ ] Devices show both statuses
- [ ] URL updates with `?status=operational,warning`
- [ ] Dropdown shows (2) badge
- [ ] Filter count shows "2 filters active"

#### 1.3 Clear Filters
- [ ] Click "X" in dropdown clears status filters
- [ ] All devices shown again
- [ ] URL updates (removes status param)
- [ ] Dropdown badge disappears
- [ ] Filter count updates

---

### 2. Filter System (Type)

#### 2.1 Single Selection
- [ ] Click "Type" dropdown opens
- [ ] Shows all types: OLT, Switch, Router, Server, Firewall, AP
- [ ] Click "Router" filters to routers only
- [ ] Device count updates
- [ ] URL updates with `?type=router`

#### 2.2 Multi Selection
- [ ] Select "Router" + "Switch"
- [ ] Shows both device types
- [ ] URL updates with `?type=router,switch`
- [ ] Dropdown badge shows (2)

#### 2.3 Combination with Status
- [ ] Status "Offline" + Type "Router" selected
- [ ] Shows only offline routers
- [ ] URL has both params: `?status=offline&type=router`
- [ ] Both dropdowns show badges

---

### 3. Filter System (Location)

#### 3.1 Dynamic Options
- [ ] "Location" dropdown shows real site names
- [ ] Options match available locations in data
- [ ] No duplicate locations

#### 3.2 Location Filtering
- [ ] Select a location
- [ ] Shows only devices from that site
- [ ] URL updates with `?location=SITE_NAME`
- [ ] Works with status + type filters

#### 3.3 Multiple Locations
- [ ] Select 2+ locations
- [ ] Shows devices from all selected sites
- [ ] URL lists all locations comma-separated

---

### 4. Search Functionality

#### 4.1 Basic Search
- [ ] Type in search box
- [ ] Search icon visible on left
- [ ] Placeholder text: "Search by hostname, IP, or site..."
- [ ] Clear button (X) appears when typing
- [ ] Search debounces (300ms delay)

#### 4.2 Search by Hostname
- [ ] Type partial hostname (e.g., "core")
- [ ] Shows matching devices
- [ ] Device count updates
- [ ] URL updates with `?q=core`

#### 4.3 Search by IP
- [ ] Type IP address (e.g., "192.168")
- [ ] Shows devices with matching IPs
- [ ] Partial IP works

#### 4.4 Search by Site
- [ ] Type site name
- [ ] Shows devices from that site
- [ ] Matches partial site names

#### 4.5 Fuzzy Matching
- [ ] Type hostname with typo (e.g., "corr" instead of "core")
- [ ] Still finds "core" devices
- [ ] Tolerates 1-2 character errors
- [ ] Shows best matches first

---

### 5. Autocomplete Suggestions

#### 5.1 Dropdown Display
- [ ] Focus search input shows suggestions
- [ ] Blur hides suggestions (after 200ms delay)
- [ ] Suggestions appear below input
- [ ] Max 10 suggestions shown
- [ ] Dropdown has shadow/border

#### 5.2 Device Suggestions
- [ ] Each suggestion shows:
  - [ ] Status emoji (✅ ⚠️ 🔴 ⚫ 🔵)
  - [ ] Device name (bold)
  - [ ] Device type (small text)
  - [ ] Site name (small text)
- [ ] Click suggestion selects device
- [ ] Search input updates with device name
- [ ] Suggestions dropdown closes

#### 5.3 Search History
- [ ] When input empty, shows recent searches
- [ ] Clock icon for history items
- [ ] Shows last 5 searches
- [ ] Click history item searches again
- [ ] History persists after refresh (localStorage)

#### 5.4 Empty State
- [ ] Type query with no results
- [ ] Shows "No devices found matching 'xyz'"
- [ ] Message is helpful

#### 5.5 Keyboard Navigation
- [ ] Arrow Down selects first suggestion
- [ ] Arrow Up/Down navigates suggestions
- [ ] Selected suggestion highlighted
- [ ] Enter key selects highlighted suggestion
- [ ] Escape key closes dropdown
- [ ] Tab moves to next field

---

### 6. URL Persistence

#### 6.1 URL Updates
- [ ] Changing filters updates URL
- [ ] Changing search updates URL
- [ ] URL updates are debounced (500ms)
- [ ] No duplicate history entries
- [ ] URL is readable/shareable

#### 6.2 URL Format
- [ ] Status: `?status=offline,warning`
- [ ] Type: `&type=router,switch`
- [ ] Location: `&location=HQ,DC1`
- [ ] Search: `&q=core-router`
- [ ] Multiple params combined correctly

#### 6.3 Bookmark/Reload
- [ ] Apply filters + search
- [ ] Copy URL
- [ ] Reload page (F5)
- [ ] Filters restored from URL
- [ ] Search query restored
- [ ] Results match

#### 6.4 Share URL
- [ ] Copy URL with filters
- [ ] Open in new tab/incognito
- [ ] Same filters applied
- [ ] Same search query
- [ ] Same results shown

#### 6.5 Browser Navigation
- [ ] Apply filter A
- [ ] Apply filter B
- [ ] Click browser Back button
- [ ] Filter A restored
- [ ] Click browser Forward button
- [ ] Filter B restored

---

### 7. Combined Filters & Search

#### 7.1 Filter Then Search
- [ ] Select status "Offline"
- [ ] Type search query
- [ ] Shows offline devices matching query
- [ ] URL has both params

#### 7.2 Search Then Filter
- [ ] Type search query
- [ ] Select type "Router"
- [ ] Shows routers matching query
- [ ] URL has both params

#### 7.3 Clear All
- [ ] Apply multiple filters + search
- [ ] Click "Clear All" button
- [ ] All filters cleared
- [ ] Search cleared
- [ ] URL cleared
- [ ] All devices shown

---

## ♿ Accessibility Testing

### 8. Keyboard Navigation

#### 8.1 Tab Order
- [ ] Tab key navigates in logical order:
  1. Search input
  2. Status dropdown
  3. Type dropdown
  4. Location dropdown
  5. Clear All button
- [ ] No keyboard traps
- [ ] Focus visible on all elements

#### 8.2 Search Input
- [ ] Tab to search input focuses it
- [ ] Type to search works
- [ ] Arrow keys navigate suggestions
- [ ] Enter selects suggestion
- [ ] Escape closes suggestions

#### 8.3 Dropdowns
- [ ] Tab to dropdown focuses trigger
- [ ] Enter/Space opens dropdown
- [ ] Arrow keys navigate options
- [ ] Space toggles checkbox
- [ ] Escape closes dropdown
- [ ] Tab moves to next field

#### 8.4 Clear Button
- [ ] Tab to "Clear All" button
- [ ] Enter/Space clears filters
- [ ] Focus returns to first filter

---

### 9. Screen Reader

#### 9.1 ARIA Labels
- [ ] Search input has label: "Search devices by name, IP, or site"
- [ ] Search has role: "combobox"
- [ ] Suggestions have role: "listbox"
- [ ] Filter region labeled: "Filter controls"
- [ ] Filter count announces: "2 filters active"

#### 9.2 Announcements
- [ ] Typing in search announces suggestion count
- [ ] Selecting filter announces filter applied
- [ ] Clearing filters announces "filters cleared"
- [ ] Error states announced with role="alert"
- [ ] Loading states announced with aria-busy

#### 9.3 Dynamic Content
- [ ] Filter count updates announced (aria-live="polite")
- [ ] Search results count announced
- [ ] Empty states announced

#### 9.4 Hidden Elements
- [ ] Decorative icons have aria-hidden="true"
- [ ] Screen reader hints present (.sr-only)
- [ ] Collapsed content properly hidden

---

### 10. Visual Accessibility

#### 10.1 Color Contrast
- [ ] Text contrast ≥ 4.5:1 (WCAG AA)
- [ ] Status colors distinguishable
- [ ] Focus indicators visible (not just color)
- [ ] Links underlined or clearly styled

#### 10.2 Focus Indicators
- [ ] All interactive elements show focus
- [ ] Focus outline visible (2px minimum)
- [ ] Focus color contrasts with background
- [ ] Focus not hidden by other elements

#### 10.3 Zoom & Reflow
- [ ] Page works at 200% zoom
- [ ] No horizontal scroll at 200%
- [ ] All text readable
- [ ] No content loss

---

## 🎨 UI/UX Testing

### 11. Visual Design

#### 11.1 Layout
- [ ] FilterBar centered/aligned properly
- [ ] Search box full width
- [ ] Dropdowns aligned horizontally
- [ ] Clear All button positioned correctly
- [ ] Responsive on mobile (320px width)

#### 11.2 Spacing
- [ ] Consistent padding/margins
- [ ] Elements not too cramped
- [ ] White space balanced
- [ ] No overlapping elements

#### 11.3 Typography
- [ ] Font sizes readable (≥ 14px body text)
- [ ] Headings distinguishable
- [ ] Line height comfortable
- [ ] Font weights clear

#### 11.4 Colors
- [ ] Status colors match design:
  - Operational: Green
  - Warning: Yellow/Orange
  - Critical: Red
  - Offline: Gray
  - Unknown: Blue
- [ ] Hover states visible
- [ ] Active states clear

---

### 12. Animations & Transitions

#### 12.1 Dropdown Animations
- [ ] Dropdowns fade in smoothly
- [ ] Dropdowns fade out smoothly
- [ ] No jarring movements
- [ ] Duration feels right (200-300ms)

#### 12.2 Filter Animations
- [ ] Badge counts animate in
- [ ] Filter count updates smoothly
- [ ] Device list updates without flash

#### 12.3 Loading States
- [ ] Skeleton loader shows during initial load
- [ ] Shimmer animation smooth
- [ ] No layout shift when content loads
- [ ] Loading spinner for search (if applicable)

#### 12.4 Performance
- [ ] Animations don't lag
- [ ] Smooth at 60fps
- [ ] No jank on low-end devices

---

## 🚨 Error Handling

### 13. Network Errors

#### 13.1 API Failure
- [ ] Disconnect network
- [ ] Reload page
- [ ] Error state shows:
  - [ ] Error icon
  - [ ] Error title: "Failed to load dashboard"
  - [ ] Error message helpful
  - [ ] "Try Again" button visible
- [ ] Click "Try Again" retries request
- [ ] Error announced to screen reader (role="alert")

#### 13.2 Search Timeout
- [ ] Simulate slow network (DevTools throttling)
- [ ] Type in search
- [ ] Loading indicator shows
- [ ] If timeout, error shows
- [ ] Can retry search

---

### 14. Empty States

#### 14.1 No Devices
- [ ] Clear all filters shows all devices
- [ ] If no devices exist, shows helpful message
- [ ] Message guides user action

#### 14.2 No Search Results
- [ ] Type gibberish query
- [ ] Shows "No devices found matching 'xyz'"
- [ ] Suggests trying different query

#### 14.3 No Filter Results
- [ ] Select impossible combination (e.g., "Offline" + site with no offline devices)
- [ ] Shows empty state
- [ ] Suggests clearing filters

---

## 🚀 Performance Testing

### 15. Load Performance

#### 15.1 Initial Load
- [ ] Page loads in <2 seconds (3G)
- [ ] Time to Interactive <3 seconds
- [ ] No console errors
- [ ] No 404s for assets

#### 15.2 Bundle Size
- [ ] Check DevTools Network tab
- [ ] Main JS bundle <200KB (gzipped)
- [ ] Filters/Search code <50KB (gzipped)
- [ ] fuse.js loaded (~15KB)

#### 15.3 Search Performance
- [ ] Type query, measure response
- [ ] Search responds in <300ms
- [ ] No lag typing in input
- [ ] Debounce prevents spam

#### 15.4 Filter Performance
- [ ] Click filter, measure response
- [ ] Filter applies in <100ms
- [ ] No delay updating device list
- [ ] No memory leaks (DevTools Memory)

---

### 16. Stress Testing

#### 16.1 Large Datasets
- [ ] Test with 1000+ devices
- [ ] Search still fast (<500ms)
- [ ] Filters still responsive
- [ ] No UI freezing

#### 16.2 Rapid Interactions
- [ ] Rapidly toggle filters on/off
- [ ] Rapidly type/delete in search
- [ ] No errors in console
- [ ] UI stays responsive

#### 16.3 Memory Usage
- [ ] Open DevTools Memory
- [ ] Take heap snapshot
- [ ] Interact with filters/search for 2 minutes
- [ ] Take another snapshot
- [ ] Compare: memory increase <10MB

---

## 🌐 Browser Compatibility

### 17. Desktop Browsers

- [ ] **Chrome (latest)**
  - [ ] All features work
  - [ ] No console errors
  - [ ] Performance good
  
- [ ] **Firefox (latest)**
  - [ ] All features work
  - [ ] No console errors
  - [ ] Performance good
  
- [ ] **Safari (latest)**
  - [ ] All features work
  - [ ] No console errors
  - [ ] Performance good
  
- [ ] **Edge (latest)**
  - [ ] All features work
  - [ ] No console errors
  - [ ] Performance good

---

### 18. Mobile Browsers

- [ ] **Chrome Mobile (Android)**
  - [ ] Dropdowns work on touch
  - [ ] Search input focuses correctly
  - [ ] Virtual keyboard doesn't break layout
  
- [ ] **Safari Mobile (iOS)**
  - [ ] Dropdowns work on touch
  - [ ] Search input focuses correctly
  - [ ] No iOS-specific bugs

---

## 📱 Responsive Testing

### 19. Breakpoints

- [ ] **Desktop (1920px)**
  - [ ] Layout looks good
  - [ ] All elements visible
  
- [ ] **Laptop (1366px)**
  - [ ] Layout adapts
  - [ ] No overflow
  
- [ ] **Tablet (768px)**
  - [ ] Filters stack or wrap
  - [ ] Touch targets ≥44px
  
- [ ] **Mobile (375px)**
  - [ ] Filters stack vertically
  - [ ] Search full width
  - [ ] Dropdowns full width
  - [ ] Touch-friendly

---

## ✅ Final Validation

### 20. Smoke Tests

- [ ] User can find a device by name
- [ ] User can filter by status
- [ ] User can share a filtered view (URL)
- [ ] User can use keyboard only
- [ ] User can use screen reader
- [ ] No errors in console
- [ ] No performance issues
- [ ] Works on Chrome, Firefox, Safari, Edge

---

## 📋 Test Results Summary

**Total Tests:** _____  
**Passed:** _____  
**Failed:** _____  
**Blocked:** _____  
**Pass Rate:** _____%

### Critical Issues Found
1. _____________________
2. _____________________
3. _____________________

### Non-Critical Issues Found
1. _____________________
2. _____________________
3. _____________________

### Recommendations
1. _____________________
2. _____________________
3. _____________________

---

**QA Sign-off:**

- [ ] All critical features working
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Accessibility compliant
- [ ] Ready for production

**Tester Signature:** _____________  
**Date:** _____________  
**Status:** ✅ Approved / ❌ Rejected / ⚠️ Approved with Conditions
