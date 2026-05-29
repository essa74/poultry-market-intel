@echo off
REM Database backup script for Poultry Market Intel (Windows)
REM Usage: scripts\backup_postgres.bat [container_name] [db_user] [db_name]
REM
REM Defaults (matching docker-compose.prod.yml):
REM   container: poultry-market-intel-db-1
REM   db_user:   poultry
REM   db_name:   poultry_market

setlocal

set BACKUP_DIR=.\backups
set CONTAINER=%1
if "%CONTAINER%"=="" set CONTAINER=poultry-market-intel-db-1
set DB_USER=%2
if "%DB_USER%"=="" set DB_USER=poultry
set DB_NAME=%3
if "%DB_NAME%"=="" set DB_NAME=poultry_market

REM Generate timestamp: YYYYMMDD_HHMMSS
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DATETIME=%%I
set TIMESTAMP=%DATETIME:~0,8%_%DATETIME:~8,6%
set FILENAME=%BACKUP_DIR%\%DB_NAME%_%TIMESTAMP%.sql

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo ^> Backing up %DB_NAME% from container %CONTAINER% ...
docker exec "%CONTAINER%" pg_dump -U "%DB_USER%" "%DB_NAME%" > "%FILENAME%"

if %ERRORLEVEL% equ 0 (
  echo ^| Backup saved: %FILENAME%
) else (
  echo ERROR: Backup failed
  exit /b 1
)

REM Keep only last 14 daily backups
echo ^> Cleaning backups older than 14 days ...
forfiles /p "%BACKUP_DIR%" /m %DB_NAME%_*.sql /d -14 /c "cmd /c del @path" 2>nul

echo ^| Done.
endlocal
