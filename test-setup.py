#!/usr/bin/env python3
"""
Script de test rapide pour StudyRAG
Vérifie que tous les composants fonctionnent correctement
"""

import os
import sys
import asyncio
import subprocess
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests
import json

console = Console()

class StudyRAGTester:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        
    def test_dependencies(self):
        """Test des dépendances système"""
        console.print("[blue]🔍 Test des dépendances...[/blue]")
        
        deps = ["python", "uv", "node", "npm"]
        all_good = True
        
        for dep in deps:
            try:
                result = subprocess.run([dep, "--version"], 
                                      capture_output=True, text=True, check=True)
                console.print(f"✅ {dep}: {result.stdout.strip().split()[0]}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print(f"❌ {dep}: Non trouvé")
                all_good = False
        
        self.test_results["dependencies"] = all_good
        return all_good
    
    def test_ollama(self):
        """Test de la connexion Ollama"""
        console.print("[blue]🤖 Test d'Ollama...[/blue]")
        
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                console.print(f"✅ Ollama: {len(models)} modèles disponibles")
                
                # Lister les modèles
                for model in models[:3]:  # Afficher les 3 premiers
                    name = model.get('name', 'Unknown')
                    size = model.get('size', 0) / (1024**3)  # GB
                    console.print(f"   • {name} ({size:.1f}GB)")
                
                self.test_results["ollama"] = True
                return True
            else:
                console.print(f"❌ Ollama: Erreur HTTP {response.status_code}")
        except requests.RequestException as e:
            console.print(f"❌ Ollama: Non accessible ({e})")
        
        console.print("   💡 Démarrez Ollama avec: ollama serve")
        self.test_results["ollama"] = False
        return False
    
    def test_python_imports(self):
        """Test des imports Python critiques"""
        console.print("[blue]🐍 Test des imports Python...[/blue]")
        
        critical_imports = [
            "fastapi",
            "uvicorn", 
            "pydantic_ai",
            "docling",
            "sentence_transformers",
            "chromadb",
            "rich",
            "asyncpg"
        ]
        
        failed_imports = []
        
        for module in critical_imports:
            try:
                __import__(module)
                console.print(f"✅ {module}")
            except ImportError:
                console.print(f"❌ {module}")
                failed_imports.append(module)
        
        if failed_imports:
            console.print(f"[red]Modules manquants: {', '.join(failed_imports)}[/red]")
            console.print("Installez avec: uv sync")
            self.test_results["python_imports"] = False
            return False
        
        self.test_results["python_imports"] = True
        return True
    
    def test_environment_config(self):
        """Test de la configuration d'environnement"""
        console.print("[blue]⚙️ Test de la configuration...[/blue]")
        
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            console.print("❌ Fichier .env manquant")
            console.print("   💡 Créez-le avec: cp .env.example .env")
            self.test_results["environment"] = False
            return False
        
        console.print("✅ Fichier .env trouvé")
        
        # Vérifier les variables critiques
        from dotenv import load_dotenv
        load_dotenv(env_file)
        
        critical_vars = {
            "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "LLM_CHOICE": os.getenv("LLM_CHOICE", "llama3.2"),
            "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        }
        
        for var, value in critical_vars.items():
            console.print(f"✅ {var}: {value}")
        
        self.test_results["environment"] = True
        return True
    
    def test_document_processing(self):
        """Test du traitement de documents"""
        console.print("[blue]📄 Test du traitement de documents...[/blue]")
        
        try:
            # Créer un document de test temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Test Document\n\nCeci est un test de traitement de document pour StudyRAG.")
                test_file = f.name
            
            # Test d'import des modules de traitement
            from ingestion.chunker import chunk_text
            from ingestion.embedder import create_embedder
            
            # Test de chunking
            with open(test_file, 'r') as f:
                content = f.read()
            
            chunks = chunk_text(content, chunk_size=100)
            console.print(f"✅ Chunking: {len(chunks)} chunks créés")
            
            # Test d'embeddings
            embedder = create_embedder()
            embedding = embedder.embed("Test embedding")
            console.print(f"✅ Embeddings: Dimension {len(embedding)}")
            
            # Nettoyer
            os.unlink(test_file)
            
            self.test_results["document_processing"] = True
            return True
            
        except Exception as e:
            console.print(f"❌ Traitement de documents: {e}")
            self.test_results["document_processing"] = False
            return False
    
    def test_database_connection(self):
        """Test de la connexion base de données"""
        console.print("[blue]🗄️ Test de la base de données...[/blue]")
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            database_url = os.getenv("DATABASE_URL", "sqlite:///./study_rag.db")
            
            if database_url.startswith("sqlite"):
                console.print("✅ SQLite configuré (aucune connexion à tester)")
                self.test_results["database"] = True
                return True
            elif database_url.startswith("postgresql"):
                # Test de connexion PostgreSQL
                import asyncpg
                
                async def test_pg():
                    try:
                        conn = await asyncpg.connect(database_url)
                        await conn.fetchval("SELECT 1")
                        await conn.close()
                        return True
                    except Exception as e:
                        console.print(f"❌ PostgreSQL: {e}")
                        return False
                
                result = asyncio.run(test_pg())
                if result:
                    console.print("✅ PostgreSQL: Connexion réussie")
                
                self.test_results["database"] = result
                return result
            else:
                console.print(f"✅ Base de données: {database_url.split('://')[0]}")
                self.test_results["database"] = True
                return True
                
        except Exception as e:
            console.print(f"❌ Base de données: {e}")
            self.test_results["database"] = False
            return False
    
    def test_api_startup(self):
        """Test du démarrage de l'API"""
        console.print("[blue]🌐 Test de l'API...[/blue]")
        
        try:
            # Import de l'app FastAPI
            from app.main import create_app
            app = create_app()
            console.print("✅ API: Application créée avec succès")
            
            # Test des routes principales
            from app.api.routes import api_router
            routes = [route.path for route in api_router.routes]
            console.print(f"✅ API: {len(routes)} routes configurées")
            
            self.test_results["api"] = True
            return True
            
        except Exception as e:
            console.print(f"❌ API: {e}")
            self.test_results["api"] = False
            return False
    
    def test_frontend_setup(self):
        """Test de la configuration frontend"""
        console.print("[blue]⚛️ Test du frontend...[/blue]")
        
        frontend_dir = self.project_root / "frontend"
        
        if not frontend_dir.exists():
            console.print("⚠️ Dossier frontend non trouvé")
            self.test_results["frontend"] = None
            return None
        
        package_json = frontend_dir / "package.json"
        if not package_json.exists():
            console.print("❌ package.json manquant")
            self.test_results["frontend"] = False
            return False
        
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            console.print("❌ node_modules manquant")
            console.print("   💡 Installez avec: cd frontend && npm install")
            self.test_results["frontend"] = False
            return False
        
        console.print("✅ Frontend: Configuration OK")
        self.test_results["frontend"] = True
        return True
    
    def show_summary(self):
        """Affiche le résumé des tests"""
        console.print("\n" + "="*60)
        
        total_tests = len([r for r in self.test_results.values() if r is not None])
        passed_tests = len([r for r in self.test_results.values() if r is True])
        
        if passed_tests == total_tests:
            status_color = "green"
            status_icon = "🎉"
            status_text = "Tous les tests passent!"
        elif passed_tests >= total_tests * 0.8:
            status_color = "yellow"
            status_icon = "⚠️"
            status_text = "La plupart des tests passent"
        else:
            status_color = "red"
            status_icon = "❌"
            status_text = "Plusieurs tests échouent"
        
        console.print(Panel.fit(
            f"[bold {status_color}]{status_icon} Résultats des tests[/bold {status_color}]\n\n"
            f"Tests réussis: {passed_tests}/{total_tests}\n\n"
            f"[bold]Détails:[/bold]\n" +
            "\n".join([
                f"{'✅' if result else '❌' if result is False else '⚠️'} {test.replace('_', ' ').title()}"
                for test, result in self.test_results.items()
            ]) + f"\n\n[bold]{status_text}[/bold]",
            title="📊 Rapport de Test StudyRAG",
            border_style=status_color
        ))
        
        # Recommandations
        if passed_tests < total_tests:
            console.print("\n[bold]🔧 Actions recommandées:[/bold]")
            
            if not self.test_results.get("dependencies"):
                console.print("• Installez les dépendances système manquantes")
            
            if not self.test_results.get("ollama"):
                console.print("• Démarrez Ollama: ollama serve")
                console.print("• Installez un modèle: ollama pull llama3.2")
            
            if not self.test_results.get("python_imports"):
                console.print("• Installez les dépendances Python: uv sync")
            
            if not self.test_results.get("environment"):
                console.print("• Configurez l'environnement: cp .env.example .env")
            
            if self.test_results.get("frontend") is False:
                console.print("• Installez les dépendances frontend: cd frontend && npm install")
        
        console.print("="*60)
        
        return passed_tests == total_tests
    
    def run(self):
        """Lance tous les tests"""
        console.print(Panel.fit(
            "[bold blue]StudyRAG - Tests de Configuration[/bold blue]\n"
            "Vérification que tous les composants sont prêts",
            title="🧪 Test Suite",
            border_style="blue"
        ))
        
        tests = [
            ("Dépendances système", self.test_dependencies),
            ("Ollama", self.test_ollama),
            ("Imports Python", self.test_python_imports),
            ("Configuration", self.test_environment_config),
            ("Traitement documents", self.test_document_processing),
            ("Base de données", self.test_database_connection),
            ("API FastAPI", self.test_api_startup),
            ("Frontend", self.test_frontend_setup),
        ]
        
        for test_name, test_func in tests:
            console.print(f"\n[bold]🧪 {test_name}[/bold]")
            test_func()
        
        return self.show_summary()


def main():
    tester = StudyRAGTester()
    success = tester.run()
    
    if success:
        console.print("\n[green]🚀 Votre StudyRAG est prêt! Lancez: python start.py[/green]")
        return 0
    else:
        console.print("\n[yellow]⚠️ Quelques ajustements sont nécessaires avant le démarrage[/yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())