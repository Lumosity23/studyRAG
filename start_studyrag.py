#!/usr/bin/env python3
"""
StudyRAG Startup Script
Comprehensive startup script with health checks and configuration validation
"""

import asyncio
import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import psutil

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

class StudyRAGStarter:
    def __init__(self):
        self.config = self.load_config()
        self.health_checks = []
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment and defaults"""
        # Load .env file if it exists
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        
        return {
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///./study_rag.db'),
            'ollama_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'host': os.getenv('HOST', '0.0.0.0'),
            'port': int(os.getenv('PORT', 8000)),
            'debug': os.getenv('DEBUG', 'true').lower() == 'true',
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'llm_choice': os.getenv('LLM_CHOICE', 'llama3.2'),
            'embedding_model': os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        }
    
    def print_banner(self):
        """Print startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                        StudyRAG                              ║
║              Assistant IA pour Documents Académiques         ║
║                                                              ║
║  🧠 Analyse intelligente de documents                        ║
║  💬 Chat en temps réel avec WebSocket                       ║
║  🔍 Recherche sémantique avancée                            ║
║  📄 Support multi-formats (PDF, DOCX, etc.)                 ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def check_python_version(self) -> bool:
        """Check Python version compatibility"""
        print("🐍 Vérification de la version Python...")
        
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
            return True
        else:
            print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (requis: 3.9+)")
            return False
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        print("📦 Vérification des dépendances...")
        
        required_packages = [
            'fastapi',
            'uvicorn', 
            'asyncpg',
            'ollama',
            'sentence_transformers',
            'docling',
            'chromadb'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package} (manquant)")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  Packages manquants: {', '.join(missing_packages)}")
            print("💡 Installez avec: uv sync")
            return False
        
        return True
    
    def check_database_connection(self) -> bool:
        """Check database connectivity"""
        print("🗄️  Vérification de la base de données...")
        
        db_url = self.config['database_url']
        
        # Check database type
        if db_url.startswith('sqlite'):
            print("  ℹ️  Utilisation de SQLite (base de données locale)")
            try:
                import sqlite3
                # Extract path from sqlite:///./study_rag.db
                db_path = db_url.replace('sqlite:///', '')
                
                # Test connection
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                print("  ✅ Base de données SQLite accessible")
                return True
            except Exception as e:
                print(f"  ❌ Erreur SQLite: {e}")
                return False
                
        elif db_url.startswith('postgresql'):
            print("  ℹ️  Utilisation de PostgreSQL")
            try:
                import asyncpg
                
                async def test_connection():
                    try:
                        conn = await asyncpg.connect(db_url)
                        await conn.fetchval("SELECT 1")
                        await conn.close()
                        return True
                    except Exception as e:
                        print(f"  ❌ Erreur de connexion PostgreSQL: {e}")
                        return False
                
                result = asyncio.run(test_connection())
                if result:
                    print("  ✅ Base de données PostgreSQL accessible")
                    return True
                else:
                    print("  ❌ Impossible de se connecter à PostgreSQL")
                    print(f"  💡 URL: {db_url}")
                    return False
                    
            except ImportError:
                print("  ❌ asyncpg non installé pour PostgreSQL")
                return False
        else:
            print(f"  ⚠️  Type de base de données non reconnu: {db_url}")
            print("  💡 Tentative de connexion générique...")
            return True  # Assume it will work
    
    def check_ollama_service(self) -> bool:
        """Check Ollama service availability"""
        print("🤖 Vérification du service Ollama...")
        
        try:
            response = requests.get(f"{self.config['ollama_url']}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                print(f"  ✅ Ollama accessible ({len(models)} modèles disponibles)")
                
                # Check if preferred model is available
                model_names = [model['name'] for model in models]
                if any(self.config['llm_choice'] in name for name in model_names):
                    print(f"  ✅ Modèle {self.config['llm_choice']} disponible")
                else:
                    print(f"  ⚠️  Modèle {self.config['llm_choice']} non trouvé")
                    print(f"  💡 Modèles disponibles: {', '.join(model_names[:3])}")
                
                return True
            else:
                print(f"  ❌ Ollama répond avec le code {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("  ❌ Impossible de se connecter à Ollama")
            print(f"  💡 URL: {self.config['ollama_url']}")
            print("  💡 Démarrez Ollama avec: ollama serve")
            return False
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            return False
    
    def check_directories(self) -> bool:
        """Check and create required directories"""
        print("📁 Vérification des répertoires...")
        
        required_dirs = [
            'static',
            'temp_files',
            'documents',
            'chroma_db'
        ]
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                print(f"  ✅ {dir_name}/")
            else:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"  ✅ {dir_name}/ (créé)")
                except Exception as e:
                    print(f"  ❌ Impossible de créer {dir_name}/: {e}")
                    return False
        
        return True
    
    def check_static_files(self) -> bool:
        """Check static files are present"""
        print("🌐 Vérification des fichiers statiques...")
        
        required_files = [
            'static/index.html',
            'static/app.js',
            'static/styles.css'
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} manquant")
                return False
        
        return True
    
    def check_port_availability(self) -> bool:
        """Check if the port is available"""
        print(f"🔌 Vérification du port {self.config['port']}...")
        
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', self.config['port']))
                if result == 0:
                    print(f"  ❌ Port {self.config['port']} déjà utilisé")
                    
                    # Try to find what's using the port
                    for proc in psutil.process_iter(['pid', 'name', 'connections']):
                        try:
                            for conn in proc.info['connections'] or []:
                                if conn.laddr.port == self.config['port']:
                                    print(f"  💡 Utilisé par: {proc.info['name']} (PID: {proc.info['pid']})")
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    return False
                else:
                    print(f"  ✅ Port {self.config['port']} disponible")
                    return True
        except Exception as e:
            print(f"  ⚠️  Impossible de vérifier le port: {e}")
            return True  # Assume it's available
    
    def run_health_checks(self) -> bool:
        """Run all health checks"""
        print("🏥 Exécution des vérifications de santé...\n")
        
        checks = [
            ("Version Python", self.check_python_version),
            ("Dépendances", self.check_dependencies),
            ("Base de données", self.check_database_connection),
            ("Service Ollama", self.check_ollama_service),
            ("Répertoires", self.check_directories),
            ("Fichiers statiques", self.check_static_files),
            ("Disponibilité du port", self.check_port_availability)
        ]
        
        passed = 0
        total = len(checks)
        
        for check_name, check_func in checks:
            print(f"📋 {check_name}:")
            try:
                result = check_func()
                if result:
                    passed += 1
                print()  # Empty line for readability
            except Exception as e:
                print(f"  ❌ Erreur inattendue: {e}\n")
        
        print(f"📊 Résultat: {passed}/{total} vérifications réussies")
        
        if passed == total:
            print("🎉 Toutes les vérifications sont passées!")
            return True
        else:
            print("⚠️  Certaines vérifications ont échoué.")
            return False
    
    def show_configuration(self):
        """Display current configuration"""
        print("⚙️  Configuration actuelle:")
        print(f"  🗄️  Base de données: {self.config['database_url']}")
        print(f"  🤖 Ollama: {self.config['ollama_url']}")
        print(f"  🧠 Modèle LLM: {self.config['llm_choice']}")
        print(f"  📊 Embeddings: {self.config['embedding_model']}")
        print(f"  🌐 Serveur: {self.config['host']}:{self.config['port']}")
        print(f"  🐛 Debug: {self.config['debug']}")
        if self.config['openai_api_key']:
            print(f"  🔑 OpenAI: Configuré (fallback)")
        print()
    
    def start_server(self):
        """Start the FastAPI server"""
        print("🚀 Démarrage du serveur StudyRAG...")
        print(f"📱 Interface web: http://localhost:{self.config['port']}")
        print(f"📚 Documentation API: http://localhost:{self.config['port']}/docs")
        print(f"🔍 Health check: http://localhost:{self.config['port']}/health")
        print("\n🔄 Le serveur redémarre automatiquement lors des modifications")
        print("⏹️  Utilisez Ctrl+C pour arrêter le serveur\n")
        
        try:
            import uvicorn
            uvicorn.run(
                "app.main:app",
                host=self.config['host'],
                port=self.config['port'],
                reload=self.config['debug'],
                log_level="info" if self.config['debug'] else "warning"
            )
        except KeyboardInterrupt:
            print("\n👋 Serveur arrêté par l'utilisateur")
        except Exception as e:
            print(f"\n❌ Erreur lors du démarrage: {e}")
            return False
        
        return True
    
    def run(self):
        """Main execution flow"""
        self.print_banner()
        
        # Show configuration
        self.show_configuration()
        
        # Run health checks
        if not self.run_health_checks():
            print("\n❌ Impossible de démarrer à cause des erreurs ci-dessus.")
            print("💡 Corrigez les problèmes et relancez le script.")
            return 1
        
        # Ask user if they want to continue
        try:
            print("\n🚀 Prêt à démarrer le serveur!")
            start = input("Continuer? (Y/n): ").lower().strip()
            if start in ['', 'y', 'yes', 'oui']:
                self.start_server()
            else:
                print("👋 Démarrage annulé par l'utilisateur")
                return 0
        except KeyboardInterrupt:
            print("\n👋 Démarrage annulé par l'utilisateur")
            return 0
        
        return 0

def main():
    """Entry point"""
    starter = StudyRAGStarter()
    return starter.run()

if __name__ == "__main__":
    sys.exit(main())