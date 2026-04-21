import streamlit as st
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Fonction pour configurer la connexion a la base de donnees
@st.cache_resource
def get_db_connection():
    # Charge les variables d'environnement du fichier .env
    load_dotenv() 
    
    # Recuperation des identifiants de connexion
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    
    # Construction de l'URL de connexion PostgreSQL
    url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    try:
        # Creation du moteur SQLAlchemy
        engine = create_engine(url)
        return engine
    except Exception as e:
        # Affichage d'une erreur si la connexion echoue
        st.error(f"Erreur de connexion : {e}")
        return None