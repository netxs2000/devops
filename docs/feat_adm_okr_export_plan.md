# Implementation Plan - OKR Export Function

This plan outlines the steps to implement the OKR export functionality for system administrators, as requested.

## 1. Requirements Recap
- **Target**: System Administrators (Full access).
- **Filters**: Support for `period` (time window) and `status`.
- **Format**: CSV with `utf-8-sig` encoding.
- **Fields**: 
    - Objective: ID, Title, Period, Status, Overall Progress %
    - Key Result: Title, Target Value, Current Value, Unit, KR Progress %
    - Owner: Full Name
- **Location**: `AdminService` and `admin_router`.

## 2. Proposed Changes

### 2.1 Backend: `devops_collector/core/admin_service.py`
Add `export_okrs` method to `AdminService` class.
- Parameters: `period: Optional[str]`, `status: Optional[str]`.
- Logic:
    - Query `OKRObjective` with filters.
    - Join `OKRKeyResult` and `User` (Owner).
    - Generate CSV with the specified headers.
    - Calculate `Progress %` (progress * 100).

### 2.2 Backend: `devops_portal/routers/admin_router.py`
Add `GET /admin/export/okrs` endpoint.
- Protect with `RoleRequired(['SYSTEM_ADMIN'])`.
- Accept query parameters for `period` and `status`.
- Call `AdminService.export_okrs`.
- Return `StreamingResponse` with CSV data.

## 3. Execution Steps

1. **Modify `AdminService`**: Implement the `export_okrs` logic.
2. **Modify `admin_router.py`**: Add the new export endpoint.
3. **Verification**: 
    - Run the API in the Docker container.
    - Use `curl` or a test script to trigger the export with various filters.
    - Verify the CSV content and encoding.

## 4. Definition of Done (DoD)
- [ ] Export functionality implemented in `AdminService`.
- [ ] API endpoint secured and functional in `admin_router.py`.
- [ ] Filters (period, status) working as expected.
- [ ] CSV encoding is `utf-8-sig`.
- [ ] Progress % is correctly calculated and exported.
- [ ] `progress.txt` updated.
