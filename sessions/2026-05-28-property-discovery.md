# Sessione 2026-05-28 — Discovery proprietà: blade oscillation + test on/off definitivo

## Obiettivo
Continuazione discovery property map MF10. Test on/off da device fisicamente ON.
Mappatura proprietà sconosciute via snapshot before/after con app Dreamehome.

## Cosa abbiamo fatto

### 1. Test on/off definitivo — piid=1 è read-only in qualsiasi stato

Con device fisicamente acceso (`power=1`):
- `set_properties(siid=2, piid=1, value=2)` → **code=80001**

Confermato definitivamente: `piid=1` è read-only sia da standby che da ON.
Non esiste modo di controllare on/off via `set_properties` sul relay cloud Dreame.

### 2. Scan siid=11–20 — nessun siid aggiuntivo esiste

50 probes (siid=11–20 × piid=1–5): tutto code=80001.
Il firmware MF10 espone property esclusivamente su siid=2, siid=3, siid=6.

### 3. Discovery blade_oscillation via snapshot before/after

Metodo: snapshot baseline → cambio da app Dreamehome → snapshot after → diff.
Snapshot conservati in `tmp/` (gitignored).

| Test | Diff | Finding |
|------|------|---------|
| Oscillazione pala sinistra ON | (2,6): 0→1 | blade_oscillation sinistra=1 |
| Oscillazione pala sinistra OFF | (2,6): 1→0 | confermato |
| Oscillazione pala destra ON | (2,6): 0→2 | blade_oscillation destra=2 |
| Oscillazione entrambe ON | (2,6): 2→3 | blade_oscillation entrambe=3 |

**`(2,6)` = blade_oscillation**: enum 0=nessuna, 1=sinistra, 2=destra, 3=entrambe.

Nota: `(2,6)` era annotata in precedenza come "sempre 3, ipotesi angolo oscillazione".
Quella osservazione era corretta nel contesto (entrambe le pale erano attive durante i
test precedenti, quindi il valore era sempre 3).

### 4. Relazione tra (2,6) e (2,7)

- `(2,7)` = oscillation master toggle (0=OFF, 1=ON) — già validato
- `(2,6)` = quale/i pale oscillano — enum indipendente dal master toggle

Da approfondire: se (2,7)=0 e si scrive (2,6)=3, le pale partono?

## Stato codice

`const.py` aggiornato:
- `MF10_PROPERTY_MAP` aggiunto `blade_oscillation: (2,6)`
- Aggiunti enum `MF10_BLADE_OSC_NONE/LEFT/RIGHT/BOTH`
- Rimossa `(2,6)` dai "not yet identified"

`docs/property_map.md` aggiornato con nuovi findings e test table.

### 4. Proprietà aggiuntive scoperte nella stessa sessione

| Test | siid,piid | Valori | Finding |
|------|-----------|--------|---------|
| Tono tasti OFF/ON | (6,7) | 0=off, 1=on | key_tone confermato |
| Display LED OFF/ON | (6,11) | 0=off, 1=on | display confermato (nuova property) |
| Monitoraggio continuo OFF/ON | (2,10) | 0=off, 1=on | continuous_monitoring confermato |
| Timer spegnimento 2h/4h | (2,8) | int=ore, 0=disattivato | off_timer confermato |

### 5. Proprietà non rilevabili via get_properties

- **Velocità oscillazione pale (standard/rapido)**: nessuna property cambia — probabilmente parametro contestuale nel comando di set oscillazione.

### 6. Probing esteso — siid inesistenti

| Range | Risultato |
|-------|-----------|
| siid=7–10 piid=1–5 | tutto 80001 |
| siid=1 piid=1–5 | tutto 80001 |
| siid=4 piid=3–8 | tutto 80001 (solo piid=1,2 esistono) |
| siid=6 piid≥12 | alias di piid=1 (timezone) — non reali |

## Proprietà ancora non identificate

| siid | piid | valore | nota |
|------|------|--------|------|
| 2 | 2 | sempre 0 | invariante in tutti i test |
| 2 | 7 | sempre 0 | invariante in tutti i test oscillazione |
| 4 | 1 | sempre 100 | probabile angolo/range oscillazione orizzontale |
| 4 | 2 | sempre 180 | probabile angolo/range oscillazione verticale |
| 6 | 4 | sempre 0 | sconosciuta |

## Stato finale property map (2026-05-28)

| Property | siid,piid | Validata |
|----------|-----------|---------|
| power | (2,1) | ✅ read-only |
| mode | (2,3) | ✅ |
| fan_speed | (2,4) | ✅ |
| child_lock | (2,5) | ✅ |
| blade_oscillation | (2,6) | ✅ enum 0/1/2/3 |
| sync_oscillation | (2,11) | ✅ |
| staggered_oscillation | (2,12) | ✅ |
| continuous_monitoring | (2,10) | ✅ |
| off_timer | (2,8) | ✅ int ore |
| temperature | (3,2) | ✅ read-only |
| key_tone | (6,7) | ✅ |
| display | (6,11) | ✅ |

## Prossimi passi

1. Implementare entità HA per le nuove property (switch, select, number)
2. Indagare (4,1) e (4,2) — probabile angolo oscillazione
3. Chiarire (2,2) e (2,7) — ancora sconosciute
