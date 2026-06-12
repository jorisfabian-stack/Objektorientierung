import json

def load_person_data(): #Diese Funktion lädt die Personendaten aus der JSON-Datei und gibt sie als Dictionary zurück
    """A Function that knows where the person database is and returns a dictionary with the persons"""
    file = open("data/person_db.json")
    person_data = json.load(file)
    file.close() 
    return person_data


def get_person_list(person_data):   #Diese Funktion nimmt das Personen-Dictionary und erstellt daraus eine Liste mit den Namen aller Personen
    """A Function that takes the persons-dictionary and returns a list of all person names"""
    list_of_names = []

    
    for eintrag in person_data:
        # bautString zusammen und hängt ihn an die Liste
        list_of_names.append(eintrag["lastname"] + ", " + eintrag["firstname"])
        
    return list_of_names


def find_person_data_by_name(person_data, suchstring):  #Diese Funktion sucht in dem Personen-Dictionary nach einem Eintrag, der zum Suchstring passt (z.B. "Huber, Julian") und gibt das dazugehörige Personen-Dictionary zurück
    """Sucht ein Personen-Dictionary anhand des Vorlesungs-Beispiels heraus."""
    # Teilt den String (z.B. "Huber, Julian") am Komma auf
    two_names = suchstring.split(", ")
    vorname = two_names[1]
    nachname = two_names[0]
    
    # Schleife durch die JSON-Daten
    for eintrag in person_data:
        # Vergleiche Nachname und Vorname einzeln
        if eintrag["lastname"] == nachname and eintrag["firstname"] == vorname:
            return eintrag  # Gibt das gefundene Dictionary zurück (statt nur print)
            
    return None # Falls keine Person gefunden wurde, gibt die Funktion None zurück




if __name__ == "__main__":
    # 1. Funktion testen: Daten laden
    p_data = load_person_data()
    print("Geladene Rohdaten aus JSON:")
    print(p_data)
    print("-" * 20)
    
    # 2. Funktion testen: Namensliste erstellen
    namen = get_person_list(p_data)
    print("Erstellte Namensliste für die Selectbox:")
    print(namen)
