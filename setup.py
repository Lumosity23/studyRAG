#!/usr/bin/env python3
"""
StudyRAG - Script de Setup Complet
Installe et configure tout l'environnement de développement en une commande.
"""

import os
import sys
import subprocess
import shutil
import asyncio
import asyncpg
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import platform

console = Console()

class StudyRAGSetup:
    def __init__(self):
        self.project_root = Path.cwd()
        self.system = platform.system().lower()
        self.errors = []
        
    def print_header(self):
        """Affiche l'en-tête du setup"""
        console.print(Panel.fit(
            "[bold blue]StudyRAG - Setup Automatique[/bold blue]\n"
            "Configuration complète de l'environnement de développement",
            border_style="blue"
        ))
        
    def check_system_requirements(self):
        """Vérifie les prérequis système"""
        console.print("\n[yellow]🔍 Vérification des prérequis système...[/yellow]")
        
        requirements = {
            "python": {"cmd": ["python3", "--version"], "min_version": "3.9"},
            "git": {"cmd": ["git", "--version"], "required": True},
            "curl": {"cmd": ["curl", "--version"], "required": True}
        }
        
        for tool, config in requirements.items():
            try:
                result = subprocess.run(config["cmd"], capture_output=True, text=True)
                if result.returncode == 0:
                    console.print(f"[green]✅ {tool}: {result.stdout.split()[1]}[/green]")
                else:
                    raise subprocess.CalledProcessError(result.returncode, config["cmd"])
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print(f"[red]❌ {tool}: Non trouvé[/red]")
                self.errors.append(f"{tool} n'est pas installé")
                
    def install_uv(self):
        """Installe UV si nécessaire"""
        console.print("\n[yellow]📦 Installation de UV (gestionnaire de dépendances)...[/yellow]")
        
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            console.print("[green]✅ UV déjà installé[/green]")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[blue]Installation de UV...[/blue]")
            
        try:
            if self.system == "windows":
                cmd = ["powershell", "-c", "irm https://astral.sh/uv/install.ps1 | iex"]
            else:
                cmd = ["curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"]
                
            subprocess.run(cmd, shell=True, check=True)
            console.print("[green]✅ UV installé avec succès[/green]")
            return True
        except subprocess.CalledProcessError:
            console.print("[red]❌ Échec de l'installation de UV[/red]")
            self.errors.append("Impossible d'installer UV")
            return False
            
    def setup_python_environment(self):
        """Configure l'environnement Python avec UV"""
        console.print("\n[yellow]🐍 Configuration de l'environnement Python...[/yellow]")
        
        try:
            # Synchroniser les dépendances
            console.print("[blue]Installation des dépendances...[/blue]")
            subprocess.run(["uv", "sync"], check=True, cwd=self.project_root)
            console.print("[green]✅ Dépendances installées[/green]")
            
            # Vérifier l'installation
            result = subprocess.run(
                ["uv", "run", "python", "-c", "import fastapi, asyncpg, rich; print('OK')"],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.returncode == 0:
                console.print("[green]✅ Environnement Python configuré[/green]")
                return True
            else:
                raise subprocess.CalledProcessError(result.returncode, "uv run python")
                
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Erreur lors de la configuration Python: {e}[/red]")
            self.errors.append("Configuration Python échouée")
            return False
            
    def setup_database(self):
        """Configure PostgreSQL et PGVector"""
        console.print("\n[yellow]🗄️ Configuration de la base de données...[/yellow]")
        
        # Vérifier si PostgreSQL est installé
        try:
            subprocess.run(["psql", "--version"], capture_output=True, check=True)
            console.print("[green]✅ PostgreSQL détecté[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ PostgreSQL non trouvé[/red]")
            console.print("[yellow]Instructions d'installation PostgreSQL:[/yellow]")
            
            if self.system == "darwin":  # macOS
                console.print("brew install postgresql@15")
            elif self.system == "linux":
                console.print("sudo apt-get install postgresql postgresql-contrib")
            else:  # Windows
                console.print("Télécharger depuis: https://www.postgresql.org/download/windows/")
                
            self.errors.append("PostgreSQL doit être installé manuellement")
            return False
            
        # Demander les informations de connexion
        console.print("\n[blue]Configuration de la base de données:[/blue]")
        
        default_db_url = "postgresql://studyrag:password@localhost:5432/studyrag"
        db_url = Prompt.ask(
            "URL de la base de données", 
            default=default_db_url
        )
        
        # Tester la connexion
        try:
            async def test_connection():
                conn = await asyncpg.connect(db_url)
                await conn.close()
                return True
                
            asyncio.run(test_connection())
            console.print("[green]✅ Connexion à la base de données réussie[/green]")
            
            # Créer le schéma
            self.create_database_schema(db_url)
            
            return db_url
            
        except Exception as e:
            console.print(f"[red]❌ Impossible de se connecter à la base: {e}[/red]")
            console.print("[yellow]Créez d'abord la base de données:[/yellow]")
            console.print(f"createdb studyrag")
            self.errors.append("Base de données non accessible")
            return None
            
    def create_database_schema(self, db_url):
        """Crée le schéma de la base de données"""
        console.print("[blue]Création du schéma de base de données...[/blue]")
        
        schema_file = self.project_root / "sql" / "schema.sql"
        if schema_file.exists():
            try:
                subprocess.run(
                    ["psql", db_url, "-f", str(schema_file)],
                    check=True, capture_output=True
                )
                console.print("[green]✅ Schéma de base de données créé[/green]")
            except subprocess.CalledProcessError:
                console.print("[yellow]⚠️ Erreur lors de la création du schéma[/yellow]")
        else:
            console.print("[yellow]⚠️ Fichier schema.sql non trouvé[/yellow]")
            
    def setup_ollama(self):
        """Configure Ollama pour les LLM locaux"""
        console.print("\n[yellow]🤖 Configuration d'Ollama...[/yellow]")
        
        # Vérifier si Ollama est installé
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            console.print("[green]✅ Ollama déjà installé[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[blue]Installation d'Ollama...[/blue]")
            
            try:
                if self.system == "windows":
                    console.print("[yellow]Téléchargez Ollama depuis: https://ollama.ai/download[/yellow]")
                    return False
                else:
                    subprocess.run(
                        ["curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"],
                        shell=True, check=True
                    )
                    console.print("[green]✅ Ollama installé[/green]")
            except subprocess.CalledProcessError:
                console.print("[red]❌ Échec de l'installation d'Ollama[/red]")
                return False
                
        # Démarrer Ollama en arrière-plan
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print("[blue]Démarrage du serveur Ollama...[/blue]")
            
            # Attendre que le serveur soit prêt
            import time
            time.sleep(3)
            
            # Télécharger un modèle recommandé
            if Confirm.ask("Télécharger le modèle llama3.2 (recommandé) ?", default=True):
                console.print("[blue]Téléchargement du modèle llama3.2...[/blue]")
                subprocess.run(["ollama", "pull", "llama3.2"], check=True)
                console.print("[green]✅ Modèle llama3.2 téléchargé[/green]")
                
            return True
            
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠️ Problème avec Ollama, continuez manuellement[/yellow]")
            return False
            
    def create_env_file(self, db_url=None):
        """Crée le fichier .env avec la configuration"""
        console.print("\n[yellow]⚙️ Création du fichier de configuration...[/yellow]")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        # Copier depuis .env.example si disponible
        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            console.print("[blue]Fichier .env créé depuis .env.example[/blue]")
            
        # Mettre à jour avec les valeurs configurées
        env_content = []
        
        if db_url:
            env_content.append(f"DATABASE_URL={db_url}")
        else:
            env_content.append("DATABASE_URL=postgresql://studyrag:password@localhost:5432/studyrag")
            
        env_content.extend([
            "OLLAMA_BASE_URL=http://localhost:11434",
            "LLM_CHOICE=llama3.2",
            "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
            "# OPENAI_API_KEY=sk-your-key-here  # Optionnel",
            "",
            "# Configuration avancée",
            "CHUNK_SIZE=1000",
            "CHUNK_OVERLAP=200",
            "MAX_SEARCH_RESULTS=5"
        ])
        
        with open(env_file, "w") as f:
            f.write("\n".join(env_content))
            
        console.print("[green]✅ Fichier .env configuré[/green]")
        
    def run_initial_tests(self):
        """Lance les tests initiaux pour vérifier l'installation"""
        console.print("\n[yellow]🧪 Tests de vérification...[/yellow]")
        
        test_scripts = [
            ("scripts/test_ollama_setup.py", "Test Ollama"),
            ("scripts/test_embedding_models.py", "Test Embeddings"),
            ("scripts/verify_implementation.py", "Vérification complète")
        ]
        
        for script_path, description in test_scripts:
            script_file = self.project_root / script_path
            if script_file.exists():
                try:
                    console.print(f"[blue]Exécution: {description}...[/blue]")
                    result = subprocess.run(
                        ["uv", "run", "python", script_path],
                        capture_output=True, text=True, cwd=self.project_root
                    )
                    
                    if result.returncode == 0:
                        console.print(f"[green]✅ {description}: OK[/green]")
                    else:
                        console.print(f"[yellow]⚠️ {description}: Problème détecté[/yellow]")
                        
                except subprocess.CalledProcessError:
                    console.print(f"[red]❌ {description}: Échec[/red]")
            else:
                console.print(f"[yellow]⚠️ Script {script_path} non trouvé[/yellow]")
                
    def create_sample_documents(self):
        """Crée des documents d'exemple si nécessaire"""
        console.print("\n[yellow]📄 Vérification des documents d'exemple...[/yellow]")
        
        test_samples_dir = self.project_root / "test_samples"
        if not test_samples_dir.exists():
            test_samples_dir.mkdir()
            console.print("[blue]Dossier test_samples créé[/blue]")
            
        # Créer un document d'exemple simple
        sample_md = test_samples_dir / "welcome.md"
        if not sample_md.exists():
            sample_content = """# Bienvenue dans StudyRAG

StudyRAG est votre assistant d'étude personnel utilisant l'IA locale.

## Fonctionnalités

- Traitement de documents PDF, Word, PowerPoint
- Recherche sémantique dans vos documents
- Réponses avec citations sources
- Modèles IA locaux (confidentialité garantie)

## Premiers pas

1. Placez vos documents dans le dossier `documents/`
2. Lancez l'ingestion: `uv run python -m ingestion.ingest --documents documents/`
3. Utilisez le CLI: `uv run python cli.py`

Bon apprentissage !
"""
            with open(sample_md, "w", encoding="utf-8") as f:
                f.write(sample_content)
            console.print("[green]✅ Document d'exemple créé[/green]")
            
    def print_next_steps(self):
        """Affiche les prochaines étapes"""
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            "[bold green]🎉 Setup terminé avec succès ![/bold green]\n\n"
            "[bold]Prochaines étapes:[/bold]\n"
            "1. [blue]uv run python -m ingestion.ingest --documents test_samples/[/blue]\n"
            "2. [blue]uv run python cli.py[/blue]\n\n"
            "[bold]Commandes utiles:[/bold]\n"
            "• Interface CLI: [blue]uv run python cli.py[/blue]\n"
            "• Interface web: [blue]uv run python main.py[/blue]\n"
            "• Tests: [blue]python scripts/verify_implementation.py[/blue]\n\n"
            "[bold]Documentation:[/bold] Consultez le dossier [blue]docs/[/blue]",
            border_style="green"
        ))
        
    def print_errors_summary(self):
        """Affiche un résumé des erreurs"""
        if self.errors:
            console.print("\n[red]⚠️ Problèmes détectés:[/red]")
            for error in self.errors:
                console.print(f"  • {error}")
            console.print("\n[yellow]Consultez la documentation pour résoudre ces problèmes.[/yellow]")
            
    def run(self):
        """Lance le setup complet"""
        self.print_header()
        
        # Étapes du setup
        steps = [
            ("Prérequis système", self.check_system_requirements),
            ("Installation UV", self.install_uv),
            ("Environnement Python", self.setup_python_environment),
            ("Base de données", self.setup_database),
            ("Ollama (LLM local)", self.setup_ollama),
            ("Configuration", lambda: self.create_env_file()),
            ("Documents d'exemple", self.create_sample_documents),
            ("Tests de vérification", self.run_initial_tests)
        ]
        
        db_url = None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for step_name, step_func in steps:
                task = progress.add_task(f"[blue]{step_name}...", total=None)
                
                try:
                    if step_name == "Base de données":
                        db_url = step_func()
                    elif step_name == "Configuration":
                        step_func(db_url)
                    else:
                        step_func()
                        
                    progress.update(task, description=f"[green]✅ {step_name}")
                    
                except Exception as e:
                    progress.update(task, description=f"[red]❌ {step_name}")
                    self.errors.append(f"{step_name}: {str(e)}")
                    
                progress.remove_task(task)
                
        # Résumé final
        if not self.errors:
            self.print_next_steps()
        else:
            self.print_errors_summary()
            
        return len(self.errors) == 0

def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        console.print("""
[bold]StudyRAG Setup Script[/bold]

Usage: python setup.py

Ce script configure automatiquement l'environnement StudyRAG:
• Installe UV et les dépendances Python
• Configure PostgreSQL et PGVector
• Installe et configure Ollama
• Crée les fichiers de configuration
• Lance les tests de vérification

Prérequis:
• Python 3.9+
• Git
• PostgreSQL (sera configuré)
• Connexion Internet
        """)
        return
        
    setup = StudyRAGSetup()
    success = setup.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()