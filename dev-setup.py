#!/usr/bin/env python3
"""
Script de setup développement StudyRAG
Configure l'environnement de développement complet
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
import requests

console = Console()

class DevSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.frontend_dir = self.project_root / "frontend"
        
    def check_system_requirements(self):
        """Vérifie les prérequis système"""
        console.print("[blue]🔍 Vérification des prérequis système...[/blue]")
        
        requirements = {
            "python": {"cmd": ["python", "--version"], "min_version": "3.9"},
            "uv": {"cmd": ["uv", "--version"], "install_url": "https://docs.astral.sh/uv/"},
            "node": {"cmd": ["node", "--version"], "min_version": "18.0"},
            "npm": {"cmd": ["npm", "--version"], "install_url": "https://nodejs.org/"},
            "git": {"cmd": ["git", "--version"], "install_url": "https://git-scm.com/"}
        }
        
        missing = []
        
        for name, req in requirements.items():
            try:
                result = subprocess.run(req["cmd"], capture_output=True, text=True, check=True)
                version = result.stdout.strip()
                console.print(f"✅ {name}: {version}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print(f"❌ {name}: Non trouvé")
                if "install_url" in req:
                    console.print(f"   📥 Installation: {req['install_url']}")
                missing.append(name)
        
        if missing:
            console.print(f"\n[red]❌ Prérequis manquants: {', '.join(missing)}[/red]")
            return False
        
        console.print("[green]✅ Tous les prérequis sont satisfaits[/green]")
        return True
    
    def setup_ollama(self):
        """Configure Ollama et installe les modèles"""
        console.print("\n[blue]🤖 Configuration d'Ollama...[/blue]")
        
        # Vérifier si Ollama est installé
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            console.print("✅ Ollama installé")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[yellow]⚠️ Ollama non trouvé[/yellow]")
            if Confirm.ask("Voulez-vous installer Ollama automatiquement?"):
                try:
                    # Installation sur Linux/macOS
                    subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh"], 
                                 stdout=subprocess.PIPE, check=True)
                    subprocess.run(["sh"], input=subprocess.PIPE, check=True)
                    console.print("✅ Ollama installé")
                except subprocess.CalledProcessError:
                    console.print("[red]❌ Erreur lors de l'installation d'Ollama[/red]")
                    console.print("Installez manuellement: https://ollama.ai/")
                    return False
            else:
                console.print("Installez Ollama manuellement: https://ollama.ai/")
                return False
        
        # Vérifier si Ollama est en cours d'exécution
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            models = response.json().get('models', [])
            console.print(f"✅ Ollama en cours d'exécution avec {len(models)} modèles")
            
            # Proposer d'installer des modèles recommandés
            recommended_models = ["llama3.2", "mistral", "qwen2.5:7b"]
            installed_models = [m['name'].split(':')[0] for m in models]
            
            for model in recommended_models:
                if model not in installed_models:
                    if Confirm.ask(f"Installer le modèle {model}? (Recommandé)"):
                        console.print(f"📥 Installation de {model}...")
                        try:
                            subprocess.run(["ollama", "pull", model], check=True)
                            console.print(f"✅ {model} installé")
                        except subprocess.CalledProcessError:
                            console.print(f"[red]❌ Erreur lors de l'installation de {model}[/red]")
            
        except requests.RequestException:
            console.print("[yellow]⚠️ Ollama n'est pas en cours d'exécution[/yellow]")
            console.print("Démarrez Ollama avec: ollama serve")
            
            if Confirm.ask("Démarrer Ollama maintenant?"):
                try:
                    # Démarrer Ollama en arrière-plan
                    subprocess.Popen(["ollama", "serve"], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    console.print("✅ Ollama démarré")
                    
                    # Attendre un peu puis réessayer
                    import time
                    time.sleep(3)
                    return self.setup_ollama()  # Récursion pour réessayer
                except subprocess.CalledProcessError:
                    console.print("[red]❌ Impossible de démarrer Ollama[/red]")
                    return False
        
        return True
    
    def setup_environment(self):
        """Configure les fichiers d'environnement"""
        console.print("\n[blue]⚙️ Configuration de l'environnement...[/blue]")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if env_file.exists():
            console.print("✅ Fichier .env existe déjà")
            if not Confirm.ask("Voulez-vous le reconfigurer?"):
                return True
        
        if not env_example.exists():
            console.print("[red]❌ Fichier .env.example non trouvé[/red]")
            return False
        
        # Lire le template
        with open(env_example, 'r') as f:
            env_content = f.read()
        
        # Configuration interactive
        console.print("\n[yellow]Configuration interactive:[/yellow]")
        
        # Base de données
        db_choice = Prompt.ask(
            "Type de base de données",
            choices=["sqlite", "postgresql", "chromadb"],
            default="sqlite"
        )
        
        if db_choice == "sqlite":
            env_content = env_content.replace(
                "DATABASE_URL=postgresql://studyrag:studyrag@localhost:5432/studyrag",
                "DATABASE_URL=sqlite:///./study_rag.db"
            )
        elif db_choice == "postgresql":
            db_url = Prompt.ask(
                "URL PostgreSQL",
                default="postgresql://studyrag:studyrag@localhost:5432/studyrag"
            )
            env_content = env_content.replace(
                "DATABASE_URL=postgresql://studyrag:studyrag@localhost:5432/studyrag",
                f"DATABASE_URL={db_url}"
            )
        
        # Modèle LLM
        llm_model = Prompt.ask(
            "Modèle LLM Ollama",
            default="llama3.2"
        )
        env_content = env_content.replace("LLM_CHOICE=llama3.2", f"LLM_CHOICE={llm_model}")
        
        # Modèle d'embeddings
        embedding_model = Prompt.ask(
            "Modèle d'embeddings",
            default="sentence-transformers/all-MiniLM-L6-v2"
        )
        env_content = env_content.replace(
            "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
            f"EMBEDDING_MODEL={embedding_model}"
        )
        
        # OpenAI API Key (optionnel)
        if Confirm.ask("Avez-vous une clé API OpenAI? (optionnel pour fallback)"):
            openai_key = Prompt.ask("Clé API OpenAI", password=True)
            env_content = env_content.replace(
                "OPENAI_API_KEY=sk-your-openai-key-here",
                f"OPENAI_API_KEY={openai_key}"
            )
        
        # Sauvegarder
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        console.print("✅ Fichier .env configuré")
        return True
    
    def install_dependencies(self):
        """Installe toutes les dépendances"""
        console.print("\n[blue]📦 Installation des dépendances...[/blue]")
        
        # Dépendances Python
        console.print("Installation des dépendances Python...")
        try:
            subprocess.run(["uv", "sync"], cwd=self.project_root, check=True)
            console.print("✅ Dépendances Python installées")
        except subprocess.CalledProcessError:
            console.print("[red]❌ Erreur lors de l'installation des dépendances Python[/red]")
            return False
        
        # Dépendances frontend
        if self.frontend_dir.exists():
            console.print("Installation des dépendances frontend...")
            try:
                subprocess.run(["npm", "install"], cwd=self.frontend_dir, check=True)
                console.print("✅ Dépendances frontend installées")
            except subprocess.CalledProcessError:
                console.print("[red]❌ Erreur lors de l'installation des dépendances frontend[/red]")
                return False
        else:
            console.print("[yellow]⚠️ Dossier frontend non trouvé[/yellow]")
        
        return True
    
    def setup_database(self):
        """Configure la base de données"""
        console.print("\n[blue]🗄️ Configuration de la base de données...[/blue]")
        
        # Lire la configuration
        env_file = self.project_root / ".env"
        if not env_file.exists():
            console.print("[red]❌ Fichier .env non trouvé[/red]")
            return False
        
        # Pour SQLite, créer le fichier si nécessaire
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        if "sqlite:" in env_content:
            console.print("✅ Base SQLite configurée (aucune action requise)")
            return True
        
        # Pour PostgreSQL, proposer de créer le schéma
        if "postgresql:" in env_content and Confirm.ask("Créer le schéma PostgreSQL?"):
            schema_file = self.project_root / "sql" / "schema.sql"
            if schema_file.exists():
                try:
                    # Extraire l'URL de la base
                    import re
                    db_url_match = re.search(r'DATABASE_URL=(.+)', env_content)
                    if db_url_match:
                        db_url = db_url_match.group(1)
                        subprocess.run(["psql", db_url, "-f", str(schema_file)], check=True)
                        console.print("✅ Schéma PostgreSQL créé")
                except subprocess.CalledProcessError:
                    console.print("[yellow]⚠️ Impossible de créer le schéma automatiquement[/yellow]")
                    console.print(f"Exécutez manuellement: psql $DATABASE_URL < {schema_file}")
        
        return True
    
    def create_sample_documents(self):
        """Crée des documents d'exemple"""
        console.print("\n[blue]📚 Configuration des documents d'exemple...[/blue]")
        
        docs_dir = self.project_root / "documents"
        docs_dir.mkdir(exist_ok=True)
        
        test_samples_dir = self.project_root / "test_samples"
        
        if test_samples_dir.exists() and any(test_samples_dir.iterdir()):
            console.print("✅ Documents d'exemple trouvés dans test_samples/")
            
            if Confirm.ask("Copier les échantillons vers documents/ pour les tests?"):
                import shutil
                for file in test_samples_dir.iterdir():
                    if file.is_file():
                        shutil.copy2(file, docs_dir)
                console.print("✅ Documents d'exemple copiés")
        else:
            # Créer un document d'exemple simple
            sample_doc = docs_dir / "welcome.md"
            if not sample_doc.exists():
                sample_content = """# Bienvenue dans StudyRAG

StudyRAG est votre assistant IA local pour l'apprentissage et la recherche documentaire.

## Fonctionnalités

- Traitement de documents multi-format avec Docling
- Recherche sémantique dans vos documents
- Conversations avec un agent IA local (Ollama)
- Interface web moderne et CLI interactif

## Comment utiliser

1. Ajoutez vos documents dans le dossier `documents/`
2. Lancez l'ingestion avec `uv run python -m ingestion.ingest --documents documents/`
3. Démarrez l'application avec `python start.py`
4. Posez vos questions!

Bon apprentissage! 🎓
"""
                with open(sample_doc, 'w', encoding='utf-8') as f:
                    f.write(sample_content)
                console.print("✅ Document d'exemple créé: welcome.md")
        
        return True
    
    def run_initial_ingestion(self):
        """Lance une ingestion initiale"""
        console.print("\n[blue]🔄 Ingestion initiale des documents...[/blue]")
        
        docs_dir = self.project_root / "documents"
        if not any(docs_dir.iterdir()):
            console.print("[yellow]⚠️ Aucun document à ingérer[/yellow]")
            return True
        
        if Confirm.ask("Lancer l'ingestion des documents maintenant?"):
            try:
                subprocess.run([
                    "uv", "run", "python", "-m", "ingestion.ingest",
                    "--documents", str(docs_dir)
                ], cwd=self.project_root, check=True)
                console.print("✅ Ingestion terminée")
            except subprocess.CalledProcessError:
                console.print("[red]❌ Erreur lors de l'ingestion[/red]")
                console.print("Vous pourrez la relancer plus tard avec:")
                console.print(f"uv run python -m ingestion.ingest --documents {docs_dir}")
                return False
        
        return True
    
    def show_next_steps(self):
        """Affiche les prochaines étapes"""
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            "[bold green]🎉 Configuration terminée![/bold green]\n\n"
            "[bold]Prochaines étapes:[/bold]\n\n"
            "1. 🚀 Démarrer l'application:\n"
            "   [cyan]python start.py[/cyan]\n\n"
            "2. 📚 Ajouter vos documents:\n"
            "   - Copiez vos fichiers dans [cyan]documents/[/cyan]\n"
            "   - Lancez: [cyan]uv run python -m ingestion.ingest --documents documents/[/cyan]\n\n"
            "3. 💬 Utiliser l'interface:\n"
            "   - Web: [cyan]http://localhost:3000[/cyan]\n"
            "   - CLI: [cyan]uv run python cli.py[/cyan]\n"
            "   - API: [cyan]http://localhost:8000/docs[/cyan]\n\n"
            "[bold]Commandes utiles:[/bold]\n"
            "- [cyan]python start.py[/cyan] - Démarrage complet\n"
            "- [cyan]./start.sh[/cyan] - Alternative bash\n"
            "- [cyan]uv run python cli.py[/cyan] - CLI seulement\n"
            "- [cyan]docker-compose up -d[/cyan] - Avec Docker",
            title="🎓 StudyRAG - Prêt à utiliser!",
            border_style="green"
        ))
        console.print("="*60)
    
    def run(self):
        """Lance le setup complet"""
        console.print(Panel.fit(
            "[bold blue]StudyRAG - Configuration Développement[/bold blue]\n"
            "Ce script va configurer votre environnement de développement complet",
            title="🛠️ Dev Setup",
            border_style="blue"
        ))
        
        steps = [
            ("Prérequis système", self.check_system_requirements),
            ("Configuration Ollama", self.setup_ollama),
            ("Environnement", self.setup_environment),
            ("Dépendances", self.install_dependencies),
            ("Base de données", self.setup_database),
            ("Documents d'exemple", self.create_sample_documents),
            ("Ingestion initiale", self.run_initial_ingestion),
        ]
        
        for step_name, step_func in steps:
            console.print(f"\n[bold]📋 {step_name}[/bold]")
            if not step_func():
                console.print(f"[red]❌ Échec de l'étape: {step_name}[/red]")
                return 1
        
        self.show_next_steps()
        return 0


def main():
    setup = DevSetup()
    return setup.run()


if __name__ == "__main__":
    sys.exit(main())