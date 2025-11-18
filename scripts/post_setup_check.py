#!/usr/bin/env python3
"""
Script de vérification post-setup
Vérifie que tous les composants sont correctement configurés après le setup
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def check_database():
    """Vérifie la connexion à la base de données"""
    try:
        import asyncpg
        from utils.db_utils import get_database_url
        
        db_url = get_database_url()
        conn = await asyncpg.connect(db_url)
        
        # Test simple
        result = await conn.fetchval("SELECT 1")
        
        # Vérifier les tables
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        await conn.close()
        
        return {
            "status": "✅",
            "details": f"{len(tables)} tables trouvées",
            "error": None
        }
        
    except Exception as e:
        return {
            "status": "❌",
            "details": "Connexion échouée",
            "error": str(e)
        }

def check_ollama():
    """Vérifie Ollama et les modèles disponibles"""
    try:
        # Vérifier le service
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            models = data.get('models', [])
            model_names = [m['name'] for m in models]
            
            return {
                "status": "✅",
                "details": f"{len(models)} modèles: {', '.join(model_names[:3])}",
                "error": None
            }
        else:
            return {
                "status": "❌",
                "details": "Service non accessible",
                "error": "Curl failed"
            }
            
    except Exception as e:
        return {
            "status": "❌",
            "details": "Erreur de connexion",
            "error": str(e)
        }

def check_embeddings():
    """Vérifie les modèles d'embeddings"""
    try:
        from utils.embedder import create_embedder
        
        embedder = create_embedder()
        test_embedding = embedder.embed("test")
        
        return {
            "status": "✅",
            "details": f"Dimension: {len(test_embedding)}",
            "error": None
        }
        
    except Exception as e:
        return {
            "status": "❌",
            "details": "Échec du test",
            "error": str(e)
        }

def check_environment():
    """Vérifie les variables d'environnement"""
    required_vars = [
        "DATABASE_URL",
        "OLLAMA_BASE_URL"
    ]
    
    optional_vars = [
        "OPENAI_API_KEY",
        "LLM_CHOICE",
        "EMBEDDING_MODEL"
    ]
    
    missing = []
    present = []
    
    for var in required_vars:
        if os.getenv(var):
            present.append(var)
        else:
            missing.append(var)
    
    for var in optional_vars:
        if os.getenv(var):
            present.append(var)
    
    if missing:
        return {
            "status": "❌",
            "details": f"Manquantes: {', '.join(missing)}",
            "error": None
        }
    else:
        return {
            "status": "✅",
            "details": f"{len(present)} variables configurées",
            "error": None
        }

def check_dependencies():
    """Vérifie les dépendances Python critiques"""
    critical_deps = [
        "fastapi",
        "asyncpg", 
        "rich",
        "pydantic_ai",
        "docling"
    ]
    
    missing = []
    present = []
    
    for dep in critical_deps:
        try:
            __import__(dep)
            present.append(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        return {
            "status": "❌",
            "details": f"Manquantes: {', '.join(missing)}",
            "error": None
        }
    else:
        return {
            "status": "✅",
            "details": f"{len(present)} dépendances OK",
            "error": None
        }

def check_sample_documents():
    """Vérifie la présence de documents d'exemple"""
    test_samples_dir = Path("test_samples")
    
    if not test_samples_dir.exists():
        return {
            "status": "❌",
            "details": "Dossier test_samples manquant",
            "error": None
        }
    
    files = list(test_samples_dir.glob("*"))
    
    if not files:
        return {
            "status": "⚠️",
            "details": "Dossier vide",
            "error": None
        }
    
    return {
        "status": "✅",
        "details": f"{len(files)} fichiers d'exemple",
        "error": None
    }

async def run_health_check():
    """Lance tous les tests de santé"""
    console.print(Panel.fit(
        "[bold blue]StudyRAG - Vérification Post-Setup[/bold blue]\n"
        "Contrôle de l'état de tous les composants",
        border_style="blue"
    ))
    
    # Tests à effectuer
    checks = [
        ("Variables d'environnement", check_environment),
        ("Dépendances Python", check_dependencies),
        ("Base de données", check_database),
        ("Ollama (LLM)", check_ollama),
        ("Embeddings", check_embeddings),
        ("Documents d'exemple", check_sample_documents)
    ]
    
    # Table des résultats
    table = Table(title="Résultats des Vérifications")
    table.add_column("Composant", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Détails", style="dim")
    
    all_ok = True
    errors = []
    
    for check_name, check_func in checks:
        console.print(f"[blue]Vérification: {check_name}...[/blue]")
        
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
                
            table.add_row(
                check_name,
                result["status"],
                result["details"]
            )
            
            if result["status"] == "❌":
                all_ok = False
                if result["error"]:
                    errors.append(f"{check_name}: {result['error']}")
                    
        except Exception as e:
            table.add_row(
                check_name,
                "❌",
                f"Erreur: {str(e)}"
            )
            all_ok = False
            errors.append(f"{check_name}: {str(e)}")
    
    console.print(table)
    
    # Résumé final
    if all_ok:
        console.print(Panel.fit(
            "[bold green]🎉 Tous les composants sont opérationnels ![/bold green]\n\n"
            "[bold]Prochaines étapes:[/bold]\n"
            "1. [blue]uv run python -m ingestion.ingest --documents test_samples/[/blue]\n"
            "2. [blue]uv run python cli.py[/blue]\n\n"
            "Votre environnement StudyRAG est prêt à l'emploi !",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]⚠️ Problèmes détectés[/bold red]\n\n"
            "Certains composants nécessitent une attention :\n" +
            "\n".join(f"• {error}" for error in errors[:5]) +
            "\n\n[bold]Consultez SETUP.md pour le dépannage[/bold]",
            border_style="red"
        ))
    
    return all_ok

def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        console.print("""
[bold]StudyRAG Post-Setup Check[/bold]

Usage: python scripts/post_setup_check.py

Ce script vérifie que tous les composants StudyRAG sont correctement configurés:
• Variables d'environnement
• Dépendances Python
• Connexion base de données
• Service Ollama
• Modèles d'embeddings
• Documents d'exemple

Lancez ce script après avoir exécuté setup.py ou setup.sh
        """)
        return
    
    try:
        success = asyncio.run(run_health_check())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Vérification interrompue[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Erreur inattendue: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()