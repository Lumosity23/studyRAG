#!/usr/bin/env python3
"""
Script de démarrage StudyRAG
Démarre automatiquement le backend et le frontend pour les tests
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests
import json

console = Console()

class StudyRAGStarter:
    def __init__(self):
        self.processes = []
        self.backend_port = 8000
        self.frontend_port = 3000
        self.ollama_port = 11434
        self.project_root = Path(__file__).parent
        
    def check_dependencies(self):
        """Vérifie que les dépendances sont installées"""
        console.print("[blue]🔍 Vérification des dépendances...[/blue]")
        
        # Vérifier UV
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            console.print("✅ UV installé")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ UV non trouvé. Installez UV: https://docs.astral.sh/uv/[/red]")
            return False
        
        # Vérifier Node.js pour le frontend
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
            console.print("✅ Node.js et npm installés")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ Node.js/npm non trouvé. Installez Node.js: https://nodejs.org/[/red]")
            return False
        
        return True
    
    def check_ollama(self):
        """Vérifie si Ollama est disponible"""
        try:
            response = requests.get(f"http://localhost:{self.ollama_port}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                console.print(f"✅ Ollama disponible avec {len(models)} modèles")
                return True
        except:
            pass
        
        console.print("[yellow]⚠️ Ollama non disponible. Démarrez Ollama avec: ollama serve[/yellow]")
        return False
    
    def setup_environment(self):
        """Configure l'environnement"""
        console.print("[blue]⚙️ Configuration de l'environnement...[/blue]")
        
        # Créer .env si nécessaire
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_file.exists() and env_example.exists():
            console.print("📝 Création du fichier .env depuis .env.example")
            with open(env_example, 'r') as f:
                content = f.read()
            
            # Ajuster les valeurs par défaut pour le développement
            content = content.replace(
                "DATABASE_URL=postgresql://studyrag:studyrag@localhost:5432/studyrag",
                "DATABASE_URL=sqlite:///./study_rag.db"  # SQLite pour simplifier les tests
            )
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            console.print("✅ Fichier .env créé")
        
        # Synchroniser les dépendances Python
        console.print("📦 Installation des dépendances Python...")
        try:
            subprocess.run(["uv", "sync"], cwd=self.project_root, check=True)
            console.print("✅ Dépendances Python installées")
        except subprocess.CalledProcessError:
            console.print("[red]❌ Erreur lors de l'installation des dépendances Python[/red]")
            return False
        
        # Installer les dépendances frontend
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            console.print("📦 Installation des dépendances frontend...")
            try:
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
                console.print("✅ Dépendances frontend installées")
            except subprocess.CalledProcessError:
                console.print("[red]❌ Erreur lors de l'installation des dépendances frontend[/red]")
                return False
        
        return True
    
    def start_backend(self):
        """Démarre le backend FastAPI"""
        console.print("[green]🚀 Démarrage du backend...[/green]")
        
        # Utiliser uvicorn directement pour plus de contrôle
        cmd = [
            "uv", "run", "uvicorn", 
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.backend_port),
            "--reload",
            "--log-level", "info"
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(("Backend", process))
        
        # Attendre que le backend soit prêt
        self.wait_for_service("Backend", f"http://localhost:{self.backend_port}/health", 30)
        
        return process
    
    def start_frontend(self):
        """Démarre le frontend Next.js"""
        frontend_dir = self.project_root / "frontend"
        if not frontend_dir.exists():
            console.print("[yellow]⚠️ Dossier frontend non trouvé, backend seulement[/yellow]")
            return None
        
        console.print("[green]🚀 Démarrage du frontend...[/green]")
        
        cmd = ["npm", "run", "dev"]
        
        process = subprocess.Popen(
            cmd,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(("Frontend", process))
        
        # Attendre que le frontend soit prêt
        self.wait_for_service("Frontend", f"http://localhost:{self.frontend_port}", 30)
        
        return process
    
    def wait_for_service(self, name, url, timeout=30):
        """Attend qu'un service soit disponible"""
        console.print(f"⏳ Attente du démarrage de {name}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code < 500:  # Service répond
                    console.print(f"✅ {name} démarré sur {url}")
                    return True
            except:
                pass
            time.sleep(1)
        
        console.print(f"[yellow]⚠️ {name} met du temps à démarrer...[/yellow]")
        return False
    
    def show_status(self):
        """Affiche le statut des services"""
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            f"[bold green]StudyRAG démarré avec succès![/bold green]\n\n"
            f"🌐 Frontend: http://localhost:{self.frontend_port}\n"
            f"🔧 Backend API: http://localhost:{self.backend_port}\n"
            f"📚 Documentation: http://localhost:{self.backend_port}/docs\n"
            f"❤️ Health Check: http://localhost:{self.backend_port}/health\n\n"
            f"[yellow]Appuyez sur Ctrl+C pour arrêter tous les services[/yellow]",
            title="🎓 StudyRAG - Prêt pour les tests!",
            border_style="green"
        ))
        console.print("="*60 + "\n")
    
    def monitor_processes(self):
        """Surveille les processus en arrière-plan"""
        def log_output(name, process):
            """Log la sortie d'un processus"""
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    # Filtrer les logs trop verbeux
                    if any(skip in line.lower() for skip in ['info:', 'debug:', 'started server']):
                        continue
                    console.print(f"[dim]{name}:[/dim] {line.strip()}")
        
        # Créer des threads pour surveiller chaque processus
        for name, process in self.processes:
            thread = threading.Thread(target=log_output, args=(name, process), daemon=True)
            thread.start()
    
    def cleanup(self):
        """Nettoie les processus"""
        console.print("\n[yellow]🛑 Arrêt des services...[/yellow]")
        
        for name, process in self.processes:
            if process.poll() is None:  # Processus encore en vie
                console.print(f"Arrêt de {name}...")
                process.terminate()
                
                # Attendre un peu puis forcer l'arrêt si nécessaire
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        
        console.print("[green]✅ Tous les services arrêtés[/green]")
    
    def run(self):
        """Lance l'application complète"""
        try:
            # Vérifications préliminaires
            if not self.check_dependencies():
                return 1
            
            self.check_ollama()
            
            if not self.setup_environment():
                return 1
            
            # Démarrage des services
            backend_process = self.start_backend()
            frontend_process = self.start_frontend()
            
            # Surveillance des processus
            self.monitor_processes()
            
            # Affichage du statut
            self.show_status()
            
            # Attendre l'interruption
            try:
                while True:
                    # Vérifier que les processus sont toujours en vie
                    for name, process in self.processes:
                        if process.poll() is not None:
                            console.print(f"[red]❌ {name} s'est arrêté inopinément[/red]")
                            return 1
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Interruption détectée...[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e}[/red]")
            return 1
        finally:
            self.cleanup()
        
        return 0


def main():
    """Point d'entrée principal"""
    console.print(Panel.fit(
        "[bold blue]StudyRAG - Script de Démarrage[/bold blue]\n"
        "Démarre automatiquement le backend et frontend pour les tests",
        title="🎓 StudyRAG Starter",
        border_style="blue"
    ))
    
    starter = StudyRAGStarter()
    
    # Gérer les signaux pour un arrêt propre
    def signal_handler(signum, frame):
        starter.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    return starter.run()


if __name__ == "__main__":
    sys.exit(main())