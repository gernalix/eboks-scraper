# Flusso e-Boks: acquisizione, SQLite, ricerca degli appuntamenti

**Inizio obbligatorio per ogni nuova richiesta:** [ARCHITECTURE.md](ARCHITECTURE.md) descrive repository canonico, estensioni Chrome già create, deployment, host nativo e archivio. Evitare di ricostruire il progetto da zero. Sul checkout Git canonico eseguire:

```sh
python3 scripts/verify_runtime.py
```

`runtime_inventory=LOCAL_OK` conferma solo file installati e indice locale: **non prova** di avere scaricato i nuovi messaggi.

## Fonti e confini

- **Fonte primaria:** i messaggi autenticati di e-Boks / Digital Post (posta pubblica e posta da aziende), inclusi gli allegati. L'autenticazione MitID resta manuale; non riusare cookie, token, API interne o estensioni che iniettano codice durante il login.
- **Originali locali:** `$HOME/Documents/e-Boks/full-export-2026-09-22/posta-*/batch-*/` (ZIP/PDF). Non cancellare o modificare gli originali.
- **Stato dell'export:** `.../progress.json` registra firme, batch e ultimo controllo, **non** è la prova che tutto sia stato scaricato. `complete=false` significa export incompleto.
- **Indice derivato:** `.../eboks.sqlite` (tabella `documents`, indice `documents_fts` FTS5). Contiene testo personale: **mai committarlo su GitHub**. Il repository pubblico contiene solo codice e documentazione.
- **Limite corrente:** l'estensione `e-Boks On-Demand UI Probe` è presente e registrata in Chrome, ma **ispeziona solo i controlli UI su click**, non scarica né legge le lettere. Il downloader automatico originariamente previsto non risulta installato/verificato. Nessun servizio periodico e-Boks di sincronizzazione risulta operativo. L'ulteriore estensione `Inbox Keepalive` non effettua scraping.

## Flusso corretto per una richiesta come «quali appuntamenti ho oggi?»

1. Verificare data locale `Europe/Copenhagen` e finestra delle **mail ricevute** (per default, ultimo mese). Non cercare indiscriminatamente messaggi vecchi di anni.
2. Aprire l'inbox e-Boks con sessione già autenticata. Verificare **entrambe** le sezioni (posta pubblica e posta da aziende), anche gli ultimi messaggi che non figurano nell'archivio. Identificare per ogni messaggio la data, l'ID o firma, il mittente, l'oggetto e gli allegati. **Non** assumere che la data massima del database sia quella della casella online. Il badge dei non letti **non** è il numero totale di comunicazioni.

   **Estensione corretta:** selezionare prima la tab autenticata `https://digitalpost.e-boks.dk/mailbox` completamente renderizzata e attivare *e-Boks On-Demand UI Probe* tramite l'icona di Chrome. La sua `report.json` in `~/Documents/ChatGPT/Chrome/.eboks-ondemand-probe/` contiene soltanto metadati dei controlli. Se il report è di un'altra tab (es. homepage), rifarlo sulla tab corretta; `checkbox_count=0` **non** significa inbox vuota. Non caricare la vecchia estensione persistente che interferiva con il post-login. La lettura passiva della tab tramite il connettore Browser non abilita click/download.
