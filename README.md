# e-Boks scraper

**Repository canonico per il codice e la documentazione.** Le lettere personali e il database SQLite restano **fuori da Git** su Fedora.

Prima di intervenire sul progetto, leggere:

1. **[Mappa di architettura e deployment](docs/ARCHITECTURE.md)** — percorso canonico, estensioni Chrome esistenti, Native Messaging Host, archivio, componenti verificati e limiti.
2. **[Workflow operativo per scaricare, importare e analizzare la posta](docs/WORKFLOW.md)** — istruzioni ripetibili per ogni richiesta di nuova posta, appuntamenti, scadenze o lettere.

Dalla directory del repository:

```sh
python3 scripts/verify_runtime.py
python3 scripts/import_archive.py
python3 scripts/check_coverage.py --since 2026-10-14 --through 2026-11-14
```

Il primo comando è **solo diagnostico**; il secondo importa gli ZIP e i PDF locali nel database persistente; il terzo verifica se l'indice locale può sostenere una ricerca, ma **non** certifica la completezza della casella online. Adattare le date della ricerca.

## Componenti versionati

- `extension/ui-probe/`: **e-Boks On-Demand UI Probe** + Native Messaging Host; ispeziona i controlli della UI soltanto dopo attivazione nella tab autenticata. **Non scarica automaticamente lettere.**
- `extension/inbox-keepalive/`: unico keepalive; codice corretto con alarm a 1 minuto e guardia UI, **testato localmente ma non ancora installato/verificato nel Chrome attuale**. La On-Demand UI Probe non svolge questa funzione.
- `scripts/manage_export.py`: raccolta verificata in batch dei download ZIP/PDF e aggiornamento `progress.json`.
- `scripts/import_archive.py`: indicizzazione idempotente ZIP/PDF → SQLite/FTS5.
- `scripts/check_coverage.py`: controllo di completezza **locale**, fail-closed.
- `scripts/verify_runtime.py`: mappa runtime/archivio e rilevamento drift codice installato, read-only.

**Stato al 14 novembre 2026:** SQLite integro, 559 elementi (ultimo 27 ottobre); almeno sei comunicazioni successive visibili online e **non ancora acquisite**. Nessun servizio/download automatico e-Boks verificato. Non inferire l'assenza di appuntamenti dai soli record locali.

Eseguire i test mirati con `python3 -m unittest discover -s tests -v` e `node tests/test_keepalive.js`. Ogni modificazione di estensioni deployate richiede validazione e aggiornamento esplicito, senza alterare il profilo Chrome durante MitID.
