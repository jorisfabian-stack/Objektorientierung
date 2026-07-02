import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import date
from uuid import uuid4

from source.person import Person, find_person_data_by_name, get_person_list, load_person_data
from source.ekgdata import Ekgdata
from source.leistungskurve import create_power_curve

DATA_ROOT = Path(__file__).resolve().parent / "data"
PICTURE_ROOT = DATA_ROOT / "pictures"
EKG_ROOT = DATA_ROOT / "ekg_data"
ACTIVITY_FILE = DATA_ROOT / "activity.csv"

st.set_page_config(
    page_title="EKG & Power Curve App",
    page_icon="💓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp > main {
        max-width: 1800px;
        margin: auto;
        padding: 1rem 2rem;
    }
    .title-style {
        font-size: 3.5rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .subtitle-style {
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .metric-card .stMetric {
        border-radius: 16px;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("EKG & Power Curve Dashboard")
st.caption("Wähle eine Person, analysiere verfügbare Tests und erweitere die Datenbank direkt im Browser.")


@st.cache_data(show_spinner=False)
def get_persons() -> list[Person]:
    return load_person_data()


def clear_person_cache() -> None:
    """Clear the cached person list so the UI can reload updated JSON data."""
    get_persons.clear()


def count_file_lines(path: Path) -> int:
    """Count non-empty lines in a file to estimate the number of raw samples."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        return sum(1 for _ in file)


def format_test_name(test: dict[str, str]) -> str:
    """Create a human-readable label for an EKG test entry."""
    date_label = test.get("date", "unbekannt")
    file_name = Path(test.get("result_link", "")).name
    return f"{date_label} – {file_name}"


def resolve_path(path_value: str) -> Path:
    """Resolve a relative or absolute path to the current working directory."""
    path = Path(path_value)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def save_uploaded_file(uploaded_file, target_dir: Path, prefix: str) -> str:
    """Save an uploaded file into the target directory and return a relative path."""
    if uploaded_file is None:
        return ""
    target_dir.mkdir(parents=True, exist_ok=True)
    original_name = Path(uploaded_file.name).name
    target_file = target_dir / f"{prefix}_{uuid4().hex[:8]}_{original_name}"
    with target_file.open("wb") as out_file:
        out_file.write(uploaded_file.getbuffer())
    return str(target_file.relative_to(Path.cwd()).as_posix())


def build_ekg_dataframe(data: Ekgdata) -> pd.DataFrame:
    """Build a small DataFrame from parsed EKG data for plotting and selection."""
    return pd.DataFrame(
        {
            "sample": list(range(1, data.sample_count() + 1)),
            "herzfrequenz": data.heart_rate,
            "leistung": data.power_original,
        }
    )


def render_person_card(person: Person) -> None:
    """Render the selected person profile including picture, age, and test count."""
    image_source = resolve_path(person.picture_path)
    left, right = st.columns([1, 2], gap="large")
    with left:
        if image_source.exists():
            st.image(str(image_source), width=320, caption=person.display_name)
        else:
            st.info("Kein Bild verfügbar")
    with right:
        st.markdown(f"### {person.display_name}")
        st.write(f"**Geburtsjahr:** {person.birth_year}")
        st.write(f"**Alter:** {person.age} Jahre")
        st.write(f"**Geschlecht:** {person.gender or 'unbekannt'}")
        st.write(f"**Verfügbare EKG-Tests:** {len(person.ekg_tests)}")
        if person.ekg_tests:
            st.write(
                "Wähle einen Test aus, um Testdatum, Dauer und Herzfrequenzanalyse anzuzeigen."
            )


def render_ekg_analysis(person: Person) -> None:
    """Render the EKG analysis controls and plots for the selected person."""
    st.subheader("EKG Testauswahl")
    tests = person.get_ekg_tests()
    if not tests:
        st.warning("Für diese Person sind noch keine EKG-Tests gespeichert.")
        return

    test_labels = [format_test_name(test) for test in tests]
    selected_label = st.selectbox("Verfügbarer Test", options=test_labels, index=0)
    selected_test = tests[test_labels.index(selected_label)]

    test_file_path = resolve_path(selected_test.get("result_link", ""))
    if not test_file_path.exists():
        st.error(f"EKG-Datei nicht gefunden: {test_file_path}")
        return

    sample_count = count_file_lines(test_file_path)
    downsample = max(1, sample_count // 1800)
    ekg_data = Ekgdata.cached_from_file(str(test_file_path), downsample_factor=downsample)
    summary = ekg_data.summary()

    st.markdown("#### Testdetails")
    st.write(f"**Testdatum:** {selected_test.get('date', 'unbekannt')}")
    st.write(f"**Dateipfad:** {selected_test.get('result_link', '')}")
    st.write(f"**Länge der Zeitreihe:** {summary['duration_minutes']} Minuten ({summary['samples']} Messwerte)")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Dauer", f"{summary['duration_minutes']} min")
    metric_columns[1].metric("Ø Herzfrequenz", f"{summary['heart_rate_avg']:.1f} bpm")
    metric_columns[2].metric("Max. Herzfrequenz", f"{summary['heart_rate_max']:.1f} bpm")
    metric_columns[3].metric("Messwerte", f"{summary['samples']}")

    data_frame = build_ekg_dataframe(ekg_data)
    time_range = st.slider(
        "Zeitraum für Plot auswählen",
        min_value=1,
        max_value=data_frame["sample"].iloc[-1],
        value=(1, min(600, data_frame["sample"].iloc[-1])),
        step=1,
    )

    selection = data_frame.iloc[time_range[0] - 1 : time_range[1]]
    with st.expander("Messwerte der ausgewählten Auswahl anzeigen", expanded=False):
        st.dataframe(selection.reset_index(drop=True))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=selection["sample"],
            y=selection["herzfrequenz"],
            name="Herzfrequenz",
            line=dict(color="#d62728", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=selection["sample"],
            y=selection["leistung"],
            name="Leistung",
            line=dict(color="#1f77b4", width=2),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title_text=f"EKG-Test {selected_test.get('date', '')}",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01),
        margin=dict(t=80, b=30, l=0, r=0),
    )
    fig.update_xaxes(title_text="Messpunkt")
    fig.update_yaxes(title_text="Herzfrequenz (bpm)", secondary_y=False)
    fig.update_yaxes(title_text="Leistung", secondary_y=True)
    st.plotly_chart(fig, key="ekg_chart")


def render_power_curve() -> None:
    st.subheader("Leistungskurve")
    if not ACTIVITY_FILE.exists():
        st.error(f"Aktivitätsdatei nicht gefunden: {ACTIVITY_FILE}")
        return

    df_activity = pd.read_csv(ACTIVITY_FILE)
    if "PowerOriginal" not in df_activity.columns or "Duration" not in df_activity.columns:
        st.error("Aktivitätsdatei fehlt notwendige Spalten.")
        return

    power_curve = create_power_curve(df_activity)
    with st.expander("Leistungskurven-Daten anzeigen", expanded=False):
        st.dataframe(power_curve.head(20))

    fig = px.line(
        power_curve,
        x="duration_s",
        y="power_w",
        labels={"duration_s": "Dauer (s)", "power_w": "Leistung (W)"},
        title="Power Curve",
    )
    fig.update_xaxes(type="log")
    fig.update_traces(mode="lines+markers", hovertemplate="Dauer: %{x:.2f}s<br>Leistung: %{y:.2f} W")
    st.plotly_chart(fig, key="power_curve_chart")


def save_person_changes(persons: list[Person]) -> None:
    Person.save_all(persons)
    clear_person_cache()
    st.success("Änderungen wurden gespeichert.")
    st.experimental_rerun()


def main() -> None:
    persons = get_persons()
    if not persons:
        st.error("Keine Personendaten gefunden. Bitte prüfen Sie die Datei data/person_db.json.")
        return

    person_names = get_person_list(persons)
    selected_name = st.selectbox("Versuchsperson auswählen", options=person_names, index=0)
    current_person = find_person_data_by_name(persons, selected_name)

    if current_person is None:
        st.error("Die ausgewählte Person konnte nicht geladen werden.")
        return

    overview_tab, ekg_tab, manage_tab = st.tabs(["Personendaten", "EKG Analyse", "Verwaltung"])

    with overview_tab:
        st.header("Personenprofil")
        render_person_card(current_person)

    with ekg_tab:
        st.header("EKG Analyse")
        render_ekg_analysis(current_person)
        st.write("---")
        render_power_curve()

    with manage_tab:
        st.header("Datenbank verwalten")
        st.write("Füge eine neue Person hinzu oder bearbeite die ausgewählte Person.")

        action = st.radio("Aktion auswählen", ["Person bearbeiten", "Neue Person anlegen"], horizontal=True)

        if action == "Neue Person anlegen":
            with st.form("new_person_form"):
                st.subheader("Neue Person hinzufügen")
                firstname = st.text_input("Vorname", value="")
                lastname = st.text_input("Nachname", value="")
                birth_year = st.number_input("Geburtsjahr", min_value=1900, max_value=date.today().year, value=2000)
                gender = st.selectbox("Geschlecht", options=["unbekannt", "male", "female", "other"], index=0)
                picture_file = st.file_uploader("Bild hochladen", type=["png", "jpg", "jpeg"], key="new_person_picture")
                add_test = st.checkbox("Ersten EKG-Test hinzufügen", key="new_test_checkbox")
                test_date = st.text_input("Testdatum (z. B. 15.04.2024)", value="", key="new_test_date")
                test_file = st.file_uploader("EKG-Datei hochladen", type=["txt"], key="new_test_file")
                new_person_submit = st.form_submit_button("Person erstellen")

                if new_person_submit:
                    if not firstname or not lastname:
                        st.error("Vorname und Nachname sind erforderlich.")
                    else:
                        picture_path = ""
                        if picture_file is not None:
                            picture_path = save_uploaded_file(picture_file, PICTURE_ROOT, "picture")
                        new_person = Person(
                            id=Person.next_person_id(persons),
                            firstname=firstname,
                            lastname=lastname,
                            date_of_birth=birth_year,
                            picture_path=picture_path,
                            gender=gender,
                            ekg_tests=[],
                        )
                        if add_test and test_file is not None:
                            ekg_path = save_uploaded_file(test_file, EKG_ROOT, "ekg")
                            new_person.ekg_tests.append(
                                {
                                    "id": Person.next_test_id(persons),
                                    "date": test_date or date.today().strftime("%d.%m.%Y"),
                                    "result_link": ekg_path,
                                }
                            )
                        persons.append(new_person)
                        save_person_changes(persons)

        if action == "Person bearbeiten":
            with st.form("edit_person_form"):
                st.subheader("Ausgewählte Person bearbeiten")
                firstname = st.text_input("Vorname", value=current_person.firstname)
                lastname = st.text_input("Nachname", value=current_person.lastname)
                birth_year = st.number_input(
                    "Geburtsjahr",
                    min_value=1900,
                    max_value=date.today().year,
                    value=current_person.date_of_birth,
                )
                gender = st.selectbox(
                    "Geschlecht",
                    options=["unbekannt", "male", "female", "other"],
                    index=["unbekannt", "male", "female", "other"].index(current_person.gender)
                    if current_person.gender in ["unbekannt", "male", "female", "other"]
                    else 0,
                )
                picture_file = st.file_uploader("Bild ersetzen", type=["png", "jpg", "jpeg"], key="edit_person_picture")
                add_test = st.checkbox("Neuen EKG-Test hinzufügen", key="edit_test_checkbox")
                edit_test_date = st.text_input("Testdatum (z. B. 15.04.2024)", value=date.today().strftime("%d.%m.%Y"), key="edit_test_date")
                edit_test_file = st.file_uploader("EKG-Datei hochladen", type=["txt"], key="edit_test_file")
                edit_submit = st.form_submit_button("Änderungen speichern")

                if edit_submit:
                    current_person.firstname = firstname
                    current_person.lastname = lastname
                    current_person.date_of_birth = birth_year
                    current_person.gender = gender
                    if picture_file is not None:
                        current_person.picture_path = save_uploaded_file(
                            picture_file, PICTURE_ROOT, "picture"
                        )
                    if add_test and edit_test_file is not None:
                        ekg_path = save_uploaded_file(edit_test_file, EKG_ROOT, "ekg")
                        current_person.ekg_tests.append(
                            {
                                "id": Person.next_test_id(persons),
                                "date": edit_test_date or date.today().strftime("%d.%m.%Y"),
                                "result_link": ekg_path,
                            }
                        )
                    save_person_changes(persons)

    st.write("---")
    st.caption("Die Änderungen werden in data/person_db.json gespeichert und können direkt in der App genutzt werden.")


if __name__ == "__main__":
    main()
