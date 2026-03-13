# Anforderungsabdeckung

## Funktional

- **F1/F2**: Koordinateneingabe und Validierung im Frontend und Backend
- **F3-F7**: Radius, Anzahl, Zeitraum und Stationsauswahl implementiert
- **F8/F9**: Jahres- und Jahreszeiten-Mittelwerte aus Tagesdaten, Datenlücken zulässig
- **F10/F11**: grafische und tabellarische Anzeige
- **F12**: Verarbeitung von `ghcnd-stations.txt`, `ghcnd-inventory.txt`, `by_station`
- **F13**: Logging für Import, Suche und Berechnungsstart

## Nicht-funktional

- **NF1/NF7**: Aggregation über Monatsmittel, meteorologische Jahreszeiten
- **NF2**: DE/EN-Umschaltung
- **NF3/NF4**: Caching und leichte Architektur; Zielwerte sind für reale Zielumgebungen zu prüfen
- **NF5**: Diagramm und Tabelle stammen aus derselben Datenbasis
- **NF6**: modularer Aufbau
- **NF8/NF9/NF10/NF11**: Client-Server, Docker, Windows-tauglich, Browsernutzung
- **NF12/NF14**: automatisierte Tests; externe Quellen sind austauschbar und abstrahiert
- **NF13**: barrierearmes, schlankes Frontend; Lighthouse-Prüfung ist als Auslieferungstest vorgesehen
