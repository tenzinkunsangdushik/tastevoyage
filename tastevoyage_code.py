import streamlit as st
import pandas as pd
import os
import hashlib
import smtplib
from email.message import EmailMessage
import binascii
import streamlit as st
import pandas as pd
from github_contents import GithubContents
import bcrypt

# Konfiguration und Hilfsfunktionen
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_ADRESSE = 'your_email@example.com'
EMAIL_PASSWORT = 'your_password'
DATEN_PFAD = 'produkte.csv'
BILD_ORDNER = 'produkt_bilder'
BENUTZER_DATEN_PFAD = 'users.csv'
DATA_FILE = "MyLoginTable.csv"
DATA_FILE_MAIN = "tastevoyage.csv"
DATA_COLUMNS = ['username', 'name', 'password']
DATA_COLUMNS_TV = ['Kategorie', 'Name', 'Bewertung', 'Notizen', 'Bildpfad']

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
    if bild is not None:
        bild_filename = name + "_" + bild.name
        bild_path = os.path.join(BILD_ORDNER, bild_filename)
        with open(bild_path, "wb") as f:
            f.write(bild.getbuffer())
        return os.path.join(BILD_ORDNER, bild_filename)
    return ""

def bild_und_eintrag_loeschen(index, df):
    bildpath = df.iloc[index]['Bildpfad']
    if bildpath and os.path.exists(bildpath):
        os.remove(bildpath)
    df.drop(index, inplace=True)
    speichern_oder_aktualisieren(df)

def speichern_oder_aktualisieren(df):
    df.to_csv(DATEN_PFAD, index=False)


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


def hauptanwendung(benutzer_df):
    st.title('Herzlich Willkommen!')
    auswahl = st.sidebar.radio("Menü:", ["Hauptmenü", "Favoriten", "Ausprobieren"])
    if st.sidebar.button('Neues Produkt'):
        st.session_state['show_form'] = True

    init_tastevoyage()
    if 'df_tastevoyage' not in st.session_state:
        st.session_state.df_tastevoyage = pd.DataFrame(columns=DATA_COLUMNS_TV)
    st.dataframe(st.session_state.df_tastevoyage)

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
                        bild_path = bild_speichern(bild, name)
                        if st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Bildpfad']:
                            os.remove(st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Bildpfad'])
                    else:
                        bild_path = st.session_state.df_tastevoyage.iloc[st.session_state['edit_index']]['Bildpfad']
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Kategorie'] = kategorie
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Name'] = name
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Bewertung'] = bewertung
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Notizen'] = notizen
                    st.session_state.df_tastevoyage.at[st.session_state['edit_index'], 'Bildpfad'] = bild_path
                    del st.session_state['edit_index']
                else:
                    bild_path = bild_speichern(bild, name) if bild else ""
                    neues_produkt = pd.DataFrame([[kategorie, name, bewertung, notizen, bild_path]], columns=DATA_COLUMNS_TV)
                    st.session_state.df_tastevoyage = pd.concat([st.session_state.df_tastevoyage, neues_produkt], ignore_index=True)
                    st.session_state.github.write_df(DATA_FILE_MAIN, st.session_state.df_tastevoyage, "added new input")

                speichern_oder_aktualisieren(st.session_state.df_tastevoyage)
                st.success("Produkt erfolgreich gespeichert!")
                st.session_state['show_form'] = False
                st.experimental_rerun()


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
        hauptanwendung(benutzer_df)
        #replace the code bellow with your own code or switch to another page
        logout_button = st.button("Logout")
        if logout_button:
            st.session_state['authentication'] = False
            st.rerun()

if __name__ == "__main__":
    main()


