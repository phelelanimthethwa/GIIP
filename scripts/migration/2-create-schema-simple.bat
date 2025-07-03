@echo off
REM Phase A - Step 2: Create Default Conference Schema (Simple CLI Version)
REM This script uses Firebase CLI to directly create the schema

echo === GIIR Conference System - Default Conference Creation ===
echo Phase A - Step 2: Create Default Conference Schema
echo.

echo 📝 Creating default conference structure using Firebase CLI...
echo.

REM Create the default conference basic info
echo Creating default conference basic info...
firebase database:set /conferences/default-2025/basic_info "{\"name\": \"GIIR Conference 2025\", \"description\": \"Global Innovation and Intellectual Research Conference\", \"start_date\": \"2025-07-15T09:00:00Z\", \"end_date\": \"2025-07-17T17:00:00Z\", \"status\": \"active\", \"timezone\": \"UTC\", \"year\": 2025, \"location\": \"TBD\", \"website\": \"https://giir-conference.org\"}"

if errorlevel 1 (
    echo ❌ Failed to create conference basic info
    exit /b 1
)

REM Create conference settings
echo Creating conference settings...
firebase database:set /conferences/default-2025/settings "{\"registration_enabled\": true, \"paper_submission_enabled\": true, \"review_enabled\": true, \"email_notifications\": true, \"max_registrations\": 1000, \"max_paper_submissions\": 500}"

if errorlevel 1 (
    echo ❌ Failed to create conference settings
    exit /b 1
)

REM Create conference metadata
echo Creating conference metadata...
firebase database:set /conferences/default-2025/metadata "{\"created_at\": %date:~6,4%%date:~3,2%%date:~0,2%, \"created_by\": \"migration-script\", \"version\": \"1.0.0\", \"migrated_from\": \"single-conference-system\"}"

if errorlevel 1 (
    echo ❌ Failed to create conference metadata
    exit /b 1
)

REM Create global settings
echo Creating global settings...
firebase database:set /global_settings/system_configuration "{\"default_conference\": \"default-2025\", \"multi_conference_enabled\": true, \"migration_version\": \"1.0.0\"}"

if errorlevel 1 (
    echo ❌ Failed to create global settings
    exit /b 1
)

echo.
echo ✅ Default conference structure created successfully
echo.
echo 🔍 Verification:
echo   📂 conferences/default-2025 - Contains conference-specific data
echo   📂 global_settings - Contains system-wide configuration
echo.
echo Next step: Deploy security rules
echo Run: node 3-deploy-security-rules.js (or manual rules deployment)
echo.

pause 