@echo off
REM Schema Import Script - Uses Firebase Database Import
REM This bypasses the individual CLI write issues by importing a complete JSON structure

echo === GIIR Conference System - Schema Import ===
echo Importing multi-conference schema using Firebase database import...
echo.

REM Navigate to migration directory
cd /d "%~dp0"

echo 📁 Current directory: %CD%
echo 📄 Schema file: schema-import.json
echo.

REM Check if schema file exists
if not exist "schema-import.json" (
    echo ❌ Schema file 'schema-import.json' not found!
    echo Please ensure the file exists in the scripts/migration directory
    pause
    exit /b 1
)

echo 🔍 Schema file found. Contents preview:
echo ----------------------------------------
type schema-import.json | findstr /C:"conferences" /C:"global_settings" /C:"default-2025"
echo ----------------------------------------
echo.

echo ⚠️  WARNING: This will import the schema to your Firebase database
echo Make sure you have created a backup before proceeding!
echo.

set /p confirm="Do you want to proceed with the import? (y/N): "
if /i not "%confirm%"=="y" (
    echo Import cancelled.
    pause
    exit /b 0
)

echo.
echo 🚀 Starting schema import...
echo.

REM Method 1: Try importing to specific paths
echo === Method 1: Importing conferences collection ===
firebase database:set /conferences/default-2025 schema-import.json --data-path conferences.default-2025

if errorlevel 1 (
    echo ❌ Method 1 failed. Trying Method 2...
    goto method2
) else (
    echo ✅ Conferences collection imported successfully
    goto import_global_settings
)

:method2
echo.
echo === Method 2: Direct file import ===
firebase database:import schema-import.json

if errorlevel 1 (
    echo ❌ Method 2 failed. Trying Method 3...
    goto method3
) else (
    echo ✅ Schema imported successfully via Method 2
    goto verify_import
)

:method3
echo.
echo === Method 3: Manual JSON content import ===
echo.
echo Since automated import failed, please manually import the schema:
echo.
echo 1. Open Firebase Console: https://console.firebase.google.com/project/giir-66ae6/database
echo 2. Click the three dots menu (⋮) at the root level
echo 3. Select "Import JSON"
echo 4. Choose the file: %CD%\schema-import.json
echo 5. Click "Import"
echo.
echo Alternatively, copy and paste the JSON content manually into the console.
echo.
pause
goto verify_import

:import_global_settings
echo.
echo === Importing global_settings collection ===
firebase database:set /global_settings schema-import.json --data-path global_settings

if errorlevel 1 (
    echo ❌ Global settings import failed
    echo Please import manually via Firebase Console
) else (
    echo ✅ Global settings imported successfully
)

:verify_import
echo.
echo === Verifying Import ===
echo Running verification script...
echo.

REM Run verification script if it exists
if exist "verify-schema.js" (
    node verify-schema.js
) else (
    echo ⚠️  Verification script not found. Please run manual verification:
    echo.
    echo 1. Open Firebase Console: https://console.firebase.google.com/project/giir-66ae6/database
    echo 2. Check for 'conferences' collection with 'default-2025' conference
    echo 3. Check for 'global_settings' collection with system configuration
    echo 4. Verify all fields are present and properly structured
)

echo.
echo 🎉 Schema import process completed!
echo.
echo Next steps:
echo 1. Verify the schema was imported correctly
echo 2. Test basic application functionality
echo 3. Proceed to Phase B - Data Migration
echo.

pause 