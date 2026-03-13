# Testkonzept

## Unit-Tests

Abgedeckt werden:

- Koordinatenvalidierung
- Haversine-Distanz
- Stationsfilterung
- Berechnung mit Datenlücken
- API-Endpunkte

## Systemtests

Drei Standorte sind als API-Systemtests abgebildet:

1. Nürnberg
2. Stuttgart
3. Hamburg

Für jeden Standort wird geprüft, dass die nächstgelegene Station korrekt ermittelt wird.

## Nicht-funktionale Absicherung

- Automatisierte Tests via `pytest`
- CI-Workflow für Backend-Tests
- semantisches, keyboard-freundliches Frontend
- Proxy-Konfiguration für einfache Browser-Nutzung
