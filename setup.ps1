# StudyRAG - Script de Setup Automatique pour Windows
# Installe tout depuis zéro : Python, Git, PostgreSQL, et configure le projet

param(
    [switch]$Help,
    [switch]$SkipPython,
    [switch]$SkipPostgreSQL
)

# Configuration des couleurs
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║                StudyRAG - Setup Automatique Windows          ║" -ForegroundColor Blue  
    Write-Host "║            Installation complète depuis zéro                 ║" -ForegroundColor Blue
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

function Write-Step {
    param($Message)
    Write-Host ""
    Write-Host "🔧 $Message..." -ForegroundColor Yellow
}

function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param($Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Chocolatey {
    Write-Step "Installation de Chocolatey (gestionnaire de paquets Windows)"
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Success "Chocolatey déjà installé"
        return $true
    }
    
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        # Rafraîchir l'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Success "Chocolatey installé avec succès"
        return $true
    }
    catch {
        Write-Error "Échec de l'installation de Chocolatey: $_"
        return $false
    }
}

function Install-Python {
    if ($SkipPython) {
        Write-Warning "Installation de Python ignorée (--SkipPython)"
        return $true
    }
    
    Write-Step "Installation de Python 3.11"
    
    # Vérifier si Python est déjà installé
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion -match "Python 3\.([9-9]|1[0-9])") {
            Write-Success "Python déjà installé: $pythonVersion"
            return $true
        }
    }
    catch {
        # Python pas installé, continuer
    }
    
    try {
        choco install python311 -y
        
        # Rafraîchir l'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Vérifier l'installation
        Start-Sleep -Seconds 5
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-Success "Python installé: $pythonVersion"
            return $true
        }
        else {
            throw "Python non détecté après installation"
        }
    }
    catch {
        Write-Error "Échec de l'installation de Python: $_"
        return $false
    }
}

function Install-Git {
    Write-Step "Installation de Git"
    
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Success "Git déjà installé: $(git --version)"
        return $true
    }
    
    try {
        choco install git -y
        
        # Rafraîchir l'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Success "Git installé avec succès"
        return $true
    }
    catch {
        Write-Error "Échec de l'installation de Git: $_"
        return $false
    }
}

function Install-PostgreSQL {
    if ($SkipPostgreSQL) {
        Write-Warning "Installation de PostgreSQL ignorée (--SkipPostgreSQL)"
        return $true
    }
    
    Write-Step "Installation de PostgreSQL"
    
    # Vérifier si PostgreSQL est déjà installé
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        Write-Success "PostgreSQL déjà installé"
        return $true
    }
    
    try {
        choco install postgresql15 --params '/Password:studyrag123' -y
        
        # Rafraîchir l'environnement
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Success "PostgreSQL installé avec succès"
        Write-Warning "Mot de passe PostgreSQL: studyrag123"
        
        return $true
    }
    catch {
        Write-Error "Échec de l'installation de PostgreSQL: $_"
        return $false
    }
}

function Install-UV {
    Write-Step "Installation de UV (gestionnaire de dépendances Python)"
    
    # Vérifier si UV est déjà installé
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Success "UV déjà installé: $(uv --version)"
        return $true
    }
    
    try {
        Write-Host "Téléchargement et installation de UV..."
        
        # Installation via PowerShell (méthode officielle)
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        
        # Chemins possibles pour UV
        $uvPaths = @(
            "$env:USERPROFILE\.cargo\bin",
            "$env:LOCALAPPDATA\Programs\uv\bin",
            "$env:APPDATA\uv\bin"
        )
        
        # Trouver UV et l'ajouter au PATH
        $uvFound = $false
        foreach ($path in $uvPaths) {
            if (Test-Path "$path\uv.exe") {
                Write-Host "UV trouvé dans: $path"
                
                # Ajouter au PATH de la session actuelle
                $env:Path = "$path;$env:Path"
                
                # Ajouter au PATH permanent de l'utilisateur
                $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
                if ($currentPath -notlike "*$path*") {
                    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$path", "User")
                    Write-Host "UV ajouté au PATH permanent"
                }
                
                $uvFound = $true
                break
            }
        }
        
        if (-not $uvFound) {
            # Essayer de rafraîchir l'environnement
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            # Vérifier à nouveau
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                $uvFound = $true
            }
        }
        
        if ($uvFound) {
            Write-Success "UV installé et configuré avec succès"
            Write-Host "Version: $(uv --version)"
            return $true
        } else {
            throw "UV installé mais non trouvé dans le PATH"
        }
    }
    catch {
        Write-Error "Échec de l'installation de UV: $_"
        Write-Host "Essayez d'installer UV manuellement:"
        Write-Host "1. Ouvrir un nouveau PowerShell"
        Write-Host "2. Exécuter: irm https://astral.sh/uv/install.ps1 | iex"
        Write-Host "3. Redémarrer PowerShell"
        return $false
    }
}

