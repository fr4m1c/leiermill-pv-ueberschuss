# LEIERMILL – PV-Überschuss für Wärmepumpen

> **Experimentelle Vorabversion.** Die Paketvorlage wurde simuliert. An einer echten Wärmepumpe wurde die Heizungsrückstellung mit einer lokal angepassten Fassung geprüft. Der vollständige Betrieb bei PV-Überschuss steht noch aus. Das Paket kann Heizungs- und Warmwassersollwerte ändern. Für einen ersten Praxistest die Automatik nur unter Aufsicht freigeben, die Warmwasserfreigabe ausgeschaltet lassen und die Rückstellung der Sollwerte am Gerät kontrollieren.

LEIERMILL ist ein Home-Assistant-YAML-Paket für die Kombination aus E3/DC und ViCare. Es liest PV-Leistung, Netzleistung, Batterieleistung und Ladezustand. Bei anhaltender Einspeisung und nahezu voller Batterie hebt es die Heiz- und optional die Warmwassersolltemperatur stufenweise an. Bei Netzbezug, Batterieentladung oder Abschaltung stellt es zuvor gespeicherte Werte wieder her.

## Status

Das [Praxistestprotokoll](Praxistest.md) dokumentiert den Ablauf 17 → 18 → 17 °C und verlinkt die Dashboard-Karte sowie das Testskript. Am Gerät stehen die reguläre PV-Anhebung, das Verhalten bei Zeitprogrammwechseln und die Heizstabfreigabe noch zur Prüfung an. Die Beispieldatei enthält Platzhalter für alle anlagenspezifischen Entitäten.

## Simulation ausführen

```sh
python -m pip install Jinja2 PyYAML
python gesamttest.py
```

Die Simulation lädt die YAML, modelliert Sensoren, Aktionen und verzögerte Rückmeldungen und erzeugt ein Markdown- und ein JSON-Protokoll.

## Für eine Testinstallation vorbereiten

1. Alle Entitäten mit `beispiel_e3dc_` und `beispiel_vicare_` in der YAML durch die eigenen Entitäten ersetzen. Jede Zuordnung zuerst in Home Assistant prüfen.
2. Die E3/DC-Sensoren müssen Watt bzw. Prozent liefern. Das Paket erwartet negative Netzleistung bei Einspeisung und negative Batterieleistung bei Entladung.
3. Die YAML als Home-Assistant-Paket einbinden und die Konfiguration prüfen. Für die Heizzeit wird die ViCare-Betriebsart `auto` mit dem aktiven Programm `normalHeating` erwartet.
4. Die Automatik für den ersten Test gezielt über `input_boolean.leiermill_pv_automatik` freigeben. Die Warmwasserfreigabe separat erst nach Prüfung des Geräteverhaltens aktivieren. Beim Abschalten über den Freigabeschalter die Wiederherstellung der vorherigen Sollwerte kontrollieren.

Bei einem Schreibtimeout schaltet das Paket die Freigabe aus. Solange die Übernahme eines Auftrags unklar ist, bleibt der Wiederherstellungsmerker erhalten. Erscheint die verspätete Anhebung, versucht das Paket, sie zurückzunehmen. Bleibt der Auftrag dauerhaft unbestätigt, die Geräteverbindung und ausstehende Aufträge prüfen. Erst nach bestätigter Klärung den Helfer `input_text.leiermill_pv_merker` manuell auf `{}` setzen und die Freigabe bei Bedarf erneut einschalten.


## Gewährleistung und Haftung

Die Software wird in ihrem aktuellen Zustand bereitgestellt. Soweit gesetzlich zulässig, werden Gewährleistung und Haftung ausgeschlossen. Für Schäden aus der Verletzung von Leben, Körper oder Gesundheit, bei Vorsatz oder grober Fahrlässigkeit sowie in sonstigen Fällen zwingender gesetzlicher Haftung gelten die gesetzlichen Vorschriften.

## Lizenz

[MIT](LICENSE)
