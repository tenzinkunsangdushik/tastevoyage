import streamlit as st
import pandas as pd
import os
import hashlib
import binascii
from github_contents import GithubContents
import bcrypt
from PIL import Image

# Konfiguration und Hilfsfunktionen
DATEN_PFAD = 'produkte.csv'
BILD_ORDNER = 'produkt_bilder'
BENUTZER_DATEN_PFAD = 'users.csv'
DATA_FILE = "MyLoginTable.csv"
DATA_FILE_MAIN = "tastevoyage.csv"
DATA_FILE_FILTERED = 'filteredtastevoyage.csv'
DATA_COLUMNS = ['username', 'name', 'password']
DATA_COLUMNS_TV = ['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad', 'Benutzer_ID']
FAVORITEN_PFAD = 'favoriten.csv'

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
        benutzer_df = pd.concat([benutzer_df, pd.DataFrame([{'username': username, 'password': make_hashes(password)}])], ignore_index=True)
        benutzer_df.to_csv(BENUTZER_DATEN_PFAD, index=False)
        return True
    return False

def bild_speichern(bild, name):
    if bild is not None:
        bild_filename = name + "_" + bild.name
        bild_path = os.path.join(BILD_ORDNER, bild_filename)
        with open(bild_path, "wb") as f:
            f.write(bild.getbuffer())
        return os.path.join(BILD_ORDNER, bild_filename)
    return ""

def bild_und_eintrag_loeschen(index, df, pfad=DATEN_PFAD):
    bildpath = df.iloc[index]['Bildpfad']
    if bildpath and os.path.exists(bildpath):
        os.remove(bildpath)
    df.drop(index, inplace=True)
    speichern_oder_aktualisieren(df, pfad)

def speichern_oder_aktualisieren(df, pfad=DATEN_PFAD):
    df.to_csv(pfad, index=False)

def login_page():
    """ Login an existing user. """
    st.title("Login")
    with st.form(key='login_form'):
        st.session_state['username'] = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            authenticate(st.session_state.username, password)

def register_page():
    """ Register a new user. """
    st.title("Register")
    with st.form(key='register_form'):
        new_username = st.text_input("New Username")
        new_name = st.text_input("Name")
        new_password = st.text_input("New Password", type="password")
        if st.form_submit_button("Register"):
            hashed_password = bcrypt.hashpw(new_password.encode('utf8'), bcrypt.gensalt()) # Hash the password
            hashed_password_hex = binascii.hexlify(hashed_password).decode() # Convert hash to hexadecimal string
            
            # Check if the username already exists
            if new_username in st.session_state.df_users['username'].values:
                st.error("Username already exists. Please choose a different one.")
                return
            else:
                new_user = pd.DataFrame([[new_username, new_name, hashed_password_hex]], columns=DATA_COLUMNS)
                st.session_state.df_users = pd.concat([st.session_state.df_users, new_user], ignore_index=True)
                
                # Writes the updated dataframe to GitHub data repository
                st.session_state.github.write_df(DATA_FILE, st.session_state.df_users, "added new user")
                st.success("Registration successful! You can now log in.")

def authenticate(username, password):
    """ 
    Initialize the authentication status.

    Parameters:
    username (str): The username to authenticate.
    password (str): The password to authenticate.    
    """
    login_df = st.session_state.df_users
    login_df['username'] = login_df['username'].astype(str)

    if username in login_df['username'].values:
        stored_hashed_password = login_df.loc[login_df['username'] == username, 'password'].values[0]
        stored_hashed_password_bytes = binascii.unhexlify(stored_hashed_password) # convert hex to bytes
        
        # Check the input password
        if bcrypt.checkpw(password.encode('utf8'), stored_hashed_password_bytes): 
            st.session_state['authentication'] = True
            st.success('Login successful')
            st.rerun()
        else:
            st.error('Incorrect password')
    else:
        st.error('Username not found')

