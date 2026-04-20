import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import plotly.express as px

# Configuration de base de la page
st.set_page_config(page_title="FinanceCore Dashboard", layout="wide")

# Fonction pour se connecter a la base de donnees
@st.cache_resource
def get_db_connection():
    load_dotenv('.env') # Charge les variables du fichier .env
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ton_mot_de_passe")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "financecore_db")
    
    DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    try:
        return create_engine(DATABASE_URI)
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return None

engine = get_db_connection()

# Fonction pour extraire et preparer les donnees
@st.cache_data
def load_data():
    if engine is None:
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        # Requete SQL pour les transactions avec jointures
        query_trans = """
        SELECT 
            t.transaction_id AS id_transaction, 
            t.montant, 
            t.type_operation AS type_transaction, 
            t.date_transaction, 
            t.statut,
            p.nom_produit AS produit_bancaire,  
            cl.client_id AS id_client, 
            cl.nom_segment AS segment, 
            a.nom_agence AS agence             
        FROM transaction t
        JOIN compte co ON t.compte_id = co.compte_id
        JOIN client cl ON co.client_id = cl.client_id
        LEFT JOIN produit p ON co.produit_id = p.produit_id
        LEFT JOIN agence a ON co.agence_id = a.agence_id
        """
        df_trans = pd.read_sql(query_trans, engine)
        
        # Traitement des dates pour faciliter l'analyse
        df_trans['date_transaction'] = pd.to_datetime(df_trans['date_transaction'])
        df_trans['annee'] = df_trans['date_transaction'].dt.year
        df_trans['mois_annee'] = df_trans['date_transaction'].dt.to_period('M').astype(str)

        # Requete SQL pour analyser le risque des clients
        query_clients = """
        SELECT 
            cl.client_id AS id_client, 
            cl.client_id AS nom,  
            cl.score_credit_client AS score_credit, 
            cl.nom_segment AS segment, 
            a.nom_agence AS agence,
            COUNT(t.transaction_id) AS nb_transactions,
            SUM(CASE WHEN t.statut = 'Rejeté' THEN 1 ELSE 0 END) AS nb_rejets,
            SUM(t.montant) AS montant_total
        FROM client cl
        LEFT JOIN compte co ON cl.client_id = co.client_id
        LEFT JOIN transaction t ON co.compte_id = t.compte_id
        LEFT JOIN agence a ON co.agence_id = a.agence_id
        GROUP BY cl.client_id, cl.score_credit_client, cl.nom_segment, a.nom_agence
        """
        df_clients = pd.read_sql(query_clients, engine)
        
        # Calcul du taux de rejet
        df_clients['taux_rejet'] = (df_clients['nb_rejets'] / df_clients['nb_transactions']).fillna(0) * 100
        
        # Fonction pour definir le niveau de risque selon le score
        def categoriser_risque(score):
            if score < 400: return 'Risqué'
            elif score >= 400 and score < 700: return 'Standard'
            else: return 'Premium'
            
        df_clients['categorie_risque'] = df_clients['score_credit'].apply(categoriser_risque)
        
        return df_trans, df_clients
    except Exception as e:
        st.error(f"Erreur SQL : {e}")
        return pd.DataFrame(), pd.DataFrame()

# Chargement des donnees
df_trans, df_clients = load_data()

# Verification si les donnees sont vides
if df_trans.empty or df_clients.empty:
    st.warning("En attente des donnees de la base PostgreSQL...")
    st.stop()

# Configuration du menu lateral (Sidebar)
st.sidebar.title("FinanceCore SA")
st.sidebar.markdown("---")

# Menu de navigation
page = st.sidebar.radio("Navigation :", ["Vue Executive", "Analyse des Risques"])

st.sidebar.markdown("---")
st.sidebar.subheader("Filtres Globaux")

# Recuperation des valeurs uniques pour les filtres
agences = ["Toutes"] + list(df_trans['agence'].dropna().unique())
segments = ["Tous"] + list(df_trans['segment'].dropna().unique())
produits = ["Tous"] + list(df_trans['produit_bancaire'].dropna().unique())
annees = sorted(list(df_trans['annee'].dropna().unique()))

# Affichage des filtres interactifs
filtre_agence = st.sidebar.selectbox("Agence", agences)
filtre_segment = st.sidebar.selectbox("Segment Client", segments)
filtre_produit = st.sidebar.selectbox("Produit Bancaire", produits)

# Filtre pour l'annee (slider)
if len(annees) > 1:
    filtre_annee = st.sidebar.slider("Periode (Annee)", min(annees), max(annees), (min(annees), max(annees)))
else:
    filtre_annee = (annees[0], annees[0]) if annees else (2022, 2024)

