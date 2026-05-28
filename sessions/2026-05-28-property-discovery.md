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

## Proprietà ancora da identificare

| siid | piid | valore osservato | prossimo test |
|------|------|-----------------|---------------|
| 2 | 2 | sempre 0 | ? |
| 2 | 8 | sempre 0 | ? |
| 2 | 10 | sempre 1 | ? |
| 6 | 7 | sempre 1 | toggle buzzer/display dall'app |

## Prossimi passi

1. Continuare discovery: buzzer, display, altre property siid=6
2. Implementare entità HA per blade_oscillation (select o due switch)
3. Verificare relazione (2,6) vs (2,7) con test isolati