def init_github():
    """Initialize the GithubContents object."""
    if 'github' not in st.session_state:
        st.session_state.github = GithubContents(
            st.secrets["github"]["owner"],
            st.secrets["github"]["repo"],
            st.secrets["github"]["token"])
        print("github initialized")
    
def init_credentials():
    """Initialize or load the dataframe."""
    if 'df_users' in st.session_state:
        pass

    if st.session_state.github.file_exists(DATA_FILE):
        st.session_state.df_users = st.session_state.github.read_df(DATA_FILE)
    else:
        st.session_state.df_users = pd.DataFrame(columns=DATA_COLUMNS)

def init_tastevoyage():
    if st.session_state.github.file_exists(DATA_FILE_MAIN):
        st.session_state.df_tastevoyage = st.session_state.github.read_df(DATA_FILE_MAIN)
    else:
        st.session_state.df_tastevoyage = pd.DataFrame(columns=DATA_COLUMNS_TV)


def init_filtered_df():
    if st.session_state.github.file_exists(DATA_FILE_FILTERED):
        st.session_state.df_filtered = st.session_state.github.read_df(DATA_FILE_FILTERED)
    else:
        st.session_state.df_filtered = pd.DataFrame(columns=DATA_COLUMNS_TV)

def show_item(item, index, df, favoriten_df=None):
    try:
        if item['Bildpfad']:  # Überprüfen, ob ein Bildpfad vorhanden ist
            image = Image.open(item['Bildpfad'])
            image = image.resize((200, 400))  # Breite und Höhe festlegen
            st.image(image, caption=item['Name'])
        else:
            st.write("Kein Bild vorhanden")
    except FileNotFoundError:
        st.write("Bild nicht gefunden")
    st.markdown(f"### *{item['Name']}*")
    st.write(f"Kategorie: {item['Kategorie']}")
    st.write(f"Bewertung: {item['Bewertung']}")
    st.write(f"Notizen: {item['Notizen']}")
    option = st.selectbox("Optionen:", ["Aktion wählen", "Bearbeiten", "Löschen"] + (["Zu Favoriten hinzufügen"] if favoriten_df is not None else ["Entfernen"]), key=f"optionen{index}")
    if option == "Bearbeiten":
        st.session_state['show_form'] = True
        st.session_state['edit_index'] = index
    elif option == "Löschen":
        bild_und_eintrag_loeschen(index, df)
        st.experimental_rerun()
    elif option == "Zu Favoriten hinzufügen" and favoriten_df is not None:
        favoriten_df = pd.concat([favoriten_df, pd.DataFrame([item])], ignore_index=True)
        speichern_oder_aktualisieren(favoriten_df, FAVORITEN_PFAD)
        st.success(f"{item['Name']} wurde zu den Favoriten hinzugefügt!")
    elif option == "Entfernen" and favoriten_df is None:
        bild_und_eintrag_loeschen(index, df, FAVORITEN_PFAD)
        st.experimental_rerun()