3. Scaricare tramite gli **strumenti ufficiali della UI** soltanto i nuovi messaggi, senza salti. Il percorso storicamente testato su 2 messaggi è **seleziona righe → Di più → Salva una copia locale/Gem en lokal kopi → Salva tutto**. Era possibile selezionare fino a 15 righe caricate; `Mostra altro` aggiunge righe, mentre select-all non copre automaticamente tutta l'inbox. Verificare che questi limiti valgano ancora prima di usarli. Non riscansionare/riscaricare righe con firma già registrata. Gestire paginazione e più allegati; usare download ZIP/PDF originali. Deduplicare tramite identificatore del messaggio e archivio, non soltanto tramite data e oggetto. Non usare le notifiche Gmail di Digital Post come sostituto del contenuto.
4. Raccogliere il batch con lo script versionato `scripts/manage_export.py` (copia deployata a fianco di `progress.json`). Eseguire `python3 scripts/manage_export.py snapshot` **prima** dei download, poi `python3 scripts/manage_export.py collect --section posta-pubblica --batch N --signatures '["firma-stabile-1","firma-stabile-2"]' --files 'nome1.zip'` usando solo firme *reali* e nomi *esatti* di file appena scaricati (sostituire sezione/batch/nomi secondo il caso). Per salvare più PDF aggiungere tutti i nomi dopo `--files`. Il collector vieta download preesistenti, ZIP corrotti e batch già registrati; segnala `crdownload_timeout` quando un download non è completo. **Non** usare `complete` salvo esaurimento della paginazione per entrambe le sezioni, verificato dalla UI. Non avanzare `progress.json` se il download non è confermato. Non mischiare altri download di Chrome. Se la UI non consente download, segnalare **INCOMPLETO**, non dichiarare assenza di appuntamenti.
5. Importare subito i nuovi ZIP e mantenere il database persistente aggiornato, con un solo comando:

   ```sh
   python3 scripts/import_archive.py \
     --root "$HOME/Documents/e-Boks/full-export-2026-09-22"
   ```

   È **idempotente**: gli ZIP originali sono immutabili; la coppia `source_zip + entry_name` identifica ogni elemento; i checksum rilevano modifiche. Sono importati **sia i membri degli ZIP sia i PDF singoli salvati direttamente nella directory `batch-*/`** (non le copie estratte in `documenti/`). PDF tramite `pdftotext`, HTML/TXT in testo; ciò che non è estraibile resta marcato `extracted=0`. SQLite conserva data dal nome del file, provenienza, testo e SHA-256. Il numero di record è il numero di *file*, non necessariamente il numero di messaggi. Nessun OCR automatico. Controllare `integrity=ok`.
5bis. Eseguire il **controllo di copertura** prima di qualsiasi risposta negativa:

   ```sh
   python3 scripts/check_coverage.py --since 2026-10-11 --through 2026-11-11 \
     --notification-at 2026-11-05T15:00:00+00:00
   ```

   Passare ogni data/ora di notifica Digital Post pertinente recuperata da Gmail.
   `coverage_gate=BLOCK` (exit code 2) impedisce di dichiarare l'assenza di
   appuntamenti: il controllo online è troppo vecchio, alcune notifiche sono
   successive all'export, mancano documenti in SQLite oppure c'è testo non estratto.
   `LOCAL_PRECHECK_OK` è **solo una condizione necessaria**: non dimostra che
   la casella online sia stata letta integralmente né che ogni notifica
   corrisponda a una specifica lettera archiviata. Verificare la corrispondenza
   sulla UI ufficiale prima di dichiarare `SINCRONIZZAZIONE_EBOKS_VERIFICATA`.

6. **Solo dopo la sincronizzazione**, interrogare con SQL/FTS5 ogni corpo testuale del mese, non soltanto i nomi file. Cercare la data dell'**appuntamento** nelle varianti danesi, italiane e numeriche (ad esempio `11. november 2026`, `11/11/2026`, `2026-11-11`, `onsdag den 11. november`), comprese date separate da interruzioni di riga o prive dell'anno. Non confondere data del documento, termine amministrativo e giorno dell'incontro.
7. Aprire per intero **ogni lettera candidata** e controllare conferme, revoche, spostamenti e versioni successive. Un'ultima convocazione prevale su una vecchia solo se lo stesso caso/appuntamento è identificabile. Riportare esclusivamente appuntamenti confermati da e-Boks, con **orario, luogo, mittente, data e documento di origine**; segnalare quelli senza orario o con incertezza.
8. Fornire il risultato con due stati distinti: `ARCHIVIO_VERIFICATO` e `SINCRONIZZAZIONE_EBOKS_VERIFICATA`. Una ricerca vuota nel solo SQLite non prova che non esistano nuove convocazioni online.

Esempio di selezione dei documenti del mese (la data `received_date` deriva dal prefisso dei nomi ZIP; non va scambiata per una data di appuntamento):

