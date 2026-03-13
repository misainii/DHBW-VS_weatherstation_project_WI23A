# Architektur

## Überblick

Die Anwendung ist als Client-Server-System umgesetzt:

- **Frontend**: statische Webanwendung in HTML/CSS/JavaScript, ausgeliefert durch Nginx
- **Backend**: FastAPI-Anwendung für Stationssuche, Datenaggregation und Berechnungen
- **Daten**: GHCN-Dateien `ghcnd-stations.txt`, `ghcnd-inventory.txt`, `by_station/*.csv`

## Backend-Schichten

- `parsers.py`: Verarbeitung der NOAA/GHCN-Dateiformate
- `data_sources.py`: Datenzugriff für lokale Beispieldaten, NOAA by_station oder AWS-Jahresdateien
- `services.py`: Distanzberechnung, Filterung, Monats-/Jahreszeiten-Aggregation
- `main.py`: REST-API

## Frontend

- zweisprachige Benutzerführung (DE/EN)
- Suche nach Stationen über Koordinaten und Filter
- Auswahl der nächsten Stationen
- Visualisierung via SVG-Liniendiagramm
- tabellarische Darstellung derselben Kennwerte

## Containerisierung

- `docker-compose.yml` startet Frontend und Backend
- Frontend kommuniziert über `/api` mit dem Backend
