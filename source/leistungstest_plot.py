import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def zeige_leistungstest():  # Diese Funktion lädt die Daten, berechnet die Zonen und gibt
    # 1. Überschrift anzeigen und Daten laden
    st.header("Auswertung Leistungstest")
    df = pd.read_csv("data/activity.csv")

    # 2. Kennzahlen berechnen und ausgeben
    mittelwert_leistung = round(df["PowerOriginal"].mean(), 2)
    maximalwert_leistung = round(df["PowerOriginal"].max(), 2)
    
    #Auswertungen des Leistungstests werden hier ausgegeben
    st.write(f"Durchschnittliche Leistung: **{mittelwert_leistung} W**")
    st.write(f"Maximale Leistung: **{maximalwert_leistung} W**")

    # 3. Zonen berechnen
    hf_max = st.number_input("Deine maximale Herzfrequenz (HF max):", value=190, max_value=250, min_value=100)
    max_gemessen = df["HeartRate"].max()
    if hf_max < max_gemessen:
        st.error(f"Die eingegebene maximale Herzfrequenz ({hf_max}) ist niedriger als die gemessene maximale Herzfrequenz ({int(max_gemessen)}). Bitte erhöhe HF max.")

    zone_top = max(hf_max, max_gemessen)
    zone_grenzen = [0, 0.60 * hf_max, 0.70 * hf_max, 0.80 * hf_max, 0.90 * hf_max, zone_top]
    zone_namen = ["Zone 1 (<60%)", "Zone 2 (60-70%)", "Zone 3 (70-80%)", "Zone 4 (80-90%)", "Zone 5 (90-100% und mehr)"]

    df["Zone"] = pd.cut(df["HeartRate"], bins=zone_grenzen, labels=zone_namen, include_lowest=True)

    # Typische FTP-Verteilung: Z1 (<55%), Z2 (55-75%), Z3 (75-90%), Z4 (90-105%), Z5 (105-120%), Z6 (120-150%), Z7 (>150%)
    watt_max = df["PowerOriginal"].max()
    watt_grenzen = [
        0, 
        0.55 * watt_max, 
        0.75 * watt_max, 
        0.90 * watt_max, 
        1.05 * watt_max, 
        1.20 * watt_max, 
        1.50 * watt_max, 
        watt_max * 2.0
    ]
    return df, zone_grenzen, watt_grenzen

  
def leistungstest_data(df, zone_grenzen, watt_grenzen): # Diese Funktion zeigt die interaktiven Kurven und die Tabellen mit den Zonen-Auswertungen an
    st.subheader("Interaktiver Kurvenverlauf")

    hintergrund_auswahl = st.radio(
        "Hintergrund-Farbzonen auswählen:",
        options=["Keine", "Herzfrequenz-Zonen", "Leistungs-Zonen (Watt)",],
        horizontal=True
    )
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["PowerOriginal"],
            name="Leistung (W)",
            line=dict(color="blue")
        ),
        secondary_y=True
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df["HeartRate"],
            name="Herzfrequenz (bpm)",
            line=dict(color="red")
        ),
        secondary_y=False
    )
    
    #Hintergrundfarben an die Y-Achse koppeln
    Herzfrequenz_farben = [
        "rgba(0, 200, 0, 0.15)",    # Zone 1: Grün
        "rgba(255, 215, 0, 0.15)",  # Zone 2: Gelb
        "rgba(255, 140, 0, 0.15)",  # Zone 3: Orange
        "rgba(255, 69, 0, 0.15)",   # Zone 4: Hellrot
        "rgba(200, 0, 0, 0.15)"     # Zone 5: Dunkelrot
    ]
    watt_farben = [
        "rgba(241, 226, 237, 0.4)",  # Z1: Active Recovery (hellrosa)
        "rgba(220, 190, 210, 0.4)",  # Z2: Endurance (etwas dunkleres rosa)
        "rgba(203, 161, 191, 0.4)",  # Z3: Tempo
        "rgba(182, 127, 169, 0.4)",  # Z4: Threshold
        "rgba(160, 94, 146, 0.4)",   # Z5: VO2Max
        "rgba(139, 66, 125, 0.4)",   # Z6: Anaerobic (dunkellila)
        "rgba(105, 35, 95, 0.4)"     # Z7: Neuromuscular (tiefes, dunkles Lila)     #wobei es Z6 und Z7 nie gibt da sie über der maximalen Leistung liegen würden
        ]
    hintergrund_shapes = []
    
    if hintergrund_auswahl != "Keine":
        if hintergrund_auswahl == "Herzfrequenz-Zonen":
            aktuelle_grenzen = zone_grenzen
            aktuelle_farben = Herzfrequenz_farben 
            anzahl_zonen = 5
            yref = "y"
        else:
            aktuelle_grenzen = watt_grenzen
            aktuelle_farben = watt_farben
            anzahl_zonen = 7
            yref = "y2"
            
    
        for i in range(anzahl_zonen):
            hintergrund_shapes.append(
                dict(
                    type="rect",
                    xref="paper",
                    yref=yref,
                    x0=0,
                    x1=1,
                    y0=aktuelle_grenzen[i],
                    y1=aktuelle_grenzen[i+1],
                    fillcolor=aktuelle_farben[i],
                    line=dict(width=0),
                    layer="below"
                )
            )

    watt_max = df["PowerOriginal"].max()

    fig.update_layout(
        shapes=hintergrund_shapes,
        height=650,
        yaxis=dict(title="Herzfrequenz (bpm)"),
        yaxis2=dict(title="Leistung (W)", side="right", overlaying="y", matches="y")
    )

    fig.update_yaxes(range=[0, 450], secondary_y=False)
    fig.update_yaxes(secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

  
    # 4. Tabellen erstellen und direkt ausgeben
    zeit_pro_zone = df.groupby("Zone").size().rename("verbrachte Zeit in jeweiliger Zone")
    
    leistung_pro_zone = df.groupby("Zone")["PowerOriginal"].mean().round(2).rename("erbrachte Leistung in jeweiliger Zone")

    st.subheader("Zonen-Analyse")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Zeit pro Zone (Sekunden):**")
        st.dataframe(zeit_pro_zone)
    with col2:
        st.write("**Ø Leistung pro Zone:**")
        st.dataframe(leistung_pro_zone)


if __name__ == "__main__":      # Hiermit wird die Hauptfunktion definiert, die beim Starten der App ausgeführt wird. Alle Funktionen, die nicht in einer Funktion definiert sind, werden ebenfalls ausgeführt.
    df, zone_grenzen, watt_grenzen = zeige_leistungstest()
    leistungstest_data(df, zone_grenzen, watt_grenzen)
