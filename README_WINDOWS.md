# StudyRAG - Guide pour Nouveaux Développeurs Windows

## 🎯 Pour un développeur Windows sans rien d'installé

Si vous êtes sur Windows et n'avez **aucun outil de développement** installé (pas de Python, Git, etc.), ce guide est fait pour vous !

## 🚀 Installation Ultra-Rapide (2 clics)

### Méthode 1: Script Batch (Recommandé pour débutants)

1. **Télécharger le projet**
   - Aller sur GitHub et cliquer "Download ZIP"
   - Extraire le dossier sur votre Bureau

2. **Lancer l'installation**
   - Double-cliquer sur `setup.bat`
   - Accepter les privilèges administrateur quand demandé
   - Suivre les instructions à l'écran

**C'est tout !** Le script installe automatiquement :
- Chocolatey (gestionnaire de paquets Windows)
- Python 3.11
- Git
- PostgreSQL 15
- UV (gestionnaire de dépendances)
- Ollama (IA locale)
- Toutes les dépendances du projet

### Méthode 2: PowerShell (Plus de contrôle)

1. **Ouvrir PowerShell en administrateur**
   - Clic droit sur le bouton Windows
   - "Windows PowerShell (Admin)" ou "Terminal (Admin)"

2. **Naviguer vers le projet**
   ```powershell
   cd "C:\Users\VotreNom\Desktop\studyrag"
   ```

3. **Lancer le setup**
   ```powershell
   .\setup.ps1
   ```

## ⏱️ Temps d'installation

- **Installation complète** : 15-30 minutes
- **Téléchargement modèle IA** : 5-15 minutes (selon connexion)
- **Total** : ~45 minutes maximum

## 🔧 Ce qui sera installé

### Outils de développement
- **Python 3.11** - Langage de programmation
- **Git** - Gestion de versions
- **UV** - Gestionnaire de dépendances Python moderne

### Base de données
- **PostgreSQL 15** - Base de données
- **Mot de passe** : `studyrag123`
- **Configuration automatique** de la base `studyrag`

### Intelligence Artificielle
- **Ollama** - Serveur IA local
- **Modèle llama3.2** - IA pour répondre aux questions
- **Embeddings locaux** - Pour la recherche sémantique

### Dépendances Python
- FastAPI, AsyncPG, Rich, PydanticAI, Docling
- Plus de 50 packages installés automatiquement

## 🎉 Après l'installation

### 1. Tester l'installation
```powershell
# Ouvrir PowerShell dans le dossier du projet
cd "C:\chemin\vers\studyrag"

# Vérifier que tout fonctionne
python scripts/post_setup_check.py
```

### 2. Première utilisation
```powershell
# Ingérer les documents d'exemple
uv run python -m ingestion.ingest --documents test_samples/

# Lancer l'interface interactive
uv run python cli.py
```

### 3. Poser votre première question
Dans le CLI, tapez : `"Qu'est-ce que StudyRAG ?"`

## 🆘 Problèmes courants

### "Execution Policy" PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### PostgreSQL ne démarre pas
```powershell
# Vérifier le service
Get-Service postgresql*

# Démarrer manuellement
Start-Service postgresql-x64-15
```

### Ollama non accessible
```powershell
# Redémarrer Ollama
taskkill /f /im ollama.exe
ollama serve
```

### Python/UV non trouvé après installation
- **Redémarrer PowerShell/Terminal**
- Les nouveaux programmes sont ajoutés au PATH

## 📁 Structure après installation

```
studyrag/
├── setup.bat              # Script d'installation (celui que vous avez lancé)
├── setup.ps1              # Script PowerShell détaillé
├── .env                   # Configuration (créé automatiquement)
├── cli.py                 # Interface en ligne de commande
├── rag_agent.py           # Agent IA principal
├── test_samples/          # Documents d'exemple
├── docs/                  # Documentation
└── scripts/               # Scripts de test et maintenance
```

## 🎓 Prochaines étapes

### Apprendre à utiliser StudyRAG
1. **Lire la documentation** : Dossier `docs/`
2. **Tester avec vos documents** : Placer vos PDF dans `documents/`
3. **Explorer le CLI** : `uv run python cli.py`

### Développement
1. **Éditeur recommandé** : VS Code avec extension Python
2. **Tests** : `python scripts/verify_implementation.py`
3. **Documentation** : `docs/development-guidelines.md`

## 💡 Conseils pour débutants

### Commandes essentielles
```powershell
# Naviguer dans les dossiers
cd "C:\chemin\vers\dossier"

# Lister les fichiers
dir

# Lancer StudyRAG
uv run python cli.py

# Voir l'aide
uv run python cli.py --help
```

### Fichiers importants
- **`.env`** : Configuration (mots de passe, URLs)
- **`cli.py`** : Interface principale
- **`test_samples/`** : Documents pour tester
- **`docs/`** : Toute la documentation

### En cas de problème
1. **Redémarrer PowerShell** (souvent suffisant)
2. **Relancer `setup.bat`** (sans danger, détecte ce qui est installé)
3. **Consulter `SETUP.md`** pour le dépannage détaillé
4. **Lancer les tests** : `python scripts/post_setup_check.py`

## 🌟 Félicitations !

Vous avez maintenant un environnement de développement IA complet sur Windows !

StudyRAG peut :
- ✅ Lire vos documents PDF, Word, PowerPoint
- ✅ Répondre à vos questions sur leur contenu
- ✅ Fonctionner 100% en local (confidentialité totale)
- ✅ Citer ses sources avec précision

**Bon apprentissage avec StudyRAG !** 🚀