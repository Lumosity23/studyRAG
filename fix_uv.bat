@echo off
REM Script simple pour diagnostiquer et corriger les problèmes UV sur Windows

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    UV Diagnostic Tool                        ║
echo ║              Résolution problème "uv non reconnu"           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo 🔍 Diagnostic UV...
echo.

REM Test 1: UV dans le PATH
where uv >nul 2>&1
if not errorlevel 1 (
    echo ✅ UV trouvé dans le PATH
    uv --version
    echo.
    echo 🎉 UV fonctionne correctement !
    echo Vous pouvez maintenant utiliser StudyRAG.
    goto :end
)

echo ❌ UV non trouvé dans le PATH
echo.

REM Test 2: Chercher UV dans les emplacements standards
echo 🔍 Recherche de UV dans les emplacements standards...

set "UV_FOUND="
set "UV_PATH="

if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_FOUND=1"
    set "UV_PATH=%USERPROFILE%\.cargo\bin"
    echo ✅ UV trouvé dans: %USERPROFILE%\.cargo\bin
)

if exist "%LOCALAPPDATA%\Programs\uv\bin\uv.exe" (
    set "UV_FOUND=1"
    set "UV_PATH=%LOCALAPPDATA%\Programs\uv\bin"
    echo ✅ UV trouvé dans: %LOCALAPPDATA%\Programs\uv\bin
)

if defined UV_FOUND (
    echo.
    echo 🔧 UV trouvé mais pas dans le PATH
    echo.
    echo Solutions:
    echo 1. REDÉMARRER votre terminal/PowerShell (solution la plus simple)
    echo 2. Ajouter manuellement au PATH:
    echo    - Ouvrir "Variables d'environnement système"
    echo    - Modifier la variable PATH utilisateur
    echo    - Ajouter: %UV_PATH%
    echo 3. Ou lancer le script PowerShell: .\fix_uv_windows.ps1
    echo.
) else (
    echo ❌ UV non trouvé dans les emplacements standards
    echo.
    echo 🔧 Solutions:
    echo 1. Réinstaller UV:
    echo    - Ouvrir PowerShell en administrateur
    echo    - Exécuter: irm https://astral.sh/uv/install.ps1 ^| iex
    echo    - Redémarrer PowerShell
    echo.
    echo 2. Installer via pip:
    echo    - pip install uv
    echo.
    echo 3. Relancer le setup complet: setup.bat
    echo.
)

:end
echo Appuyez sur une touche pour continuer...
pause >nul