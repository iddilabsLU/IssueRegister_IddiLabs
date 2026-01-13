@echo off
REM Issue Register - Build Script
REM Creates a single Windows executable using PyInstaller

echo ========================================
echo  Issue Register Build Script
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements-dev.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>NUL
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

echo.
echo Building executable...
echo.

REM Clean previous builds
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build the executable using the spec file (has all hidden imports configured)
pyinstaller IssueRegister.spec --clean

if errorlevel 1 (
    echo.
    echo Build FAILED!
    echo.
    echo Common issues:
    echo - Missing dependencies: pip install -r requirements-dev.txt
    echo - Antivirus blocking: Add exclusion for project folder
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build Complete!
echo ========================================
echo.
echo Executable location: dist\IssueRegister.exe
echo.
echo To run: dist\IssueRegister.exe
echo.
pause
