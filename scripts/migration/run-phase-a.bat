@echo off
REM Phase A Master Execution Script for Windows
REM Runs all Phase A steps: Backup -> Create Schema -> Deploy Rules

echo ========================================================
echo     GIIR Conference System - Phase A Migration
echo       Schema Preparation for Multi-Conference
echo ========================================================
echo.

echo Phase A includes:
echo   1. Database Backup
echo   2. Create Default Conference Schema  
echo   3. Deploy Multi-Conference Security Rules
echo.

set /p confirm="Are you ready to begin Phase A migration? (y/N): "
if /i not "%confirm%"=="y" (
    echo Migration cancelled.
    exit /b 0
)

echo.
echo 🚀 Starting Phase A Migration...
echo.

REM Step 1: Database Backup
echo === Step 1: Database Backup ===
call 1-backup-database.sh
if errorlevel 1 (
    echo ❌ Database backup failed. Stopping migration.
    exit /b 1
)

echo.
echo === Step 2: Create Default Conference Schema ===
node 2-create-default-conference.js
if errorlevel 1 (
    echo ❌ Schema creation failed. Stopping migration.
    exit /b 1
)

echo.
echo === Step 3: Deploy Security Rules ===
node 3-deploy-security-rules.js
if errorlevel 1 (
    echo ❌ Security rules deployment failed. Stopping migration.
    exit /b 1
)

echo.
echo ========================================================
echo            ✅ Phase A Completed Successfully!
echo ========================================================
echo.
echo What was completed:
echo   ✅ Complete database backup created
echo   ✅ Default conference (default-2025) created
echo   ✅ Global settings migrated to conference structure
echo   ✅ Multi-conference security rules deployed
echo   ✅ Conference isolation enabled
echo.
echo Next Steps:
echo   📋 Phase B: Data Migration (users, registrations, papers)
echo   🚀 Run: run-phase-b.bat
echo.
echo 🔍 Verification:
echo   • Check Firebase console for new collections
echo   • Verify security rules are active  
echo   • Test basic application functionality
echo.

pause 