function Setup-PythonEnvironment {
    Write-Step "Configuration de l'environnement Python"
    
    # Vérifier que UV est accessible
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "UV n'est pas accessible. Redémarrez PowerShell et relancez le script."
        return $false
    }
    
    try {
        # Synchroniser les dépendances
        Write-Host "Installation des dépendances Python..."
        $syncResult = uv sync 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Problème avec uv sync: $syncResult"
            Write-Host "Tentative avec pip en fallback..."
            
            # Fallback avec pip si UV échoue
            python -m pip install --upgrade pip
            python -m pip install -r requirements.txt
        }
        
        # Vérifier l'installation
        Write-Host "Test des dépendances critiques..."
        $testResult = uv run python -c "import fastapi, asyncpg, rich; print('OK')" 2>$null
        
        if ($testResult -eq "OK") {
            Write-Success "Environnement Python configuré"
            return $true
        }
        else {
            # Test avec python direct
            $testResult2 = python -c "import fastapi, asyncpg, rich; print('OK')" 2>$null
            if ($testResult2 -eq "OK") {
                Write-Success "Environnement Python configuré (via pip)"
                return $true
            } else {
                throw "Test des dépendances échoué"
            }
        }
    }
    catch {
        Write-Error "Erreur lors de la configuration Python: $_"
        Write-Host "Essayez manuellement:"
        Write-Host "1. pip install fastapi asyncpg rich pydantic-ai docling"
        Write-Host "2. Ou redémarrez PowerShell et relancez le script"
        return $false
    }
}

function Setup-Database {
    Write-Step "Configuration de la base de données PostgreSQL"
    
    if ($SkipPostgreSQL) {
        Write-Warning "Configuration de la base de données ignorée"
        return "postgresql://studyrag:studyrag123@localhost:5432/studyrag"
    }
    
    try {
        # Attendre que PostgreSQL soit prêt
        Write-Host "Attente du démarrage de PostgreSQL..."
        Start-Sleep -Seconds 10
        
        # Créer la base de données et l'utilisateur
        $env:PGPASSWORD = "studyrag123"
        
        # Créer l'utilisateur studyrag
        psql -U postgres -c "CREATE USER studyrag WITH PASSWORD 'studyrag123';" 2>$null
        
        # Créer la base de données
        psql -U postgres -c "CREATE DATABASE studyrag OWNER studyrag;" 2>$null
        
        # Donner les privilèges
        psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE studyrag TO studyrag;" 2>$null
        
        $dbUrl = "postgresql://studyrag:studyrag123@localhost:5432/studyrag"
        
        # Tester la connexion
        $testConnection = psql $dbUrl -c "SELECT 1;" 2>$null
        if ($testConnection) {
            Write-Success "Base de données configurée"
            
            # Créer le schéma si disponible
            if (Test-Path "sql\schema.sql") {
                Write-Host "Création du schéma de base de données..."
                psql $dbUrl -f "sql\schema.sql" 2>$null
                Write-Success "Schéma de base de données créé"
            }
            
            return $dbUrl
        }
        else {
            throw "Test de connexion échoué"
        }
    }
    catch {
        Write-Warning "Problème avec la configuration de la base de données: $_"
        Write-Host "Configuration manuelle requise:"
        Write-Host "1. Ouvrir pgAdmin ou psql"
        Write-Host "2. Créer la base 'studyrag'"
        Write-Host "3. Créer l'utilisateur 'studyrag' avec mot de passe 'studyrag123'"
        
        return "postgresql://studyrag:studyrag123@localhost:5432/studyrag"
    }
}

