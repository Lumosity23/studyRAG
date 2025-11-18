@echo off
REM StudyRAG - Script de Setup Simple pour Windows
REM Lance le setup PowerShell avec les bonnes permissions

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                StudyRAG - Setup Windows                      ║
echo ║              Installation automatique complète               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Vérifier si PowerShell est disponible
powershell -Command "Write-Host 'PowerShell détecté'" >nul 2>&1
if errorlevel 1 (
    echo ❌ PowerShell requis mais non trouvé
    echo Installez PowerShell depuis: https://github.com/PowerShell/PowerShell
    pause
    exit /b 1
)

echo 🔧 Lancement du setup automatique...
echo.
echo ⚠️  IMPORTANT: Ce script va installer:
echo    • Chocolatey (gestionnaire de paquets)
echo    • Python 3.11
echo    • Git
echo    • PostgreSQL 15
echo    • UV (gestionnaire dépendances Python)
echo    • Ollama (LLM local)
echo.

set /p confirm="Continuer l'installation ? [Y/n]: "
if /i "%confirm%"=="n" (
    echo Installation annulée
    pause
    exit /b 0
)

echo.
echo 🚀 Démarrage de l'installation...
echo.

REM Exécuter le script PowerShell avec privilèges administrateur
powershell -Command "Start-Process PowerShell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0setup.ps1\"' -Verb RunAs -Wait"

if errorlevel 1 (
    echo.
    echo ❌ Erreur lors de l'installation
    echo Consultez SETUP.md pour le dépannage
) else (
    echo.
    echo ✅ Installation terminée !
    echo.
    echo Prochaines étapes:
    echo 1. Ouvrir PowerShell dans ce dossier
    echo 2. Exécuter: uv run python -m ingestion.ingest --documents test_samples/
    echo 3. Exécuter: uv run python cli.py
)

echo.
pause