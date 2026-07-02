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
from source.config import DATA_ROOT, PICTURE_ROOT, EKG_ROOT, ACTIVITY_FILE
from source.logging_config import setup_logging, get_logger, tail_log_lines

# Configure logging early so modules can write logs during import/runtime
setup_logging()
logger = get_logger(__name__)

logger.info("Starting Streamlit app")
logger.debug("DATA_ROOT=%s EKG_ROOT=%s ACTIVITY_FILE=%s", DATA_ROOT, EKG_ROOT, ACTIVITY_FILE)

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
    """Load all persons from the database with Streamlit caching.
    
    Returns:
        Cached list of Person instances from person_db.json.
    """
    persons = load_person_data()
    logger.info("Loaded %d persons from database", len(persons))
    return persons


def clear_person_cache() -> None:
    """Clear the cached person list so the UI can reload updated JSON data."""
    get_persons.clear()


def find_person_by_id(persons: list[Person], person_id: int | None) -> Person | None:
    """Return a person by numeric ID or None if not found."""
    if person_id is None:
        return None
    for person in persons:
        if person.id == person_id:
            return person
    return None


def authenticate_person(persons: list[Person], identifier: str, password: str) -> Person | None:
    """Authenticate a person using username, email or full name and password."""
    person = Person.find_by_identifier(persons, identifier)
    if person is not None and person.verify_password(password):
        logger.info("Person logged in: %s", identifier)
        return person
    logger.warning("Login failed for %s", identifier)
    return None


def get_logged_in_person(persons: list[Person]) -> Person | None:
    """Return the currently logged-in person from session state."""
    return find_person_by_id(persons, st.session_state.get("logged_in_person_id"))


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
        st.write(f"**Benutzername:** {person.username or 'nicht gesetzt'}")
        st.write(f"**E-Mail:** {person.email or 'nicht gesetzt'}")
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
    """Render the power curve analysis from activity data.
    
    Loads activity CSV, calculates the power curve, and displays it with
    a logarithmic time scale.
    """
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


with st.sidebar.expander("App-Logs", expanded=False):
    if st.checkbox("Show app log (tail)", value=False, key="show_log"):
        lines = tail_log_lines(400)
        if not lines:
            st.info("No log file found yet. Start the app and reproduce some actions.")
        else:
            st.code("\n".join(lines), language="text")


def save_person_changes(persons: list[Person]) -> None:
    """Save modified persons list to database and refresh the UI.
    
    Args:
        persons: List of Person instances to save to person_db.json.
    """
    Person.save_all(persons)
    clear_person_cache()
    st.success("Änderungen wurden gespeichert.")
    st.experimental_rerun()


