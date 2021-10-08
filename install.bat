@ECHO OFF

rem Installation script for Windows.
rem This script expects that only one python is in PATH.Windows.

SET VENV_DIR=.venv
SET VENV_PYTHON=.venv\Scripts\python.exe

rem Check if .venv directory exists
IF EXIST .venv\ (
  ECHO Virtual environment exists, quit!
  EXIT /b 1
)

rem Get count of installed pythons
FOR /F "tokens=* USEBACKQ" %%F IN (`where python^|find /v /c ""`) DO (
    SET PYTHON_COUNT=%%F
)
IF "%PYTHON_COUNT%"=="0" (
    ECHO No python found, install python to proceed!
    EXIT /b 1
)
IF "%PYTHON_COUNT%"=="1" (
    rem Get python path
    FOR /F "tokens=* USEBACKQ" %%F IN (`where python`) DO (
        SET PYTHON=%%F
    )
    CALL:installVenv
)
IF "%PYTHON_COUNT%" gtr "1" (
    ECHO "More than 1 python installed, cannot decide!"
    rem Here could be logic to choose wanted python.
    EXIT /b 1
)

:installVenv
rem Print python path
ECHO Using system's python to create .venv: %PYTHON%
rem Create virtual environment
%PYTHON% -m venv %VENV_DIR%
rem Activate virtual environment, upgrade pip, install package defined in setup.py
.venv\Scripts\activate && %VENV_PYTHON% -m pip install --upgrade pip && %VENV_PYTHON% -m pip install -e .[dev]
EXIT /b 0