# Praxistest am 11. November 2026

Der Test wurde in einer Home-Assistant-Installation mit einer Viessmann Vitocal 250-A A19 und einer lokal angepassten Paketfassung durchgeführt.

| Prüfung | Beobachtung |
|---|---|
| Dashboard aufklappen | Der Schalter unter der Energiezentrale blendet die Freigabebedienung ein. |
| Einschaltbestätigung abbrechen | Die PV-Freigabe bleibt ausgeschaltet. |
| Einmalige Heizungsanhebung | Der Sollwert stieg von 17 auf 18 °C. |
| Rückstellung | Der Sollwert kehrte auf 17 °C zurück. Der Rückstellmerker war leer, das Rückstellskript beendet und die Regelungsautomation weiterhin eingeschaltet. Die PV-Freigabe blieb aus. |

Der Start mit echtem PV-Überschuss, die regulären Heizstufen, die Warmwasseranhebung und das Verhalten bei Verbindungsausfall stehen in der Praxis noch zur Prüfung an. Der Überschusstest wurde wegen fehlender Solarerzeugung verschoben.

## YAML-Beispiele

- [Dashboard-Karte](beispiele/dashboard-pv-freigabe.yaml) unter dem Energiefluss platzieren. Dafür einen UI-Schalter mit der Entitäts-ID `input_boolean.leiermill_pv_steuerung_anzeigen` anlegen. Dieser steuert nur die Sichtbarkeit. Das Einschalten der PV-Freigabe fragt nach Bestätigung.
- [Rückstellungstest](beispiele/rueckstellung-testen.yaml) im YAML-Editor eines separaten Skripts verwenden. Beide Vorkommen der Beispiel-Heizentität und bei Bedarf die Automations-ID an die Installation anpassen. Der Test setzt einen Ausgangswert von 17 °C, einen leeren Merker, eine ausgeschaltete PV-Freigabe und eine laufende Regelungsautomation mit Unterstützung für den Pending-Merker voraus. Erst bei bewusster Freigabe wird der echte Sollwert einmalig geändert. Bei fehlender Rückmeldung den Merker stehen lassen und die Ursache prüfen.

Die Beispiele wurden für die Veröffentlichung von den anlagenspezifischen Entitäts-IDs getrennt. Die öffentliche Paketvorlage und die lokal geprüfte Fassung sind unterschiedliche Dateistände.
