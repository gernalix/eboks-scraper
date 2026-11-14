# e-Boks scraper — stato operativo

Fonte canonica per le issue: https://github.com/gernalix/eboks-scraper/issues

- Codice e procedure attive: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/WORKFLOW.md](docs/WORKFLOW.md).
- Il vecchio checkout `~/projects/eboks-scraper/` conserva solo il componente keepalive deployato. Il checkout Git canonico è `~/projects/eboks-scraper-repo/`.
- L'estensione `e-Boks On-Demand UI Probe` è presente, ma non è un downloader. Un downloader incremental e-Boks completamente automatico **non è dimostrato funzionante**.
- Da completare quando l'UI ufficiale è utilizzabile: acquisire tutti i nuovi documenti, riconciliare entrambe le sezioni, importare e verificare le convocazioni. Non registrare `complete=true` senza prova delle due sezioni.
- Evitare nuovi scheduler, orchestratori o codici duplicati; preservare dati e componenti locali.
