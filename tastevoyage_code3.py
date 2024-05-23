import streamlit as st
import pandas as pd
import os
import hashlib
import binascii
import base64
from github_contents import GithubContents
import bcrypt
from PIL import Image
import matplotlib.pyplot as plt
import io

# Konfiguration und Hilfsfunktionen
DATEN_PFAD = 'produkte.csv'
BILD_ORDNER = 'produkt_bilder'
BENUTZER_DATEN_PFAD = 'users.csv'
DATA_FILE = "MyLoginTable.csv"
DATA_FILE_MAIN = "tastevoyage.csv"
DATA_FILE_FILTERED = 'filteredtastevoyage.csv'
DATA_COLUMNS = ['username', 'name', 'password']
DATA_COLUMNS_TV = ['username', 'Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bilddaten']
FAVORITEN_PFAD = 'favoriten.csv'

# Initialisiere Github-Verbindung
def init_github():
    """Initialize the GithubContents object."""
    if 'github' not in st.session_state:
        st.session_state.github = GithubContents(
            st.secrets["github"]["owner"],
            st.secrets["github"]["repo"],
            st.secrets["github"]["token"])
        print("github initialized")

# Bild hochladen und in Base64 konvertieren
def bild_speichern_base64(bild):
    if bild is not None:
        img_bytes = bild.read()
        img_base64 = base64.b64encode(img_bytes).decode()
        return img_base64
    return ""

# Speichern oder Aktualisieren der CSV-Datei auf GitHub
def speichern_oder_aktualisieren(df, pfad):
    csv_content = df.to_csv(index=False)
    if pfad == DATA_FILE_MAIN:
        st.session_state.github.write(pfad, csv_content, "Updated tastevoyage data")
    elif pfad == FAVORITEN_PFAD:
        st.session_state.github.write(pfad, csv_content, "Updated favorites data")
    else:
        st.session_state.github.write(pfad, csv_content, "Updated data")

def login_page():
    """Login an existing user."""
    st.title("Login")
    with st.form(key='login_form'):
        st.session_state['username'] = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            authenticate(st.session_state.username, password)

def register_page():
    """Register a new user."""
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
            st.experimental_rerun()
        else:
            st.error('Incorrect password')
    else:
        st.error('Username not found')

def init_credentials():
    """Initialize or load the dataframe."""
    if 'df_users' not in st.session_state:
        if st.session_state.github.file_exists(DATA_FILE):
            st.session_state.df_users = st.session_state.github.read_df(DATA_FILE)
        else:
            st.session_state.df_users = pd.DataFrame(columns=DATA_COLUMNS)

def init_tastevoyage():
    if 'df_tastevoyage' not in st.session_state:
        if st.session_state.github.file_exists(DATA_FILE_MAIN):
            st.session_state.df_tastevoyage = st.session_state.github.read_df(DATA_FILE_MAIN)
        else:
            st.session_state.df_tastevoyage = pd.DataFrame(columns=DATA_COLUMNS_TV)
    # Debugging-Ausgabe hinzufügen
    print("Tastevoyage DataFrame nach dem Laden:")
    print(st.session_state.df_tastevoyage)

    # Überprüfe, ob 'username' in den Spalten enthalten ist
    if 'username' not in st.session_state.df_tastevoyage.columns:
        print("Warnung: 'username' Spalte nicht im DataFrame vorhanden!")
        # Füge 'username' Spalte hinzu, wenn sie fehlt
        st.session_state.df_tastevoyage['username'] = None

    # Zusätzliche Debugging-Ausgabe der Spalten
    print("Spalten im DataFrame:", st.session_state.df_tastevoyage.columns)

def init_filtered_df():
    if 'df_filtered' not in st.session_state:
        if st.session_state.github.file_exists(DATA_FILE_FILTERED):
            st.session_state.df_filtered = st.session_state.github.read_df(DATA_FILE_FILTERED)
        else:
            st.session_state.df_filtered = pd.DataFrame(columns=DATA_COLUMNS_TV)

def show_item(item, index, df, favoriten_df=None):
    if 'Bilddaten' not in item:
        item['Bilddaten'] = ""
    if 'Kategorie' not in item:
        item['Kategorie'] = ""
    if 'Name' not in item:
        item['Name'] = ""
    if 'Bewertung' not in item:
        item['Bewertung'] = ""
    if 'Notizen' not in item:
        item['Notizen'] = ""

    try:
        if isinstance(item['Bilddaten'], str) and item['Bilddaten']:  # Überprüfen, ob Bilddaten vorhanden und ein String sind
            img_data = base64.b64decode(item['Bilddaten'])
            image = Image.open(io.BytesIO(img_data))
            image = image.resize((200, 400))  # Breite und Höhe festlegen
            st.image(image, caption=item['Name'])
        else:
            st.write("Kein Bild vorhanden")
    except Exception as e:
        st.write("Fehler beim Laden des Bildes:", e)
    st.markdown(f"### {item['Name']}")
    st.write(f"Kategorie: {item['Kategorie']}")
    st.write(f"Bewertung: {item['Bewertung']}")
    st.write(f"Notizen: {item['Notizen']}")
    option = st.selectbox("Optionen:", ["Aktion wählen", "Bearbeiten", "Löschen"] + (["Zu Favoriten hinzufügen"] if favoriten_df is not None else ["Entfernen"]), key=f"optionen{index}")
    if option == "Bearbeiten":
        st.session_state['show_form'] = True
        st.session_state['edit_index'] = index
    elif option == "Löschen":
        bild_und_eintrag_loeschen(index, df, DATA_FILE_MAIN)
        st.experimental_rerun()
    elif option == "Zu Favoriten hinzufügen" and favoriten_df is not None:
        favoriten_df = pd.concat([favoriten_df, pd.DataFrame([item])], ignore_index=True)
        speichern_oder_aktualisieren(favoriten_df, FAVORITEN_PFAD)
        st.success(f"{item['Name']} wurde zu den Favoriten hinzugefügt!")
    elif option == "Entfernen" and favoriten_df is not None:
        favoriten_df.drop(index, inplace=True)
        speichern_oder_aktualisieren(favoriten_df, FAVORITEN_PFAD)
        st.success(f"{item['Name']} wurde aus den Favoriten entfernt!")
        st.experimental_rerun()

