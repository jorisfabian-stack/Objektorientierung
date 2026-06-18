# EKG & Power Curve App

Von Milan und Joris

## Beschreibung

Diese Anwendung dient zur Visualisierung und Analyse von EKG- und Leistungsdaten.

Die App bietet folgende Funktionen:

* Auswahl einer Versuchsperson aus einer Datenbank
* Anzeige der zugehörigen Personendaten und Bilder
* Auswertung eines Leistungstests
* Berechnung einer Leistungskurve (Power Curve)
* Interaktive Darstellung der Leistungsdaten mit Plotly und Streamlit

Die Daten werden aus den Dateien im Verzeichnis `data/` geladen.

---

## Voraussetzungen

Für die Ausführung wird Python 3.11 oder neuer empfohlen.

Die benötigten Bibliotheken werden über PDM verwaltet.

---

## Installation

Repository klonen und in das Projektverzeichnis wechseln:

```bash
git clone <repository-url>
cd Objektorientierung-main
```

PDM installieren:

```bash
pip install pdm
```

Abhängigkeiten installieren:

```bash
pdm install
```

---

## Anwendung starten

### Streamlit-Webanwendung

```bash
pdm run streamlit run main.py
```

Anschließend öffnet sich die Anwendung im Browser.


## Projektstruktur

```text
.
├── main.py                # Streamlit-Hauptanwendung
├── data/
│   ├── activity.csv
│   ├── person_db.json
│   ├── ekg_data/
│   └── pictures/
├── source/
│   ├── ekgdata.py
│   ├── leistungskurve.py
│   ├── leistungstest_plot.py
│   └── person.py
├── pyproject.toml
└── pdm.lock
```

---

## Verwendete Bibliotheken

* streamlit
* pandas
* numpy
* matplotlib
* plotly
* pillow