function Install-Ollama {
    Write-Step "Installation d'Ollama (LLM local)"
    
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        Write-Success "Ollama déjà installé"
    }
    else {
        Write-Host "Téléchargement d'Ollama..."
        try {
            # Télécharger et installer Ollama
            $ollamaUrl = "https://ollama.ai/download/windows"
            Write-Host "Veuillez télécharger et installer Ollama depuis: $ollamaUrl"
            Write-Host "Appuyez sur Entrée après l'installation..."
            Read-Host
            
            # Vérifier l'installation
            if (Get-Command ollama -ErrorAction SilentlyContinue) {
                Write-Success "Ollama installé"
            }
            else {
                Write-Warning "Ollama non détecté, continuez manuellement"
                return $false
            }
        }
        catch {
            Write-Warning "Installation manuelle d'Ollama requise"
            return $false
        }
    }
    
    # Démarrer Ollama
    try {
        Write-Host "Démarrage d'Ollama..."
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 5
        
        # Télécharger un modèle
        $downloadModel = Read-Host "Télécharger le modèle llama3.2 (recommandé) ? [Y/n]"
        if ($downloadModel -eq "" -or $downloadModel -eq "Y" -or $downloadModel -eq "y") {
            Write-Host "Téléchargement du modèle llama3.2 (cela peut prendre du temps)..."
            ollama pull llama3.2
            Write-Success "Modèle llama3.2 téléchargé"
        }
        
        return $true
    }
    catch {
        Write-Warning "Problème avec Ollama: $_"
        return $false
    }
}

function Create-EnvFile {
    param($DatabaseUrl)
    
    Write-Step "Création du fichier de configuration"
    
    $envContent = @"
# Configuration StudyRAG

# Base de données
DATABASE_URL=$DatabaseUrl

# Ollama (LLM local)
OLLAMA_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.2

# Embeddings (local par défaut)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# OpenAI (optionnel)
# OPENAI_API_KEY=sk-your-key-here

# Configuration avancée
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_SEARCH_RESULTS=5
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success "Fichier .env configuré"
}

function Create-SampleDocuments {
    Write-Step "Création de documents d'exemple"
    
    # Créer le dossier test_samples
    if (!(Test-Path "test_samples")) {
        New-Item -ItemType Directory -Path "test_samples" | Out-Null
    }
    
    # Document d'accueil
    $welcomeContent = @"
# Bienvenue dans StudyRAG

StudyRAG est votre assistant d'étude personnel utilisant l'IA locale.

## Fonctionnalités

- Traitement de documents PDF, Word, PowerPoint
- Recherche sémantique dans vos documents
- Réponses avec citations sources
- Modèles IA locaux (confidentialité garantie)

## Premiers pas

1. Placez vos documents dans le dossier ``documents/``
2. Lancez l'ingestion: ``uv run python -m ingestion.ingest --documents documents/``
3. Utilisez le CLI: ``uv run python cli.py``

## Commandes utiles

- Interface CLI interactive: ``uv run python cli.py``
- Interface web: ``uv run python main.py``
- Tests: ``python scripts/verify_implementation.py``

Bon apprentissage !
"@

    $welcomeContent | Out-File -FilePath "test_samples\welcome.md" -Encoding UTF8
    
    # Guide Windows
    $windowsGuideContent = @"
# Guide StudyRAG pour Windows

## Installation terminée ✅

Votre environnement StudyRAG est maintenant configuré sur Windows !

## Prochaines étapes

### 1. Ingérer vos premiers documents
```powershell
# Utiliser les exemples
uv run python -m ingestion.ingest --documents test_samples/

# Ou vos propres documents
uv run python -m ingestion.ingest --documents documents/
```

### 2. Lancer l'interface
```powershell
# CLI interactif (recommandé)
uv run python cli.py

# Interface web
uv run python main.py
```

### 3. Tester le système
```powershell
python scripts/verify_implementation.py
```

## Spécificités Windows

### Services installés
- **Python 3.11** via Chocolatey
- **PostgreSQL 15** avec mot de passe: studyrag123
- **Git** pour le versioning
- **UV** pour la gestion des dépendances
- **Ollama** pour les LLM locaux

### Dépannage Windows

#### PostgreSQL ne démarre pas
```powershell
# Vérifier le service
Get-Service postgresql*

# Démarrer le service
Start-Service postgresql-x64-15
```

#### Ollama non accessible
```powershell
# Redémarrer Ollama
taskkill /f /im ollama.exe
ollama serve
```

#### Problèmes de PATH
Redémarrez PowerShell ou votre terminal après l'installation.

## Support Windows

Pour les problèmes spécifiques à Windows, vérifiez:
1. Les services Windows (PostgreSQL, etc.)
2. Les variables d'environnement PATH
3. Les permissions d'exécution PowerShell
"@

    $windowsGuideContent | Out-File -FilePath "test_samples\guide_windows.md" -Encoding UTF8
    
    Write-Success "Documents d'exemple créés"
}

