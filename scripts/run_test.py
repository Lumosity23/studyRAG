#!/usr/bin/env python3
"""
Script pour lancer le test complet : parsing + évaluation
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console

console = Console()

def run_test():
    """Lance le test complet du système"""
    
    console.print("[bold blue]🧪 LANCEMENT DU TEST COMPLET[/bold blue]")
    console.print()
    
    # Étape 1: Parser le document de test
    console.print("[cyan]Étape 1: Parsing du document de test...[/cyan]")
    try:
        result = subprocess.run([
            sys.executable, "main.py", "parse", "test_document.md"
        ], capture_output=True, text=True, check=True)
        
        console.print("[green]✓ Parsing réussi![/green]")
        if result.stdout:
            console.print(result.stdout)
            
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Erreur lors du parsing: {e}[/red]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        return False
    
    console.print()
    
    # Étape 2: Évaluer les résultats
    console.print("[cyan]Étape 2: Évaluation des résultats...[/cyan]")
    try:
        result = subprocess.run([
            sys.executable, "test_evaluation.py"
        ], capture_output=True, text=True, check=True)
        
        console.print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Erreur lors de l'évaluation: {e}[/red]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        return False
    
    console.print()
    console.print("[bold green]🎉 Test terminé![/bold green]")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)