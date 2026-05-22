# research/

Materiale di reverse engineering: snapshot di proprietà, diff, note sperimentali.

## Struttura
- `snapshots/` — output JSON di `tools/scan_properties.py`. Naming: `<YYYY-MM-DD>-<before|after>-<azione>.json` (es. `2026-05-22-before-speed-change.json`).
- `diffs/` — output di `tools/diff_properties.py` o note di confronto.
- File ad-hoc: ipotesi su modalità, tabelle action sospette, screenshot dell'app Dreamehome (se non sensibili).

## Sicurezza (repo pubblico)
- Snapshot e diff sono **gitignorati di default** — possono contenere DID, MAC, stato dispositivo.
- Per condividere esempi in docs/README, crea versione redacted con placeholder e committala esplicitamente (es. `example.json` non gitignorato).
- **Mai** committare token, refresh token o header di auth.

## Procedura discovery (riassunto, dettagli nella spec)
1. `tools/scan_properties.py --output before.json ...`
2. Cambia una funzione dall'app Dreamehome (una alla volta).
3. `tools/scan_properties.py --output after.json ...`
4. `tools/diff_properties.py before.json after.json`
5. Conferma con un secondo ciclo. Aggiorna `docs/property_map.md`.
