# Flusso e-Boks: acquisizione, SQLite, ricerca degli appuntamenti

## Fonti e confini

- **Fonte primaria:** i messaggi autenticati di e-Boks / Digital Post (posta pubblica e posta da aziende), inclusi gli allegati. L'autenticazione MitID resta manuale; non riusare cookie, token, API interne o estensioni che iniettano codice durante il login.
- **Originali locali:** `$HOME/Documents/e-Boks/full-export-2026-09-22/posta-*/batch-*/` (ZIP/PDF). Non cancellare o modificare gli originali.
- **Stato dell'export:** `.../progress.json` registra firme, batch e ultimo controllo, **non** è la prova che tutto sia stato scaricato. `complete=false` significa export incompleto.
- **Indice derivato:** `.../eboks.sqlite` (tabella `documents`, indice `documents_fts` FTS5). Contiene testo personale: **mai committarlo su GitHub**. Il repository pubblico contiene solo codice e documentazione.
- **Limite corrente:** il repository versiona l'importatore; **non** dispone ancora di un downloader e-Boks funzionante e verificato in autonomia. Nessun servizio periodico di sincronizzazione risulta operativo.

## Flusso corretto per una richiesta come «quali appuntamenti ho oggi?»

1. Verificare data locale `Europe/Copenhagen` e finestra delle **mail ricevute** (per default, ultimo mese). Non cercare indiscriminatamente messaggi vecchi di anni.
2. Aprire l'inbox e-Boks con sessione già autenticata. Verificare **entrambe** le sezioni (posta pubblica e posta da aziende), anche gli ultimi messaggi che non figurano nell'archivio. Identificare per ogni messaggio la data, l'ID o firma, il mittente, l'oggetto e gli allegati. **Non** assumere che la data massima del database sia quella della casella online.
3. Scaricare tramite gli **strumenti ufficiali della UI** soltanto i nuovi messaggi, senza salti. Gestire paginazione e più allegati; usare download ZIP/PDF originali. Deduplicare tramite identificatore del messaggio e archivio, non soltanto tramite data e oggetto. Non usare le notifiche Gmail di Digital Post come sostituto del contenuto.
4. Raccogliere il batch nel percorso originale con lo script locale già esistente `manage_export.py`: eseguire `snapshot` **prima** dei download e `collect --section ... --batch ... --signatures ... --files ...` soltanto dopo aver verificato nomi, firme e file effettivamente scaricati. Non avanzare `progress.json` se il download non è confermato. Non mischiare altri download di Chrome. Se la UI non consente download, segnalare **INCOMPLETO**, non dichiarare assenza di appuntamenti.
5. Importare subito i nuovi ZIP e mantenere il database persistente aggiornato, con un solo comando:

   ```sh
   python3 scripts/import_archive.py \
     --root "$HOME/Documents/e-Boks/full-export-2026-09-22"
   ```

   È **idempotente**: gli ZIP originali sono immutabili; la coppia `source_zip + entry_name` identifica ogni elemento; i checksum rilevano modifiche. PDF tramite `pdftotext`, HTML/TXT in testo; ciò che non è estraibile resta marcato `extracted=0`. SQLite conserva data dal nome del file, provenienza, testo e SHA-256. Nessun OCR automatico. Controllare `integrity=ok`.
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