def hauptanwendung(benutzer_df):
    st.title(f"Herzlich Willkommen, {st.session_state['username']}!")
    auswahl = st.sidebar.radio("Menü:", ["Hauptmenü", "Favoriten", "Ausprobieren", "Statistiken"])
    
    if st.sidebar.button('Neues Produkt'):
        st.session_state['show_form'] = True
    
    init_tastevoyage()
    init_filtered_df()
    # if os.path.exists(DATEN_PFAD) and os.path.getsize(DATEN_PFAD) > 0:
    #     df = pd.read_csv(DATEN_PFAD)
    # else:
    #     df = pd.DataFrame(columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad', 'Benutzer_ID'])
    
    # if os.path.exists(FAVORITEN_PFAD) and os.path.getsize(FAVORITEN_PFAD) > 0:
    #     favoriten_df = pd.read_csv(FAVORITEN_PFAD)
    # else:
    #     favoriten_df = pd.DataFrame(columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad', 'Benutzer_ID'])
    df = st.session_state.df_tastevoyage[st.session_state.df_tastevoyage['Benutzer_ID'] == st.session_state['username']]
    favoriten_df = st.session_state.df_filtered[st.session_state.df_filtered['Benutzer_ID'] == st.session_state['username']]

    produktsuche(df)  # Produktsuche-Funktion hinzufügen

    if auswahl == "Hauptmenü":
        if not df.empty:
            for i in range(0, len(df), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(df):
                        with cols[idx]:
                            show_item(df.iloc[i + idx], i + idx, df, favoriten_df)
    
    elif auswahl == "Favoriten":
        if not favoriten_df.empty:
            for i in range(0, len(favoriten_df), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(favoriten_df):
                        with cols[idx]:
                            show_item(favoriten_df.iloc[i + idx], i + idx, favoriten_df)
    
    elif auswahl == "Statistiken":
        statistik_seite(df)

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
                    df.at[st.session_state['edit_index'], 'Benutzer_ID'] = st.session_state['username']
                    del st.session_state['edit_index']
                else:
                    bild_path = bild_speichern(bild, name) if bild else ""
                    neues_produkt = pd.DataFrame([[kategorie, name, bewertung, notizen, bild_path]], columns=['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad'])
                    df = pd.concat([df, neues_produkt], ignore_index=True)
                speichern_oder_aktualisieren(df)
                st.success("Produkt erfolgreich gespeichert!")
                st.session_state['show_form'] = False
                st.experimental_rerun()

import matplotlib.pyplot as plt

def statistik_seite(df):
    st.title("Statistiken")
    
    # Durchschnittsbewertung pro Kategorie
    avg_bewertung = df.groupby('Kategorie')['Bewertung'].mean().sort_values()
    st.subheader("Durchschnittsbewertung pro Kategorie")
    fig, ax = plt.subplots()
    avg_bewertung.plot(kind='barh', ax=ax)
    st.pyplot(fig)

    # Anzahl der Produkte pro Kategorie
    anzahl_produkte = df['Kategorie'].value_counts()
    st.subheader("Anzahl der Produkte pro Kategorie")
    fig, ax = plt.subplots()
    anzahl_produkte.plot(kind='bar', ax=ax)
    st.pyplot(fig)
def main():
    init_github() # Initialize the GithubContents object
    init_credentials() # Loads the credentials from the Github data repository

    if 'authentication' not in st.session_state:
        st.session_state['authentication'] = False

    if not st.session_state['authentication']:
        options = st.sidebar.selectbox("Select a page", ["Login", "Register"])
        if options == "Login":
            login_page()
        elif options == "Register":
            register_page()
    else:
        with st.sidebar:
            logout_button = st.button("Logout")
            if logout_button:
                st.session_state['authentication'] = False
                st.rerun()
        hauptanwendung(st.session_state['df_users']) 

def produktsuche(df):
    st.sidebar.subheader("Produktsuche")
    suche = st.sidebar.text_input("Produktname eingeben")
    suchergebnisse = pd.DataFrame()  # Hier initialisieren
    if suche:
        suchergebnisse = df[df['Name'].str.contains(suche, case=False, na=False)]
    if not suchergebnisse.empty:
            st.write(f"Suchergebnisse für '{suche}':")
            for i in range(0, len(suchergebnisse), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(suchergebnisse):
                        with cols[idx]:
                            show_item(suchergebnisse.iloc[i + idx], i + idx, suchergebnisse)
            else:
                st.write("Keine Produkte gefunden.")


def main():
    init_github()  # Initialize the GithubContents object
    init_credentials()  # Loads the credentials from the Github data repository

    if 'authentication' not in st.session_state:
        st.session_state['authentication'] = False

    if not st.session_state['authentication']:
        options = st.sidebar.selectbox("Select a page", ["Login", "Register"])
        if options == "Login":
            login_page()
        elif options == "Register":
            register_page()
    else:
        with st.sidebar:
            logout_button = st.button("Logout")
            if logout_button:
                st.session_state['authentication'] = False
                st.rerun()
        hauptanwendung(st.session_state['df_users'])

if __name__ == "__main__":
    main()
