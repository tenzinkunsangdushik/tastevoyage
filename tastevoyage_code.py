##############################################################################################################
# Title: Multi-User Login and Registration Example
# Author: Samuel Wehrli, Dominik Kunz
# Date: 05.05.2024
# Institution: ZHAW - Institute for Computational Health
#
# Description: 
# A Streamlit app that allows multiple users to login and register. 
# The app uses a CSV file to store user credentials and pushes it to a seperate Github repository. 
# The bcrypt library hashes the passwords and the binascii library to convert the hashed password to 
# a hexadecimal string. The app uses the GithubContents class from the github_contents.py file to 
# interact with the Github data repository. The st.secrets object stores the Github owner, repository, 
# and token which are used to authenticate the Github data repository.
#
# To run the app, install the required libraries using: pip install bcrypt binascii
##############################################################################################################


import binascii
import streamlit as st
import pandas as pd
from github_contents import GithubContents
import bcrypt

# Set constants
DATA_FILE = "MyLoginTable.csv"
DATA_COLUMNS = ['username', 'name', 'password']

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
        #replace the code bellow with your own code or switch to another page
        st.success(f"Hurray {st.session_state['username']}!! You are logged in.", icon="🤩")
        logout_button = st.button("Logout")
        if logout_button:
            st.session_state['authentication'] = False
            st.rerun()

if __name__ == "__main__":
    main()
