# docs/

Documentazione tecnica derivata dal lavoro di sviluppo (non spec di partenza, che vive in `specs/`).

## File previsti (man mano che il progetto procede)
- `property_map.md` — tabella siid/piid/aiid validata empiricamente (output Fase 2).
- `discovery-procedure.md` — procedura step-by-step snapshot → diff → conferma proprietà.
- `troubleshooting.md` — problemi comuni (offline, cannot_connect, auth scaduta, deep standby).
- `architecture.md` — diagramma flussi coordinator/client/entità, se necessario.

## Regole
- Documentare solo cose **già verificate**. Per ipotesi/candidati usare `research/`.
- Se un device-specific value finisce in docs, sostituirlo con placeholder (`<DID>`, `<MAC>`) — repo pubblico.