function Run-Tests {
    Write-Step "Tests de vérification"
    
    $testScripts = @(
        @{Path="scripts\test_ollama_setup.py"; Name="Test Ollama"},
        @{Path="scripts\test_embedding_models.py"; Name="Test Embeddings"},
        @{Path="scripts\post_setup_check.py"; Name="Vérification post-setup"}
    )
    
    foreach ($test in $testScripts) {
        if (Test-Path $test.Path) {
            Write-Host "Exécution: $($test.Name)..."
            try {
                $result = uv run python $test.Path 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "$($test.Name): OK"
                }
                else {
                    Write-Warning "$($test.Name): Problème détecté"
                }
            }
            catch {
                Write-Warning "$($test.Name): Échec"
            }
        }
        else {
            Write-Warning "Script $($test.Path) non trouvé"
        }
    }
}

function Show-NextSteps {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                🎉 Setup terminé avec succès !                ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Prochaines étapes:" -ForegroundColor Blue
    Write-Host "1. uv run python -m ingestion.ingest --documents test_samples/"
    Write-Host "2. uv run python cli.py"
    Write-Host ""
    Write-Host "Commandes utiles:" -ForegroundColor Blue
    Write-Host "• Interface CLI: uv run python cli.py"
    Write-Host "• Interface web: uv run python main.py"
    Write-Host "• Tests: python scripts/verify_implementation.py"
    Write-Host ""
    Write-Host "Documentation: Consultez le dossier docs/" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Informations importantes:" -ForegroundColor Yellow
    Write-Host "• Mot de passe PostgreSQL: studyrag123"
    Write-Host "• Ollama fonctionne en arrière-plan"
    Write-Host "• Tous les modèles sont locaux (pas de clé API requise)"
}

function Main {
    if ($Help) {
        Write-Host "StudyRAG Setup Script pour Windows"
        Write-Host ""
        Write-Host "Usage: .\setup.ps1 [options]"
        Write-Host ""
        Write-Host "Options:"
        Write-Host "  -Help              Affiche cette aide"
        Write-Host "  -SkipPython        Ignore l'installation de Python"
        Write-Host "  -SkipPostgreSQL    Ignore l'installation de PostgreSQL"
        Write-Host ""
        Write-Host "Ce script installe automatiquement:"
        Write-Host "• Chocolatey (gestionnaire de paquets Windows)"
        Write-Host "• Python 3.11"
        Write-Host "• Git"
        Write-Host "• PostgreSQL 15"
        Write-Host "• UV (gestionnaire de dépendances Python)"
        Write-Host "• Ollama (LLM local)"
        Write-Host "• Configure l'environnement StudyRAG"
        Write-Host ""
        Write-Host "Prérequis:"
        Write-Host "• Windows 10/11"
        Write-Host "• PowerShell 5.1+ (exécuter en tant qu'administrateur)"
        Write-Host "• Connexion Internet"
        return
    }
    
    # Vérifier les privilèges administrateur
    if (!(Test-Administrator)) {
        Write-Error "Ce script doit être exécuté en tant qu'administrateur"
        Write-Host "Clic droit sur PowerShell -> 'Exécuter en tant qu'administrateur'"
        exit 1
    }
    
    Write-Header
    
    $errors = @()
    
    # Étapes d'installation
    if (!(Install-Chocolatey)) { $errors += "Chocolatey" }
    if (!(Install-Python)) { $errors += "Python" }
    if (!(Install-Git)) { $errors += "Git" }
    if (!(Install-PostgreSQL)) { $errors += "PostgreSQL" }
    if (!(Install-UV)) { $errors += "UV" }
    if (!(Setup-PythonEnvironment)) { $errors += "Environnement Python" }
    
    $dbUrl = Setup-Database
    Create-EnvFile -DatabaseUrl $dbUrl
    Create-SampleDocuments
    
    if (!(Install-Ollama)) { $errors += "Ollama" }
    
    Run-Tests
    
    if ($errors.Count -eq 0) {
        Show-NextSteps
    }
    else {
        Write-Host ""
        Write-Host "⚠️ Problèmes détectés avec:" -ForegroundColor Yellow
        foreach ($error in $errors) {
            Write-Host "  • $error" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "Consultez SETUP.md pour le dépannage" -ForegroundColor Yellow
    }
}

# Exécution du script principal
Main