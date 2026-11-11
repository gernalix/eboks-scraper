# e-Boks scraper

Documentazione e strumenti per l'indicizzazione locale dei messaggi e-Boks.

- [Flusso di acquisizione, importazione SQLite e ricerca appuntamenti](docs/WORKFLOW.md)
- Importazione idempotente: `python3 scripts/import_archive.py`

**Stato:** la lettura/esportazione incrementale dalla casella online non è ancora automatizzata e verificata. La presenza di dati in SQLite non dimostra che la casella e-Boks sia aggiornata. I messaggi originali e i database personali restano fuori da Git.