# Creation des masques pour filtrer les donnees selon les choix de l'utilisateur
mask_t = pd.Series(True, index=df_trans.index)
mask_c = pd.Series(True, index=df_clients.index)

if filtre_agence != "Toutes":
    mask_t &= (df_trans['agence'] == filtre_agence)
    mask_c &= (df_clients['agence'] == filtre_agence)
if filtre_segment != "Tous":
    mask_t &= (df_trans['segment'] == filtre_segment)
    mask_c &= (df_clients['segment'] == filtre_segment)
if filtre_produit != "Tous":
    mask_t &= (df_trans['produit_bancaire'] == filtre_produit)
    
mask_t &= (df_trans['annee'] >= filtre_annee[0]) & (df_trans['annee'] <= filtre_annee[1])

# Application des filtres
df_f_trans = df_trans[mask_t]
df_f_clients = df_clients[mask_c]

# Page 1 : Vue Executive
if page == "Vue Executive":
    st.title("Vue Executive - Performances Globales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Calcul des indicateurs principaux (KPIs)
    vol_total = len(df_f_trans)
    ca_total = df_f_trans[df_f_trans['type_transaction'] == 'Credit']['montant'].sum()
    clients_actifs = df_f_trans['id_client'].nunique()
    marge_estimee = ca_total * 0.15 
    
    # Affichage des indicateurs
    col1.metric("Volume Transactions", f"{vol_total:,}")
    col2.metric("Chiffre d'Affaires", f"{ca_total:,.0f} €")
    col3.metric("Clients Actifs", f"{clients_actifs:,}")
    col4.metric("Marge Moyenne (15%)", f"{marge_estimee:,.0f} €")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Evolution Mensuelle")
        # Preparation et affichage du graphique des tendances mensuelles
        evo = df_f_trans.groupby(['mois_annee', 'type_transaction'])['montant'].sum().reset_index()
        fig_line = px.line(evo, x='mois_annee', y='montant', color='type_transaction', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.subheader("CA par Agence et par Produit")
        # Preparation et affichage du graphique en barres
        bar_data = df_f_trans[df_f_trans['type_transaction'] == 'Credit'].groupby(['agence', 'produit_bancaire'])['montant'].sum().reset_index()
        fig_bar = px.bar(bar_data, x='agence', y='montant', color='produit_bancaire', barmode='group', text_auto='.2s')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("Repartition des Clients par Segment")
        # Preparation et affichage du diagramme circulaire
        pie_data = df_f_trans.groupby('segment')['id_client'].nunique().reset_index()
        couleurs_seg = {'Premium':'#22c55e', 'Standard':'#3b82f6', 'Risqué':'#ef4444'}
        fig_pie = px.pie(pie_data, names='segment', values='id_client', hole=0.4, color='segment', color_discrete_map=couleurs_seg)
        st.plotly_chart(fig_pie, use_container_width=True)

# Page 2 : Analyse des Risques
elif page == "Analyse des Risques":
    st.title("Analyse des Risques et Scoring")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Matrice de Correlation")
        # Affichage de la correlation entre les variables numeriques
        corr_matrix = df_f_clients[['score_credit', 'montant_total', 'taux_rejet']].corr()
        fig_heat = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with c2:
        st.subheader("Score Credit vs Montant Transaction")
        # Affichage du nuage de points pour voir la repartition des risques
        couleurs_risque = {'Risqué':'#ef4444', 'Standard':'#f97316', 'Premium':'#22c55e'}
        fig_scatter = px.scatter(df_f_clients, x='score_credit', y='montant_total', 
                                 color='categorie_risque', color_discrete_map=couleurs_risque,
                                 hover_data=['nom', 'taux_rejet'])
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    st.subheader("Top 10 Clients a Risque")
    # Tri et affichage des 10 clients les plus a risque
    top_risques = df_f_clients.sort_values(by=['score_credit', 'taux_rejet'], ascending=[True, False]).head(10)
    
    # Fonction pour colorer les lignes selon le niveau de risque
    def color_risque(val):
        if val == 'Risqué': return 'background-color: #fecaca; color: #991b1b; font-weight: bold'
        elif val == 'Standard': return 'background-color: #fed7aa; color: #9a3412'
        return 'background-color: #bbf7d0; color: #166534'
    
    df_style = top_risques[['id_client', 'nom', 'score_credit', 'taux_rejet', 'categorie_risque']].style.map(color_risque, subset=['categorie_risque'])
    st.dataframe(df_style, use_container_width=True)
    
    # Bouton pour telecharger les donnees en format CSV
    st.download_button(
        label="Exporter la liste filtree (CSV)",
        data=top_risques.to_csv(index=False).encode('utf-8'),
        file_name='clients_risques_financecore.csv',
        mime='text/csv'
    )