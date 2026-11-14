# e-Boks scraper — stato operativo

Fonte canonica per le issue: https://github.com/gernalix/eboks-scraper/issues

- Codice e procedure attive: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/WORKFLOW.md](docs/WORKFLOW.md).
- Il checkout Git canonico è `~/projects/eboks-scraper-repo/`; Chrome usa il keepalive nella sua directory `extension/inbox-keepalive/`. Il vecchio percorso `~/projects/eboks-scraper/` non è il deployment corrente.
- L'estensione `e-Boks On-Demand UI Probe` è presente, ma non è un downloader. Un downloader incremental e-Boks completamente automatico **non è dimostrato funzionante**.
- Acquisizione incrementale del 14 novembre completata: sei nuove comunicazioni pubbliche importate, nessuna novità aziende. Keepalive installato e un clic automatico osservato. Per nuove richieste ricontrollare online entrambe le sezioni; l’export storico resta incompleto. Non registrare `complete=true` senza esaurire la paginazione storica.
- Chiusura Git del 14 novembre: PR #7 e #8 integrate; vecchio worktree archiviato privatamente e branch completati ritirati. Verificare la pulizia corrente con Git/GitHub e `mv-git-purify --project eboks-scraper --plan`, senza dedurla dai soli docs.
- Evitare nuovi scheduler, orchestratori o codici duplicati; preservare dati e componenti locali.
