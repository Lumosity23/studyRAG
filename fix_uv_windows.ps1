# Script de diagnostic et correction UV pour Windows
# À utiliser si UV n'est pas reconnu après l'installation

param(
    [switch]$Help
)

function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║                    UV Diagnostic & Fix Tool                  ║" -ForegroundColor Blue
    Write-Host "║                  Résolution problèmes UV Windows             ║" -ForegroundColor Blue
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

function Test-UVInstallation {
    Write-Step "Diagnostic de l'installation UV"
    
    # Test 1: UV dans le PATH
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Success "UV trouvé dans le PATH: $(uv --version)"
        return $true
    }
    
    Write-Warning "UV non trouvé dans le PATH"
    
    # Test 2: Chercher UV dans les emplacements standards
    $uvPaths = @(
        "$env:USERPROFILE\.cargo\bin\uv.exe",
        "$env:LOCALAPPDATA\Programs\uv\bin\uv.exe",
        "$env:APPDATA\uv\bin\uv.exe",
        "$env:ProgramFiles\uv\bin\uv.exe"
    )
    
    Write-Host "Recherche de UV dans les emplacements standards..."
    
    foreach ($path in $uvPaths) {
        if (Test-Path $path) {
            Write-Success "UV trouvé: $path"
            
            # Tester la version
            $version = & $path --version 2>$null
            if ($version) {
                Write-Success "Version: $version"
                return $path
            }
        }
    }
    
    Write-Error "UV non trouvé dans les emplacements standards"
    return $false
}

function Fix-UVPath {
    param($UVPath)
    
    Write-Step "Correction du PATH pour UV"
    
    if ($UVPath -eq $true) {
        Write-Success "UV déjà dans le PATH, aucune correction nécessaire"
        return $true
    }
    
    if (-not $UVPath) {
        Write-Error "UV non trouvé, impossible de corriger le PATH"
        return $false
    }
    
    # Extraire le dossier du chemin complet
    $uvDir = Split-Path $UVPath -Parent
    
    try {
        # Ajouter au PATH de la session actuelle
        $env:Path = "$uvDir;$env:Path"
        Write-Success "UV ajouté au PATH de la session actuelle"
        
        # Ajouter au PATH permanent de l'utilisateur
        $currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentUserPath -notlike "*$uvDir*") {
            $newUserPath = "$currentUserPath;$uvDir"
            [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
            Write-Success "UV ajouté au PATH permanent de l'utilisateur"
        }
        
        # Vérifier que UV fonctionne maintenant
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Success "UV maintenant accessible: $(uv --version)"
            return $true
        } else {
            Write-Warning "UV ajouté au PATH mais pas encore accessible"
            Write-Host "Redémarrez PowerShell pour que les changements prennent effet"
            return $false
        }
    }
    catch {
        Write-Error "Erreur lors de la modification du PATH: $_"
        return $false
    }
}

function Install-UVManually {
    Write-Step "Installation manuelle de UV"
    
    try {
        Write-Host "Téléchargement du script d'installation UV..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        
        Write-Success "Installation UV terminée"
        
        # Attendre un peu pour que l'installation se termine
        Start-Sleep -Seconds 3
        
        # Tester l'installation
        $uvPath = Test-UVInstallation
        if ($uvPath) {
            return Fix-UVPath $uvPath
        } else {
            Write-Error "Installation réussie mais UV non trouvé"
            return $false
        }
    }
    catch {
        Write-Error "Échec de l'installation manuelle: $_"
        return $false
    }
}

function Show-ManualInstructions {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║                    Instructions Manuelles                    ║" -ForegroundColor Yellow
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Si le script automatique échoue, suivez ces étapes:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Ouvrir un nouveau PowerShell en tant qu'administrateur"
    Write-Host "2. Exécuter: irm https://astral.sh/uv/install.ps1 | iex"
    Write-Host "3. Redémarrer PowerShell"
    Write-Host "4. Tester: uv --version"
    Write-Host ""
    Write-Host "Si UV n'est toujours pas reconnu:"
    Write-Host "5. Ouvrir 'Variables d'environnement système'"
    Write-Host "6. Modifier la variable PATH utilisateur"
    Write-Host "7. Ajouter: C:\Users\$env:USERNAME\.cargo\bin"
    Write-Host "8. Redémarrer PowerShell"
    Write-Host ""
    Write-Host "Alternative - Installation via pip:"
    Write-Host "pip install uv"
    Write-Host ""
}

function Main {
    if ($Help) {
        Write-Host "UV Diagnostic & Fix Tool pour Windows"
        Write-Host ""
        Write-Host "Usage: .\fix_uv_windows.ps1"
        Write-Host ""
        Write-Host "Ce script:"
        Write-Host "• Diagnostique les problèmes d'installation UV"
        Write-Host "• Corrige automatiquement le PATH"
        Write-Host "• Réinstalle UV si nécessaire"
        Write-Host "• Fournit des instructions manuelles"
        return
    }
    
    Write-Header
    
    # Diagnostic
    $uvPath = Test-UVInstallation
    
    if ($uvPath -eq $true) {
        Write-Success "UV fonctionne correctement !"
        Write-Host "Vous pouvez maintenant utiliser StudyRAG"
        return
    }
    
    # Tentative de correction du PATH
    if ($uvPath) {
        $fixed = Fix-UVPath $uvPath
        if ($fixed) {
            Write-Success "Problème résolu ! UV est maintenant accessible"
            return
        }
    }
    
    # Installation manuelle
    Write-Host ""
    $install = Read-Host "UV non trouvé. Voulez-vous tenter une réinstallation ? [Y/n]"
    if ($install -eq "" -or $install -eq "Y" -or $install -eq "y") {
        $installed = Install-UVManually
        if ($installed) {
            Write-Success "UV installé et configuré avec succès !"
            return
        }
    }
    
    # Instructions manuelles
    Show-ManualInstructions
}

# Exécution du script principal
Main