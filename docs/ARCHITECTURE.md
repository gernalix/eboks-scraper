# Architettura e-Boks: sorgenti, deploy e dati

Aggiornato da verifiche dirette su Fedora, 14 novembre 2026. **Non confondere codice esistente, installazione, acquisizione completa e sincronizzazione online.**

## Verifica successiva del 14 novembre 2026, ore 09:30 Copenhagen

Inbox Keepalive è stato caricato dall’utente nel Chrome corrente dal percorso canonico. `verify_runtime.py` rileva `keepalive_chrome_registered=True`; un osservatore diagnostico temporaneo ha registrato il clic automatico Inbox con stack `clickInboxInPage`, poi si è rimosso. Alla fine dell’acquisizione la tab autenticata è stata lasciata aperta. La tabella seguente riporta lo stato aggiornato. La sincronizzazione incrementale è completata per i nuovi messaggi dopo il 27 ottobre (dettagli in WORKFLOW); l’export storico resta incompleto.

## Source of truth

**Unico repository Git canonico:** `gernalix/eboks-scraper`, branch `main`. Checkout operativo storico: `~/projects/eboks-scraper-repo` (eventuali worktree Git di task sono temporanei).

| Componente | Sorgente versionata qui | Deployment/dati locali | Stato verificato |
|---|---|---|---|
| Chrome **e-Boks On-Demand UI Probe** | `extension/ui-probe/{manifest.json,worker.js,native_host.py}` | `~/Documents/ChatGPT/Chrome/.eboks-ondemand-probe/` | File presenti; Native Messaging Host registrato |
| Native Messaging Host della probe | `extension/ui-probe/native_host.py` | `~/.config/google-chrome/NativeMessagingHosts/com.gernalix.eboks_ui_probe.json` → percorso sopra | Registrazione presente per extension ID `imapkpjnpakmnapjgbfjoajdieahphco` |
| Chrome **Inbox Keepalive** (non downloader) | `extension/inbox-keepalive/{manifest.json,worker.js}` | `~/projects/eboks-scraper-repo/extension/inbox-keepalive/` | Registrato in Chrome; test locali e clic automatico Inbox verificati il 14/11/2026 |
| Gestore esportazioni | `scripts/manage_export.py` | `~/Documents/e-Boks/full-export-2026-09-22/manage_export.py` | Copia di runtime presente |
| Importazione ZIP/PDF → SQLite | `scripts/import_archive.py` | Eseguire dal repository canonico | Versionato; locale, idempotente |
| Preflight copertura | `scripts/check_coverage.py` | Eseguire dal repository canonico | Versionato; **non** certifica l'inbox online |
| Mappa runtime | `scripts/verify_runtime.py` | Eseguire dal repository canonico | Read-only; rileva componenti mancanti e drift, non autenticazione |
| Originali | **Mai in Git** | `~/Documents/e-Boks/full-export-2026-09-22/posta-pubblica/batch-*/` e `posta-aziende/batch-*/` | Export storico parziale |
| Stato incrementale | **Mai in Git** | `.../progress.json` | File presente; flag `complete=false` in entrambe le sezioni alla verifica |
| Indice personale | **Mai in Git** | `.../eboks.sqlite` | 566 elementi, 559 con testo estratto, integrità `ok`; ultimo documento 12/11/2026 |
| Ultimo report tecnico della probe | **Mai in Git** | `.../.eboks-ondemand-probe/report.json` | Report 14/11/2026 ore 08:23: solo controlli UI; nessun testo delle lettere |

I percorsi deployed esistono separatamente **perché Chrome carica la sua estensione da quel percorso** e lo stato degli export risiede fuori dal repository. Il repository contiene una copia sorgente riproducibile, **non** una seconda istanza del database o un altro scheduler. `verify_runtime.py` controlla per SHA-256 che i file deployati corrispondano alle versioni Git; dopo modifiche deliberate, aggiornare i deployment soltanto dopo validazione e senza modificare il profilo Chrome in esecuzione.

