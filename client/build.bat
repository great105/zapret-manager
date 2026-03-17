@echo off
chcp 65001 >nul
echo ============================================
echo   Сборка Zapret Manager
echo ============================================
echo.

:: 1. Зависимости
echo [1/4] Установка зависимостей...
pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

:: 2. Скачиваем бинарники zapret2 (если ещё не скачаны)
if not exist "binaries\winws2.exe" (
    echo [2/4] Скачивание бинарников zapret2 с GitHub...
    python download_zapret2.py
    if errorlevel 1 (
        echo.
        echo ОШИБКА: не удалось скачать бинарники.
        echo Скачайте вручную и положите в папку binaries\
        echo   - winws2.exe
        echo   - WinDivert.dll
        echo   - WinDivert64.sys
        pause
        exit /b 1
    )
) else (
    echo [2/4] Бинарники zapret2 уже есть
)

:: 3. Проверяем все файлы на месте
echo [3/4] Проверка файлов...
set MISSING=0
if not exist "binaries\winws2.exe" (
    echo   ОТСУТСТВУЕТ: binaries\winws2.exe
    set MISSING=1
)
if not exist "binaries\WinDivert.dll" (
    echo   ОТСУТСТВУЕТ: binaries\WinDivert.dll
    set MISSING=1
)
if not exist "binaries\WinDivert64.sys" (
    echo   ОТСУТСТВУЕТ: binaries\WinDivert64.sys
    set MISSING=1
)
if %MISSING%==1 (
    echo.
    echo ОШИБКА: не все бинарники на месте!
    pause
    exit /b 1
)
echo   Все файлы на месте.

:: 4. Сборка .exe
echo [4/4] Сборка ZapretManager.exe...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "ZapretManager" ^
    --add-data "binaries;binaries" ^
    --hidden-import customtkinter ^
    --collect-all customtkinter ^
    --uac-admin ^
    main.py

if errorlevel 1 (
    echo.
    echo ОШИБКА СБОРКИ!
    pause
    exit /b 1
)

:: Копируем .exe также в папку для обновлений сервера
if exist "..\server\updates" (
    copy /y "dist\ZapretManager.exe" "..\server\updates\ZapretManager.exe" >nul
    echo.
    echo Копия для обновлений: ..\server\updates\ZapretManager.exe
)

echo.
echo ============================================
echo   ГОТОВО!
echo ============================================
echo.
echo   Файл: dist\ZapretManager.exe
echo.
echo   Этот файл — всё, что нужно пользователю.
echo   В нём встроены бинарники zapret2.
echo   Пользователь просто запускает и нажимает кнопку.
echo.
echo   Для раздачи обновлений:
echo     1. Увеличь версию в client\version.py
echo     2. Пересобери: build.bat
echo     3. Увеличь версию в server\versions.json
echo     4. .exe автоматически скопирован в server\updates\
echo.
pause
