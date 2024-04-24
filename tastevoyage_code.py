
import streamlit as st
import pandas as pd
import os
import hashlib

# Hilfsfunktion, um Passwörter zu hashen
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Hilfsfunktion, um die Passwörter zu überprüfen
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Login-Daten Setup
USER_DATA = {"username": make_hashes("admin")}

# Verzeichnisstruktur Setup
DATA_PATH = 'produkte.csv'
IMAGE_FOLDER = 'produkt_bilder'
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Funktionen ...

# Rest des Codes ...

# Anmeldeseite
def login():
    st.sidebar.title("Anmeldung")

    username = st.sidebar.text_input("Benutzername")
    password = st.sidebar.text_input("Passwort", type='password')

    if st.sidebar.checkbox("Anmelden"):
        hashed_pswd = make_hashes(password)

        # Benutzerüberprüfung
        if username in USER_DATA and USER_DATA[username] == hashed_pswd:
            st.session_state['logged_in'] = True
        else:
            st.sidebar.warning("Falsche Benutzername/Passwort-Kombination")

# Überprüfen, ob Benutzer bereits angemeldet ist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_app()  # Ihre Hauptanwendungsfunktion
else:
    login()  # Zeigt die Login-Seite



def speichern_oder_aktualisieren(df):
    df.to_csv(DATA_PATH, index=False, header=True)

def bild_speichern(bild, name):
    if bild is not None:
        bild_filename = name + "_" + bild.name
        bild_path = os.path.join(IMAGE_FOLDER, bild_filename)
        with open(bild_path, "wb") as f:
            f.write(bild.getbuffer())
        return os.path.join(IMAGE_FOLDER, bild_filename)
    return ""

def bild_und_eintrag_loeschen(index, df):
    bildpfad = df.iloc[index]['Bildpfad']
    vollstaendiger_pfad = os.path.join(IMAGE_FOLDER, bildpfad)
    if bildpfad and os.path.exists(vollstaendiger_pfad):
        os.remove(vollstaendiger_pfad)
    df.drop(index, inplace=True)
    speichern_oder_aktualisieren(df)


st.markdown("""
<style>
.card {
    border: 1px solid #eeeeee;
    border-radius: 5px;
    padding: 16px;
    margin: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.heart {
    font-size: 1.5em;
    color: #ff0000;
    position: absolute;
    top: 16px;
    right: 16px;
    cursor: pointer;
}
.name {
    font-size: 1.5em;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


auswahl = st.sidebar.radio("Menü:", ["Hauptmenü", "Favoriten", "Need to try"])
if st.sidebar.button('Neues Produkt'):
    st.session_state['show_form'] = True

if os.path.exists(DATA_PATH) and os.path.getsize(DATA_PATH) > 0:
    df = pd.read_csv(DATA_PATH)
else:
    df = pd.DataFrame(columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad'])
if auswahl == "Hauptmenü":
    if not df.empty:
        items_per_row = 2
        rows = [df.iloc[i:i + items_per_row] for i in range(0, len(df), items_per_row)]
        for row in rows:
            cols = st.columns(items_per_row)
            for idx, col in enumerate(cols):
                if idx < len(row):
                    with col:
                        item = row.iloc[idx]
                        if item['Bildpfad'] and os.path.exists(item['Bildpfad']):
                            st.image(item['Bildpfad'], width=150, caption=item['Name'])
                        else:
                            st.write("Kein Bild vorhanden")
                        st.write(f"Kategorie: {item['Kategorie']}")
                        st.write(f"Bewertung: {item['Bewertung']}")
                        st.write(f"Notizen: {item['Notizen']}")
                        option = st.selectbox("Optionen:", ["Aktion wählen", "Bearbeiten", "Löschen"], key=f"options{item.name}")
                        if option == "Bearbeiten":
                            st.session_state['show_form'] = True
                            st.session_state['edit_index'] = item.name
                        elif option == "Löschen":
                            bild_und_eintrag_loeschen(item.name, df)
                            st.experimental_rerun()
                        
    else:
        st.write("Keine Produkte gespeichert.")
if 'show_form' in st.session_state and st.session_state['show_form']:
    with st.form(key='neues_produkt_form'):
        kategorie = st.text_input("Kategorie des Produkts:", value="" if 'edit_index' not in st.session_state else df.iloc[st.session_state['edit_index']]['Kategorie'])
        name = st.text_input("Name des Produkts:", value="" if 'edit_index' not in st.session_state else df.iloc[st.session_state['edit_index']]['Name'])
        bewertung = st.slider("Bewertung:", 1, 10, 5 if 'edit_index' not in st.session_state else df.iloc[st.session_state['edit_index']]['Bewertung'])
        bild = st.file_uploader("Bild des Produkts hochladen:", type=['jpg', 'png'], key='bild')
        notizen = st.text_area("Notizen zum Produkt:", value="" if 'edit_index' not in st.session_state else df.iloc[st.session_state['edit_index']]['Notizen'])
        submit_button = st.form_submit_button("Produkt speichern")
        
        if submit_button:
            if 'edit_index' in st.session_state:
                if bild:
                    bild_path = bild_speichern(bild, name)
                    if df.iloc[st.session_state['edit_index']]['Bildpfad']:
                        os.remove(df.iloc[st.session_state['edit_index']]['Bildpfad'])
                else:
                    bild_path = df.iloc[st.session_state['edit_index']]['Bildpfad']
                df.at[st.session_state['edit_index'], 'Kategorie'] = kategorie
                df.at[st.session_state['edit_index'], 'Name'] = name
                df.at[st.session_state['edit_index'], 'Bewertung'] = bewertung
                df.at[st.session_state['edit_index'], 'Notizen'] = notizen
                df.at[st.session_state['edit_index'], 'Bildpfad'] = bild_path
                del st.session_state['edit_index']
            else:
                bild_path = bild_speichern(bild, name) if bild else ""
                neues_produkt = pd.DataFrame([[kategorie, name, bewertung, notizen, bild_path]], columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad'])
                df = pd.concat([df, neues_produkt], ignore_index=True)
            speichern_oder_aktualisieren(df)
            st.success("Produkt erfolgreich gespeichert!")
            st.session_state['show_form'] = False
