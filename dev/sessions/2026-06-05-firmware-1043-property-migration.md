# 2026-06-05 — Migrazione property map firmware 1043 / plugin 116

## Problema

Aggiornamento firmware 1035→1043 (plugin 104→116) ha rotto l'integrazione:
`Command get_properties failed: code=80001` al primo polling.

Root cause: il coordinator invia tutte le property in un unico batch. Il Dreame Cloud
rifiuta l'intera busta con code=80001 se anche una sola `(siid,piid)` non esiste nella
spec del firmware corrente.

## Property cambiate in firmware 1043

### Spostate
| Feature | fw1035 | fw1043 | Metodo di conferma |
|---|---|---|---|
| `child_lock` | (2,5) | **(6,10)** | diff before/after toggle app |
| `blade_oscillation` | (2,6) | **(2,8)** | diff before/after oscillazione sfalsata (valore 0→3=both) |
| `sync_oscillation` | (2,11) | **(2,9)** | diff before/after sincronizzazione (valore 0→1); confermato con get singolo (2,9)=1 |

### Rimosse dall'integrazione (su richiesta utente)
| Feature | fw1035 | Motivo rimozione |
|---|---|---|
| `key_tone` | (6,7) | Property dinamica: 80001 quando OFF, 1 quando ON → incompatibile con batch polling. Rimossa per semplicità. |
| `display` LED | (6,11) | In fw1043 (6,11) restituisce la stringa timezone ("Europe/Rome"), non è più il LED display. |
| `off_timer` | (2,8) | (2,8) è ora `blade_oscillation`. Nuova posizione dell'off_timer sconosciuta. Rimossa su richiesta utente. |

### Semantica cambiata (non confermata, da validare)
| Feature | piid | fw1035 | fw1043 osservato |
|---|---|---|---|
| `continuous_monitoring` | (2,10) | 0=off, 1=on | Restituisce 2 quando fan spento, 1 quando fan acceso. Rimossa dall'integrazione. |

> Nota: l'ipotesi iniziale che `sync_oscillation` (2,11) leggesse "1 quando off" era
> sbagliata — (2,11) è semplicemente **deprecata** e la property si è spostata a (2,9).
> Confermato con diff before/after sincronizzazione dall'app.

### Invariate e confermate
- `power` (2,1), `mode` (2,3), `fan_speed` (2,4): invariate ✓
- `device_rotation` (2,7): invariata ✓
- `staggered_oscillation` (2,12): 0=off, 1=on — confermata con diff ✓
- `temperature` (3,2): invariata ✓

## Nuovo panorama siid=2 e siid=6 in fw1043

### siid=2 (piid 1–20 scansionati)
Valori "baseline" con fan acceso:

| piid | valore | identificata? |
|---|---|---|
| 1 | 1 | power (1=on) |
| 2 | 0 | sconosciuta |
| 3 | 0 | mode (AI) |
| 4 | 4 | fan_speed |
| 5 | 80001 | sconosciuta (era child_lock, ora 80001) |
| 6 | 80001 | sconosciuta (era blade_oscillation, ora 80001) |
| 7 | 0 | device_rotation |
| 8 | 0 | **blade_oscillation** (0=none, 3=both) |
| 9 | 0 | sconosciuta |
| 10 | 1 | continuous_monitoring (semantica incerta) |
| 11 | 1 | sync_oscillation (semantica incerta) |
| 12 | 0 | staggered_oscillation (0=off, 1=on) ✓ |
| 13–19 | 1 | sconosciute — tutte 1 con fan acceso, 2 con fan spento |
| 20 | 0 | sconosciuta |

### siid=6 (piid 1–20+)
| piid | valore tipico | identificata? |
|---|---|---|
| 1 | "Europe/Rome" | timezone |
| 2 | "" | sconosciuta |
| 3 | 80001 | inaccessibile |
| 4 | 0 | sconosciuta |
| 5 | dinamico | legato a key_tone (1 quando key_tone OFF) |
| 6 | 80001 | inaccessibile |
| 7 | dinamico | key_tone (1 quando ON, 80001 quando OFF) |
| 8 | 0 | sconosciuta |
| 9 | 80001 | inaccessibile |
| 10 | 0/1 | **child_lock** (0=off, 1=on) ✓ |
| 11 | "Europe/Rome" | timezone (era display LED in fw1035) |
| 12 | 1 | sconosciuta |
| 13–19 | "Europe/Rome" o 1 | prevalentemente timezone duplicata |
| 20 | "" | sconosciuta |
| 21–29 | "" | vuote |
| 30 | 1 | sconosciuta |

## Modifiche al codice

File aggiornati:
- `const.py`: property map aggiornata, rimossi key_tone/display/off_timer, "number" rimosso da PLATFORMS
- `switch.py`: rimossi switch key_tone e display (rimangono: child_lock, continuous_monitoring, device_rotation)
- `strings.json`, `translations/en.json`, `translations/it.json`: rimossi key_tone, display, off_timer

## Cosa resta da validare

1. `sync_oscillation` (2,11): testare "oscillazione sincronizzata" dall'app per trovare il valore "on" in fw1043
2. `continuous_monitoring` (2,10): testare toggle da app per confermare write values
3. Off_timer: se l'utente in futuro vuole riaggiungerlo, fare scan mirato dopo aver impostato un timer dall'app
4. Proprietà sconosciute (2,9), (2,13)–(2,20): non mappate, non esposte
