@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Sputnik Public

cls
echo(
echo(                 .-""""-.
echo(              .-'  CCCP  '-.
echo(             /   *      *   \
echo(            /      [O]       \
echo(            \   *      *     /
echo(             '-._______.-'
echo(                /  /I\  \
echo(               /  / I \  \
echo(              /__/  I  \__\
echo(
echo(             S P U T N I K
echo(           LOCAL JACKBOX GUARD
echo(

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_PYW=%~dp0.venv\Scripts\pythonw.exe"
set "PYTHON_EXE="

if exist "%VENV_PY%" (
    "%VENV_PY%" --version >nul 2>nul
    if not errorlevel 1 goto :install_packages
    echo Existing environment is damaged. Recreating it...
    rmdir /s /q "%~dp0.venv"
)

call :find_python
if defined PYTHON_EXE goto :create_venv

echo Python was not found. Installing it automatically...
where winget.exe >nul 2>nul
if errorlevel 1 goto :no_winget

winget install --id Python.Python.3.13 -e --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo Python 3.13 installation failed. Trying Python 3.12...
    winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :python_install_error
)

call :find_python
if not defined PYTHON_EXE goto :python_not_found_after_install

:create_venv
echo Creating a private Python environment...
"%PYTHON_EXE%" -m venv "%~dp0.venv"
if errorlevel 1 goto :venv_error
if not exist "%VENV_PY%" goto :venv_error

:install_packages
"%VENV_PY%" -c "import selenium" >nul 2>nul
if not errorlevel 1 goto :verify_project

echo Installing Selenium. This is needed only once...
"%VENV_PY%" -m pip install --disable-pip-version-check --requirement "%~dp0requirements.txt"
if errorlevel 1 goto :pip_error

:verify_project
echo Checking the application...
"%VENV_PY%" -c "import main; app=main.App(); app.root.update_idletasks(); app.root.destroy()" >nul 2>nul
if errorlevel 1 goto :app_error

if /i "%~1"=="--check" (
    echo SELF-TEST OK
    exit /b 0
)

echo Starting Sputnik Public...
start "Sputnik Public" "%VENV_PYW%" "%~dp0main.py"
if errorlevel 1 goto :start_error
exit /b 0

:find_python
for %%P in (
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
) do (
    if not defined PYTHON_EXE if exist "%%~P" set "PYTHON_EXE=%%~P"
)
exit /b 0

:no_winget
echo(
echo ERROR: Python and Windows Package Manager are missing.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH" during installation, then run START.bat again.
goto :fail

:python_install_error
echo ERROR: Windows could not install Python automatically.
echo Check the internet connection and run START.bat again.
goto :fail

:python_not_found_after_install
echo ERROR: Python was installed but could not be found.
echo Restart Windows once, then run START.bat again.
goto :fail

:venv_error
echo ERROR: Could not create the private Python environment.
goto :fail

:pip_error
echo ERROR: Could not install Selenium. Check the internet connection.
goto :fail

:app_error
echo ERROR: The application self-test failed.
echo Run this command to see details:
echo "%VENV_PY%" "%~dp0main.py"
goto :fail

:start_error
echo ERROR: Windows could not start the application.
goto :fail

:fail
echo(
pause
exit /b 1
