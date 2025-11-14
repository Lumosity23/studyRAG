# Échantillons de Test

Ce dossier contient des fichiers d'exemple pour tester les différents formats supportés par le système.

## Fichiers disponibles

- `test_document.docx` - Document Word de test
- `test_document.html` - Document HTML de test  
- `test_document.md` - Document Markdown de test
- `esp32-c3-mini-1_datasheet_en.pdf` - PDF technique d'exemple

## Usage

Ces fichiers peuvent être utilisés pour :
- Tester l'ingestion de documents
- Valider le traitement de différents formats
- Développer et déboguer les fonctionnalités

```bash
# Tester l'ingestion avec ces échantillons
uv run python -m ingestion.ingest --documents test_samples/
```