```sql
SELECT received_date, source_zip, entry_name, body
FROM documents
WHERE received_date BETWEEN '2026-10-11' AND '2026-11-11'
ORDER BY received_date DESC, entry_name;
```

Si può usare `documents_fts MATCH 'indkaldelse OR samtale OR møde OR tid'` per restringere i candidati, **mai come unico filtro**, perché una convocazione può usare termini differenti. Il controllo finale esamina tutti i documenti del periodo.

## Acquisizione incrementale del 14 novembre 2026, successiva alla ricognizione

- Sei nuovi messaggi pubblici esportati dalla UI ufficiale in batch 93: sei PDF e un file indice, tutti importati; nessun nuovo messaggio aziende (ordine per data decrescente verificato).
- SQLite: 566 elementi, 559 con testo estratto, ultimo documento 12 novembre; integrità `ok`. Secondo import senza nuove righe.
- Confrontate le firme dei messaggi nuovi con il confine già archiviato del 27 ottobre. Sincronizzazione incrementale verificata per quel periodo; export storico ancora incompleto, nessun flag `complete` avanzato.
- Il collector attende soltanto i `.crdownload` corrispondenti ai nomi espliciti richiesti: altri download Chrome non bloccano uno ZIP e-Boks già completo. Test di regressione verifica sia il blocco pertinente sia il download estraneo preservato.
- Il controllo di copertura su un periodo anteriore al confine incrementale resta correttamente `BLOCK`; non estendere la conclusione all’intero archivio storico.
- Keepalive caricato dall’utente tramite la UI interna Chrome. Registrazione rilevata e clic automatico del timer osservato sulla Inbox autenticata (stack `clickInboxInPage`, 14 novembre ore 09:30 Copenhagen); osservatore diagnostico one-shot rimosso automaticamente al clic. La tab è lasciata aperta. Questo non garantisce durata illimitata della sessione server.

## Ricognizione precedente del 14 novembre 2026

- **ARCHIVIO_LOCALE:** `integrity_check=ok`, 559 record, 552 con testo estratto; massimo `received_date=2026-10-27`.
- **PROBE:** installata e host registrato; `report.json` dell'08:23 mostrava zero checkbox da una pagina non utile a verificare i messaggi. **Non è il keepalive**; la funzione keepalive è implementata nell'estensione separata `Inbox Keepalive`, e non è ancora dimostrato che sia caricata nel Chrome reale.
- **INBOX ONLINE:** tab autenticata `digitalpost.e-boks.dk/mailbox` visibile; almeno sei comunicazioni successive al documento più recente del database non ancora acquisite. Non registrare mittenti, oggetti o informazioni personali nei docs pubblici.
- **SINCRONIZZAZIONE_EBOKS_VERIFICATA:** **NO**. Nessun nuovo ZIP scaricato/importato durante questa ricognizione.
- **AZIONE RESIDUA:** acquisire contenuti originali dei sei messaggi dalla UI ufficiale, oltre a verificare la sezione aziende, importare, fare query su tutti i corpi e riconciliare convocazioni, annullamenti e scadenze. Non dichiarare `nessun appuntamento` sulla base del solo indice locale.

## Stato verificato l'11 novembre 2026

- Archivio locale: ultimo import da ZIP il 3 novembre; l'ultimo documento esportato era del **27 ottobre 2026**.
- Indice SQLite creato localmente con **559 elementi, 552 con testo estratto** e `PRAGMA integrity_check = ok`.
- Sono state rilevate **notifiche Digital Post più recenti dell'ultimo archivio**, non ancora riconciliate con gli ZIP. Una ricerca sui soli ZIP è **incompleta**.
- Non dedurre appuntamenti e-Boks da Google Calendar: è una fonte differente.

## Verifica rapida dell'indice

```sh
sqlite3 "$HOME/Documents/e-Boks/full-export-2026-09-22/eboks.sqlite" \
  "PRAGMA integrity_check; SELECT COUNT(*), SUM(extracted) FROM documents;"
```

Il prossimo miglioramento, se richiesto, è un downloader incrementale e-Boks **basato esclusivamente sulla UI ufficiale**, con verifica di completezza; non introdurre un secondo scheduler, nuove credenziali o scritture sul profilo browser.
