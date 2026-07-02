import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from source.config import ACTIVITY_FILE
from source.logging_config import get_logger

logger = get_logger(__name__)


def zeige_leistungstest():
    """Load activity data and calculate zone thresholds for heart rate and power.
    
    Displays a performance test header, calculates average and maximum power values,
    prompts the user for maximum heart rate, and computes training zones.
    
    Returns:
        Tuple of (DataFrame with activity data, zone boundaries for HR, zone boundaries for power).
    """
    st.header("Auswertung Leistungstest")
    logger.debug("Loading activity file %s", ACTIVITY_FILE)
    df = pd.read_csv(ACTIVITY_FILE)

    mittelwert_leistung = round(df["PowerOriginal"].mean(), 2)
    maximalwert_leistung = round(df["PowerOriginal"].max(), 2)
    
    st.write(f"Durchschnittliche Leistung: **{mittelwert_leistung} W**")
    st.write(f"Maximale Leistung: **{maximalwert_leistung} W**")
    hf_max = st.number_input("Deine maximale Herzfrequenz (HF max):", value=190, max_value=250, min_value=100)
    max_gemessen = df["HeartRate"].max()
    if hf_max < max_gemessen:
        st.error(f"Die eingegebene maximale Herzfrequenz ({hf_max}) ist niedriger als die gemessene maximale Herzfrequenz ({int(max_gemessen)}). Bitte erhöhe HF max.")

    zone_top = max(hf_max, max_gemessen)
    zone_grenzen = [0, 0.60 * hf_max, 0.70 * hf_max, 0.80 * hf_max, 0.90 * hf_max, zone_top]
    zone_namen = ["Zone 1 (<60%)", "Zone 2 (60-70%)", "Zone 3 (70-80%)", "Zone 4 (80-90%)", "Zone 5 (90-100% und mehr)"]

    df["Zone"] = pd.cut(df["HeartRate"], bins=zone_grenzen, labels=zone_namen, include_lowest=True)

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

  
def leistungstest_data(df, zone_grenzen, watt_grenzen):
    """Render an interactive dual-axis chart with zone shading and detailed analytics.
    
    Creates a Plotly figure with heart rate and power data, applies zone-based background
    coloring, and displays zone-specific statistics in a summary table.
    
    Args:
        df: DataFrame containing 'HeartRate', 'PowerOriginal', and 'Zone' columns.
        zone_grenzen: List of heart rate zone boundaries for background shading.
        watt_grenzen: List of power zone boundaries for background shading.
    """
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
        "rgba(241, 226, 237, 0.4)",  # Z1: Active Recovery
        "rgba(220, 190, 210, 0.4)",  # Z2: Endurance
        "rgba(203, 161, 191, 0.4)",  # Z3: Tempo
        "rgba(182, 127, 169, 0.4)",  # Z4: Threshold
        "rgba(160, 94, 146, 0.4)",   # Z5: VO2Max
        "rgba(139, 66, 125, 0.4)",   # Z6: Anaerobic
        "rgba(105, 35, 95, 0.4)"     # Z7: Neuromuscular
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

    st.plotly_chart(fig, key="performance_test_chart")

    zeit_pro_zone = df.groupby("Zone").size().rename("verbrachte Zeit in jeweiliger Zone")
    
    leistung_pro_zone = df.groupby("Zone")["PowerOriginal"].mean().round(2).rename("erbrachte Leistung in jeweiliger Zone")

    st.subheader("Zonen-Analyse")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Zeit pro Zone (Sekunden):**")
        st.dataframe(zeit_pro_zone)
    with col2:
        st.write("**Durchschnittliche Leistung pro Zone:**")
        st.dataframe(leistung_pro_zone)