Altri percorsi storici, **non canonici**: `~/projects/eboks-scraper/` (vecchia copia incompleta del keepalive; eliminabile dopo verifica che Chrome non la usa), `~/Documents/ChatGPT/eboks scraper/` (repository Git vuoto, non sorgente del sistema), `~/projects/codex-roadmap/` (storico esplorazione). Non eliminare dati personali, export o componenti ancora installati. Il seed storico `seeds/eboks-scraper.zip.b64` al commit `13c104c` contiene letteralmente `[... ELLIPSIZATION ...]`; il payload non è un archivio ZIP recuperabile e **non** costituisce un downloader installato.

## Cosa fanno davvero le estensioni

**On-Demand UI Probe**: solo quando si clicca sull'icona dell'estensione in una scheda e-Boks già autenticata, `worker.js` usa `activeTab` e `chrome.scripting.executeScript` per ispezionare checkbox e controlli visibili; invia un report limitato al Native Messaging Host, che lo scrive in `report.json`. La probe **non** seleziona automaticamente messaggi, non scarica ZIP/PDF e non legge corpi delle lettere. Il report è utile solo se acquisito nella scheda `https://digitalpost.e-boks.dk/mailbox` correttamente renderizzata, non su homepage/login. Non attivare la vecchia probe persistente `.eboks-ui-probe`, storicamente associata a pagina bianca dopo MitID.

**Inbox Keepalive**: unico responsabile del mantenimento sessione. `chrome.alarms` richiama la funzione di clic sulla voce Inbox **ogni minuto**, esclusivamente nelle schede Inbox e-Boks già aperte; salta l'operazione in presenza di selezioni attive, dialog di export o editing. Non richiede Native Messaging, non esegue login MitID e non è una garanzia anti-logout (il server può scadere la sessione indipendentemente). **Test Node PASS_LOCAL; installazione in Chrome e clic automatico verificati il 14 novembre 2026**. Per ripristinare un’installazione mancante, caricare la directory unpacked canonica da `chrome://extensions`, senza riavviare il browser né alterare il profilo direttamente; poi verificare un clic del timer. Il tool browser può rifiutare le pagine interne Chrome: in quel caso il caricamento richiede l’utente, senza aggirare il limite con input desktop sintetico. Il keepalive non scarica o legge comunicazioni.

## Interfaccia ufficiale di download

Il percorso storico passava da `Di più`; il 14 novembre è stato verificato su sei messaggi il comando diretto:

`Posta in arrivo` → selezione dei messaggi → `Salva una copia locale` (`Gem en lokal kopi`) → `Salva tutto` → conferma `OK` del salvataggio sul computer.

La pagina del 14 novembre mostrava 15 righe e il pulsante `Mostra altro`. **Non assumere che select-all copra l’intera inbox.** Nel batch corrente sono state selezionate soltanto le sei righe nuove tramite ID e sono stati acquisiti sei PDF più un indice nello ZIP. Un messaggio può produrre più file: ricontrollare sempre UI, allegati e contenuto dell’export, senza riselezionare firme già processate.

## Comando di ingresso unico per ogni nuova richiesta

Dal checkout canonico:

```sh
python3 scripts/verify_runtime.py
python3 scripts/check_coverage.py --since 2026-10-14 --through 2026-11-14
```

Poi **ispezionare la casella online autentica** in entrambe le sezioni. Per i dettagli di download, import, SQL e gestione degli errori seguire [WORKFLOW.md](WORKFLOW.md). `runtime_inventory=LOCAL_OK` non significa che la casella sia sincronizzata.

## Limiti residui dopo l’acquisizione del 14 novembre 2026

Le sei comunicazioni nuove sono state acquisite e lette; entrambe le Inbox sono state confrontate con il confine incrementale del 27 ottobre. Questo controllo non completa l’export storico e non prova l’assenza di messaggi ricevuti dopo l’ultima verifica. Il file `report.json` della probe, generato alle 08:23 da una pagina senza checkbox pertinenti, **non certifica export né lettura lettere**. La nuova acquisizione è provata da ZIP, firme, import e controllo della UI, non dal report della probe.

## Vincoli di sicurezza e conservazione

Non leggere cookie, token, storage del browser o endpoint privati; non iniettare script in fase di login, redirect MitID o bootstrap e-Boks. Solo UI ufficiale già autenticata; stop su CAPTCHA/rate-limit/sessione scaduta. Non modificare o pubblicare originali, ZIP, PDF, database, `progress.json` o `report.json` nel repository pubblico. Non confondere il numero di righe SQLite con il numero dei messaggi (allegati multipli).
