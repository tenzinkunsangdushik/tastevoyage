import streamlit as st
import pandas as pd
import os
import hashlib
import smtplib
from email.message import EmailMessage

# Konfiguration und Hilfsfunktionen
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_ADRESSE = 'your_email@example.com'
EMAIL_PASSWORT = 'your_password'
DATEN_PFAD = 'produkte.csv'
BILD_ORDNER = 'produkt_bilder'
BENUTZER_DATEN_PFAD = 'users.csv'

# Datenpfade und Initialisierung
if not os.path.exists(BILD_ORDNER):
    os.makedirs(BILD_ORDNER)
if not os.path.exists(BENUTZER_DATEN_PFAD):
    benutzer_df = pd.DataFrame(columns=['username', 'password'])
    benutzer_df.to_csv(BENUTZER_DATEN_PFAD, index=False)
else:
    benutzer_df = pd.read_csv(BENUTZER_DATEN_PFAD)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def verify_login(username, password, benutzer_df):
    user_info = benutzer_df[benutzer_df['username'] == username]
    if not user_info.empty and check_hashes(password, user_info.iloc[0]['password']):
        return True
    return False

def register_user(username, password, benutzer_df):
    if username not in benutzer_df['username'].values:
        benutzer_df = benutzer_df.append({'username': username, 'password': make_hashes(password)}, ignore_index=True)
        benutzer_df.to_csv(BENUTZER_DATEN_PFAD, index=False)
        return True
    return False

def bild_speichern(bild, name):
    print("Bild wird hochgeladen:", bild)  # Ausgabe zum Überprüfen
    if bild is not None:
        bild_filename = name + "_" + bild.name
        bild_path = os.path.join(BILD_ORDNER, bild_filename)
        if os.path.exists(bild_path):
            os.remove(bild_path)  # Lösche das vorhandene Bild, falls vorhanden
        with open(bild_path, "wb") as f:
            f.write(bild.getbuffer())
        if os.path.exists(bild_path):
            return bild_path
        else:
            st.error("Fehler beim Speichern des Bildes.")
        st.experimental_rerun()
    return ""

def bild_und_eintrag_loeschen(index, df):
    bildpfad = df.iloc[index]['Bildpfad']
    if bildpfad and os.path.exists(bildpfad):
        os.remove(bildpfad)
    df.drop(index, inplace=True)
    speichern_oder_aktualisieren(df)

def speichern_oder_aktualisieren(df):
    df.to_csv(DATEN_PFAD, index=False)

def hauptanwendung(benutzer_df):
    st.title('Herzlich Willkommen!')
    auswahl = st.sidebar.radio("Menü:", ["Hauptmenü", "Favoriten", "Ausprobieren"])
    if st.sidebar.button('Neues Produkt'):
        st.session_state['show_form'] = True

    if os.path.exists(DATEN_PFAD) and os.path.getsize(DATEN_PFAD) > 0:
        df = pd.read_csv(DATEN_PFAD)
    else:
        df = pd.DataFrame(columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad'])

    if auswahl == "Hauptmenü":
        if not df.empty:
            for i in range(0, len(df), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(df):
                        with cols[idx]:
                            item = df.iloc[i + idx]
                            bild_path = bild_speichern(item['Bild'], item['Name']) if 'Bild' in item and item['Bild'] else ""
                            if bild_path:
                                st.image(bild_path, width=150, caption=item['Name'])
                            else:
                                st.write("Kein Bild vorhanden")
                            st.write(f"Kategorie: {item['Kategorie']}")
                            st.write(f"Bewertung: {item['Bewertung']}")
                            st.write(f"Notizen: {item['Notizen']}")
                            option = st.selectbox("Optionen:", ["Aktion wählen", "Bearbeiten", "Löschen"], key=f"optionen{item.name}")
                            if option == "Bearbeiten":
                                st.session_state['show_form'] = True
                                st.session_state['edit_index'] = item.name
                            elif option == "Löschen":
                                bild_und_eintrag_loeschen(item.name, df)
                                st.experimental_rerun()

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

with st.sidebar:
    st.title("Anmeldung")
    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type='password')
    login_button = st.button("Anmelden")
    register_button = st.button("Registrieren")

    if login_button and verify_login(username, password, benutzer_df):
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        st.experimental_rerun()
    elif login_button:
        st.error("Falscher Benutzername/Passwort-Kombination")

    if register_button and register_user(username, password, benutzer_df):
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        st.success('Benutzer erfolgreich registriert.')
        st.experimental_rerun()
    elif register_button:
        st.error('Registrierung fehlgeschlagen.')

# Authentifizierungsstatus prüfen und Hauptanwendung anzeigen
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    hauptanwendung(benutzer_df)
else:
    st.info("Bitte melden Sie sich an, um fortzufahren.")

# Logout-Funktion in der Seitenleiste, falls eingeloggt
if st.session_state.get('logged_in'):
    if st.sidebar.button('Abmelden'):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['authentication_status'] = None
        st.experimental_rerun()
