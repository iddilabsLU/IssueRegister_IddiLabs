# Issue Register — Bug Fixes and Enhancements

> **Status:** COMPLETE
> **Last Updated:** 2025-12-31
> **All items below have been implemented and tested.**

---

## 1. Issue Register View

### 1.1 Missing Filter: Identified By
**Status:** COMPLETE
**Implementation:** Added multi-select dropdown filter for "Identified By" field in `src/ui/widgets/filter_panel.py:171-175`.

### 1.2 Missing Filter: Identification Date
**Status:** COMPLETE
**Implementation:** Added date range filter (from/to) for "Identification Date" in `src/ui/widgets/filter_panel.py:203-227`.

### 1.3 Multi-Select Behaviour for Filters
**Status:** COMPLETE
**Implementation:** Created `MultiSelectComboBox` widget class in `src/ui/widgets/filter_panel.py:18-116`. All dropdown filters now support multi-select with checkboxes. OR logic within filters, AND logic between filters.

### 1.4 Dropdown Placeholder Text
**Status:** COMPLETE
**Implementation:** Editable comboboxes display "Select or type new..." placeholder. See `src/ui/issue_dialog.py:101,107,113,119`.

### 1.5 Collapse filter section
**Status:** COMPLETE
**Implementation:** Created `CollapsibleFilterPanel` class in `src/ui/widgets/filter_panel.py:359-455`. Blue vertical strip with "FILTERS" text when collapsed.

---

## 2. Dashboard View

### 2.1 Dashboard Filters
**Status:** COMPLETE
**Implementation:** Dashboard uses `CollapsibleFilterPanel` with independent filters. See `src/ui/dashboard.py:49-53`. Filters update all KPI cards and charts.

### 2.2 KPI Cards Text Truncation
**Status:** COMPLETE
**Implementation:** Fixed card sizing in `src/ui/widgets/kpi_card.py:47-58`. Added word wrap, minimum heights, and proper width handling.

---

## 3. Settings

### 3.1 Export Users List
**Status:** COMPLETE
**Implementation:** "Export Users" button added in `src/ui/settings.py:150-159`. Handler at lines 410-432. Exports Username, Role, Departments to Excel.

### 3.2 Audit Log Implementation
**Status:** COMPLETE
**Implementation:**
- Database table created in `src/database/migrations.py`
- Audit service in `src/services/audit.py`
- Logs: issue CRUD, status changes, user actions, settings changes
- Export button in `src/ui/settings.py:161-170`
- Export handler at lines 434-455

### 3.3 Editor Department Restrictions
**Status:** COMPLETE
**Implementation:** Editor can have View and Edit department restrictions. UI in `src/ui/settings.py:608-641` with separate lists for view/edit departments.

---

## 4. Packaging

### 4.1 PyInstaller Build Guide
**Status:** COMPLETE
**Implementation:**
- `BUILD.md` created with step-by-step instructions
- `build.bat` working correctly
- `IssueRegister.spec` configured for proper build

---

## 5. Documentation

### 5.1 Update Project Documentation
**Status:** COMPLETE
**Implementation:** Documentation updated:
- `CLAUDE.md` - Project overview and patterns
- `BUILD.md` - Build instructions
- `FIXES.md` - This file (marked complete)

---

## Testing Checklist

All items verified:

- [x] All filters work independently and in combination
- [x] Multi-select filters show correct results (OR within, AND between)
- [x] Dropdown placeholders display "Select or type new..."
- [x] Dashboard filters update all visualisations
- [x] KPI card text is fully visible
- [x] User export generates valid Excel
- [x] Audit log captures all specified actions
- [x] Audit log export works for Admin and Editor
- [x] Editor department restrictions work correctly
- [x] .exe builds without errors
- [x] Documentation matches current functionality

---

## Test Coverage

**187 tests passing** covering:
- Database operations (connection, models, queries)
- Authentication service
- Permission service
- Issue service (CRUD, status transitions, dashboard data)
- Audit service (logging, filtering)
- Export service (Excel, backup/restore)

---

*All enhancements complete.*