def bild_und_eintrag_loeschen(index, df, pfad=DATEN_PFAD):
    if 'Bilddaten' in df.columns:
        df.drop(index, inplace=True)
        speichern_oder_aktualisieren(df, pfad)
    else:
        st.error(f"Index {index} not found in dataframe. Unable to delete.")

def hauptanwendung():
    st.title(f"Herzlich Willkommen, {st.session_state['username']}!")
    auswahl = st.sidebar.radio("Menü:", ["Hauptmenü", "Favoriten", "Statistiken"])
    
    if st.sidebar.button('Neues Produkt'):
        st.session_state['show_form'] = True
    
    init_tastevoyage()
    
    if st.session_state.github.file_exists(FAVORITEN_PFAD):
        favoriten_df = st.session_state.github.read_df(FAVORITEN_PFAD)
    else:
        favoriten_df = pd.DataFrame(columns=DATA_COLUMNS_TV)
    
    produktsuche(st.session_state.df_tastevoyage)  # Produktsuche-Funktion hinzufügen

    # Debugging-Ausgabe hinzufügen
    print("Tastevoyage DataFrame vor dem Filtern:")
    print(st.session_state.df_tastevoyage)

    # Filtere die Daten basierend auf dem aktuellen Benutzer
    user_data = st.session_state.df_tastevoyage[st.session_state.df_tastevoyage['username'] == st.session_state['username']]
    
    # Debugging-Ausgabe hinzufügen
    print("Gefilterte Benutzerdaten:")
    print(user_data)

    if auswahl == "Hauptmenü":
        if not user_data.empty:
            for i in range(0, len(user_data), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(user_data):
                        with cols[idx]:
                            show_item(user_data.iloc[i + idx], i + idx, user_data, favoriten_df)
    
    elif auswahl == "Favoriten":
        user_favorites = favoriten_df[favoriten_df['username'] == st.session_state['username']]
        if not user_favorites.empty:
            for i in range(0, len(user_favorites), 2):
                cols = st.columns(2)
                for idx in range(2):
                    if i + idx < len(user_favorites):
                        with cols[idx]:
                            show_item(user_favorites.iloc(i + idx), i + idx, user_favorites)
    
    elif auswahl == "Statistiken":
        statistik_seite(user_data)

    if 'show_form' in st.session_state and st.session_state['show_form']:
        with st.form(key='neues_produkt_form'):
            kategorie = st.text_input("Kategorie des Produkts:", value="" if 'edit_index' not in st.session_state else st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Kategorie'])
            name = st.text_input("Name des Produkts:", value="" if 'edit_index' not in st.session_state else st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Name'])
            bewertung = st.slider("Bewertung:", 1, 10, 5 if 'edit_index' not in st.session_state else st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Bewertung'])
            bild = st.file_uploader("Bild des Produkts hochladen:", type=['jpg', 'png'], key='bild')
            notizen = st.text_area("Notizen zum Produkt:", value="" if 'edit_index' not in st.session_state else st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Notizen'])
            submit_button = st.form_submit_button("Produkt speichern")
            if submit_button:
                if 'edit_index' in st.session_state:
                    if bild:
                        bild_data = bild_speichern_base64(bild)
                    else:
                        bild_data = st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Bilddaten']
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Kategorie'] = kategorie
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Name'] = name
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Bewertung'] = bewertung
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Notizen'] = notizen
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Bilddaten'] = bild_data
                    del st.session_state['edit_index']
                else:
                    bild_data = bild_speichern_base64(bild) if bild else ""
                    neues_produkt = pd.DataFrame([[st.session_state['username'], kategorie, name, bewertung, notizen, bild_data]], columns=DATA_COLUMNS_TV)
                    st.session_state.df_tastevoyage = pd.concat([st.session_state.df_tastevoyage, neues_produkt], ignore_index=True)
                speichern_oder_aktualisieren(st.session_state.df_tastevoyage, DATA_FILE_MAIN)
                st.success("Produkt erfolgreich gespeichert!")
                st.session_state['show_form'] = False
                st.experimental_rerun()

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

def produktsuche(df):
    st.sidebar.subheader("Produktsuche")
    suche = st.sidebar.text_input("Produktname eingeben")
    suchergebnisse = pd.DataFrame()  # Hier initialisieren
    if suche:
        # Filtere die Suchergebnisse basierend auf dem aktuellen Benutzer
        suchergebnisse = df[(df['username'] == st.session_state['username']) & df['Name'].str.contains(suche, case=False, na=False)]
    if not suchergebnisse.empty:
        st.write(f"Suchergebnisse für '{suche}':")
        for i in range(0, len(suchergebnisse), 2):
            cols = st.columns(2)
            for idx in range(2):
                if i + idx < len(suchergebnisse):
                    with cols[idx]:
                        show_item(suchergebnisse.iloc[i + idx], i + idx, suchergebnisse)

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
                st.experimental_rerun()
        hauptanwendung()

if __name__ == "__main__":
    main()