def main() -> None:
    """Main Streamlit application entry point.
    
    Manages the overall UI layout with authentication, profile display,
    EKG analysis, and editing for the logged-in person.
    """
    if "logged_in_person_id" not in st.session_state:
        st.session_state.logged_in_person_id = None

    persons = get_persons()
    if st.session_state.logged_in_person_id is None:
        st.header("Anmelden oder neuen Account erstellen")
        auth_tabs = st.tabs(["Anmelden", "Registrieren"])

        with auth_tabs[0]:
            if not persons:
                st.warning("Noch keine Personen vorhanden. Bitte erst einen neuen Account registrieren.")
            else:
                identifier = st.text_input("Benutzername, E-Mail oder Name", key="login_identifier")
                password = st.text_input("Passwort", type="password", key="login_password")
                if st.button("Anmelden"):
                    person = authenticate_person(persons, identifier.strip(), password)
                    if person is not None:
                        st.session_state.logged_in_person_id = person.id
                        st.success(f"Erfolgreich angemeldet als {person.display_name}")
                        st.experimental_rerun()
                    else:
                        st.error("Anmeldung fehlgeschlagen. Bitte prüfe Benutzername/E-Mail/Name und Passwort.")

        with auth_tabs[1]:
            with st.form("register_form"):
                st.subheader("Neuen Account anlegen")
                firstname = st.text_input("Vorname", value="", key="register_firstname")
                lastname = st.text_input("Nachname", value="", key="register_lastname")
                username = st.text_input("Benutzername", value="", key="register_username")
                email = st.text_input("E-Mail", value="", key="register_email")
                birth_year = st.number_input("Geburtsjahr", min_value=1900, max_value=date.today().year, value=2000, key="register_birth_year")
                gender = st.selectbox("Geschlecht", options=["unbekannt", "male", "female", "other"], index=0, key="register_gender")
                password = st.text_input("Passwort", type="password", key="register_password")
                password_confirm = st.text_input("Passwort bestätigen", type="password", key="register_password_confirm")
                picture_file = st.file_uploader("Bild hochladen", type=["png", "jpg", "jpeg"], key="register_picture")
                add_test = st.checkbox("Ersten EKG-Test hinzufügen", key="register_new_test_checkbox")
                test_date = st.text_input("Testdatum (z. B. 15.04.2024)", value="", key="register_test_date")
                test_file = st.file_uploader("EKG-Datei hochladen", type=["txt"], key="register_test_file")
                register_submit = st.form_submit_button("Account erstellen")

                if register_submit:
                    username_value = username.strip()
                    email_value = email.strip().lower()
                    if not firstname or not lastname or not password or not username_value:
                        st.error("Vorname, Nachname, Benutzername und Passwort sind erforderlich.")
                    elif password != password_confirm:
                        st.error("Die Passwörter stimmen nicht überein.")
                    elif any(person.username.strip().lower() == username_value for person in persons if person.username):
                        st.error("Der Benutzername ist bereits vergeben.")
                    elif email_value and any(person.email.strip().lower() == email_value for person in persons if person.email):
                        st.error("Diese E-Mail ist bereits registriert.")
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
                            username=username_value,
                            email=email_value,
                        )
                        new_person.set_password(password)
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
                        st.session_state.logged_in_person_id = new_person.id
                        st.success(f"Account erstellt und angemeldet als {new_person.display_name}")
                        st.experimental_rerun()
        return

    current_person = get_logged_in_person(persons)
    if current_person is None:
        st.error("Der angemeldete Benutzer konnte nicht gefunden werden. Bitte melde dich erneut an.")
        st.session_state.logged_in_person_id = None
        st.experimental_rerun()
        return

    if st.sidebar.button("Abmelden"):
        st.session_state.logged_in_person_id = None
        st.success("Du wurdest abgemeldet.")
        st.experimental_rerun()
        return

    st.success(f"Eingeloggt als {current_person.display_name}")

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
        st.header("Meine Daten bearbeiten")
        st.write("Nur dein eigener Account und deine eigenen EKG-Tests sind hier sichtbar.")

        with st.form("edit_person_form"):
            st.subheader("Mein Profil bearbeiten")
            firstname = st.text_input("Vorname", value=current_person.firstname, key="edit_firstname")
            lastname = st.text_input("Nachname", value=current_person.lastname, key="edit_lastname")
            username = st.text_input("Benutzername", value=current_person.username, key="edit_username")
            email = st.text_input("E-Mail", value=current_person.email, key="edit_email")
            birth_year = st.number_input(
                "Geburtsjahr",
                min_value=1900,
                max_value=date.today().year,
                value=current_person.date_of_birth,
                key="edit_birth_year",
            )
            gender = st.selectbox(
                "Geschlecht",
                options=["unbekannt", "male", "female", "other"],
                index=["unbekannt", "male", "female", "other"].index(current_person.gender)
                if current_person.gender in ["unbekannt", "male", "female", "other"]
                else 0,
                key="edit_gender",
            )
            picture_file = st.file_uploader("Bild ersetzen", type=["png", "jpg", "jpeg"], key="edit_person_picture")
            add_test = st.checkbox("Neuen EKG-Test hinzufügen", key="edit_test_checkbox")
            edit_test_date = st.text_input("Testdatum (z. B. 15.04.2024)", value=date.today().strftime("%d.%m.%Y"), key="edit_test_date")
            edit_test_file = st.file_uploader("EKG-Datei hochladen", type=["txt"], key="edit_test_file")
            edit_submit = st.form_submit_button("Änderungen speichern")

            if edit_submit:
                username_value = username.strip()
                email_value = email.strip().lower()
                if not username_value:
                    st.error("Benutzername darf nicht leer sein.")
                elif any(
                    person.username.strip().lower() == username_value
                    and person.id != current_person.id
                    for person in persons
                    if person.username
                ):
                    st.error("Der Benutzername ist bereits vergeben.")
                elif email_value and any(
                    person.email.strip().lower() == email_value
                    and person.id != current_person.id
                    for person in persons
                    if person.email
                ):
                    st.error("Diese E-Mail ist bereits vergeben.")
                else:
                    current_person.firstname = firstname
                    current_person.lastname = lastname
                    current_person.username = username_value
                    current_person.email = email_value
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

        with st.form("change_password_form"):
            st.subheader("Passwort ändern")
            old_password = st.text_input("Aktuelles Passwort", type="password", key="old_password")
            new_password = st.text_input("Neues Passwort", type="password", key="new_password")
            confirm_password = st.text_input("Neues Passwort bestätigen", type="password", key="confirm_password")
            change_password_submit = st.form_submit_button("Passwort aktualisieren")

            if change_password_submit:
                if not old_password or not new_password or not confirm_password:
                    st.error("Bitte fülle alle Passwortfelder aus.")
                elif new_password != confirm_password:
                    st.error("Die neuen Passwörter stimmen nicht überein.")
                elif not current_person.verify_password(old_password):
                    st.error("Das aktuelle Passwort ist falsch.")
                else:
                    current_person.set_password(new_password)
                    save_person_changes(persons)
                    st.success("Passwort erfolgreich geändert.")

    st.write("---")
    st.caption("Die Änderungen werden in data/person_db.json gespeichert und können direkt in der App genutzt werden.")


if __name__ == "__main__":
    main()
