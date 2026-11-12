# LEIERMILL – Simulationsprotokoll

Lokale Ausführung der YAML-Templates und Aktionen mit modellierter HA-Laufzeit und virtueller Zeit. Keine Netzwerkverbindung, keine Gerätezugriffe. Nicht gleichzusetzen mit einem Test der echten HA-Laufzeit oder Viessmann-API.

Quelle: `pv_waermepumpe.yaml`
SHA256: `45032893f2e923eb89ca24f6b712c5b25aecae71483b5593f0f3f24b96679916`

| Prüffall | Ergebnis |
|---|---|
| 98 % / 10 min Freigabe; 20 °C → WW 55 °C → 22 °C → Ausgangswerte | BESTANDEN |
| Batterie zuerst; Startgrenze 98 % | BESTANDEN |
| Eigenverbrauch der WP beendet Anhebung nicht; ohne Reserve keine nächste Stufe | BESTANDEN |
| Kurze Wolke bleibt toleriert; Zusatzverbrauch ab 3 min nimmt Anhebung zurück | BESTANDEN |
| Batterieentladung über 700 W für 3 min | BESTANDEN |
| SoC unter 95 % für 5 min | BESTANDEN |
| Pause und neue Startprüfung jeweils 10 min | BESTANDEN |
| Manuelle 21 °C bleiben erhalten; eigene WW-Anhebung wird zurückgesetzt | BESTANDEN |
| Wechsel in reduzierte Zeitphase | BESTANDEN |
| Neustart mit gespeichertem Wiederherstellungsjournal | BESTANDEN |
| Ungültiger E3/DC-Sensor während Anhebung | BESTANDEN |
| E3/DC-Messwert älter als 180 Sekunden | BESTANDEN |
| Falsche Leistungseinheit verhindert Freigabe | BESTANDEN |
| Ohne WW-Freigabe keine WW-Anhebung | BESTANDEN |
| 30 Sekunden verzögerte Viessmann-Rückmeldung | BESTANDEN |
| Fehlgeschlagene Sollwertanhebung deaktiviert Automatik | BESTANDEN |
| Fehlgeschlagene Rückstellung behält Journal; Wiederholung stellt zurück | BESTANDEN |
| Gespeicherte Ausgangswerte 19/50 statt fest verdrahteter 18/48 | BESTANDEN |
| Rückstellbestätigung erst nach 70 Sekunden; Journal bleibt bis Bestätigung | BESTANDEN |
| Anhebung wird erst 90 Sekunden nach Auftrag übernommen, nach Schreibtimeout | BESTANDEN |

## Grenzen

- Installierter HA-Dateistand (nur gespeicherte Version vorhanden)
- Ampel und Forecast (deren aktueller YAML-Dateistand liegt nicht vor)
- Reale Zeitplanwirkung, Heizstabfreigabe und physische Wärmeabgabe
- Späte API-Schreibaufträge nach Timeout, parallele HA-Ereignisse und Neustart mitten in laufendem API-Auftrag

## Wiederholen

`python -m pip install PyYAML Jinja2`

`python gesamttest.py`

Die YAML bleibt unverändert. Nicht in Home Assistant als Paket installieren. Das JSON-Protokoll enthält jeden simulierten Schreibaufruf mit virtueller Zeit.
Die Simulation benötigt keine Verbindung zu Home Assistant.
