# Wetterstation Explorer – vollständige Abgabeversion

Dieses Projekt ist eine vollständige, lauffähige Webanwendung zur Suche nach GHCN-Wetterstationen,
zur Auswertung täglicher TMIN/TMAX-Messwerte und zur grafischen/tabellarischen Darstellung
von Jahres- und Jahreszeiten-Mittelwerten.

## Start mit Docker / Podman

```bash
podman compose up --build
```

oder

```bash
docker compose up --build
```

Danach:

- Frontend: http://localhost:3000
- Backend / API: http://localhost:8000
- API-Dokumentation: http://localhost:8000/docs

## Datenquellen

Standardmäßig nutzt die Anwendung die im Repository enthaltenen GHCN-Beispieldaten im NOAA-Format:

- `ghcnd-stations.txt`
- `ghcnd-inventory.txt`
- `by_station/*.csv`

Optional kann das Backend zur Laufzeit auch mit entfernten Datenquellen betrieben werden:

- NOAA `by_station` CSV
- AWS/NODD Jahres-CSV

Konfiguration erfolgt über Umgebungsvariablen in `docker-compose.yml`.

## Projektstruktur

- `backend/` FastAPI-Server, Parser, Services, Tests
- `frontend/` statisches, barrierearmes Browser-Frontend (DE/EN)
- `docs/` Architektur, Testkonzept, Anforderungsabdeckung

## Tests

Lokal im Backend-Verzeichnis:

```bash
pytest
```
