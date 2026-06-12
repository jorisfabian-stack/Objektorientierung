import streamlit as st
import sys
from pathlib import Path

# Pfade für die Importe konfigurieren
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "source"))

import read_data_1
from pandas_plot import zeige_leistungstest, leistungstest_data
from Leistungskurve import create_power_curve
import pandas as pd
import plotly.express as px

# Seiten-Konfiguration
st.set_page_config(layout="wide", page_title="EKG & Power Curve App")

# ========== EKG DASHBOARD ==========
st.write("# EKG APP")
st.write("## Versuchsperson auswählen")

# 1. Die echten JSON-Daten laden
daten = read_data_1.load_person_data()

# 2. Die Namensliste generieren
person_names = read_data_1.get_person_list(daten)

# 3. Auswahlbox mit den echten Namen befüllen
current_user = st.selectbox(
    'Versuchsperson',
    options=person_names,
    key="sbVersuchsperson"
)

st.write("Der Name ist:", current_user)

current_person_data = read_data_1.find_person_data_by_name(daten, current_user)

# Prüfen, ob die Person existiert und ob ein Bildpfad hinterlegt ist
col1, col2 = st.columns(2)

with col1:
    if current_person_data and "picture_path" in current_person_data:
        bild_pfad = current_person_data["picture_path"]
        st.image(bild_pfad, width=300)
    else:
        st.write("Kein Bild für diese Person gefunden.")

# Leistungstest-Auswertung anzeigen
with col2:
    df, zone_grenzen, watt_grenzen = zeige_leistungstest()

st.write("---")
leistungstest_data(df, zone_grenzen, watt_grenzen)

st.write("---")
st.write("# Power Curve Analyse")
st.write("## Deine Leistungskurve")
try:
    data_file = project_root / "data" / "activity.csv"
    if data_file.exists():
        df_activity = pd.read_csv(data_file)
        power_curve = create_power_curve(df_activity)

        with st.expander("Leistungskurven-Daten anzeigen", expanded=False):
            st.dataframe(power_curve.head(10))

        st.write("### Leistungskurven-Plot:")
        fig = px.line(
            power_curve,
            x="duration_s",
            y="power_w",
            markers=True,
            labels={"duration_s": "Dauer (s)", "power_w": "Leistung (W)"},
            title="Leistungskurve",
        )
        fig.update_xaxes(type="log")
        fig.update_traces(
            hovertemplate="Dauer: %{x:.2f}s<br>Leistung: %{y:.2f} W",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Datei nicht gefunden: {data_file}")
        st.write(f"Bitte stelle sicher, dass die Datei unter `{data_file}` vorhanden ist.")
except Exception as e:
    st.error(f"Fehler beim Laden der Daten: {str(e)}")

# Footer
st.write("---")
st.write("built by Milan and Joris :)")
