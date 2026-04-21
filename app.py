import streamlit as st
import pandas as pd
import plotly.express as px

# Importation de nos modules personnalises
from modules.database import get_db_connection
from modules.processor import load_data

# Configuration de base de la page
st.set_page_config(page_title="FinanceCore Dashboard", layout="wide")

# 1. Connexion a la base de donnees via le module
engine = get_db_connection()

# 2. Chargement des donnees via le module
df_trans, df_clients = load_data(engine)

# Verification si les donnees sont vides
if df_trans.empty or df_clients.empty:
    st.warning("En attente des donnees de la base PostgreSQL...")
    st.stop()

# --- INTERFACE UTILISATEUR (UI) ---

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

# Creation des masques pour filtrer les donnees
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
        evo = df_f_trans.groupby(['mois_annee', 'type_transaction'])['montant'].sum().reset_index()
        fig_line = px.line(evo, x='mois_annee', y='montant', color='type_transaction', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.subheader("CA par Agence et par Produit")
        bar_data = df_f_trans[df_f_trans['type_transaction'] == 'Credit'].groupby(['agence', 'produit_bancaire'])['montant'].sum().reset_index()
        fig_bar = px.bar(bar_data, x='agence', y='montant', color='produit_bancaire', barmode='group', text_auto='.2s')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("Repartition des Clients par Segment")
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
        corr_matrix = df_f_clients[['score_credit', 'montant_total', 'taux_rejet']].corr()
        fig_heat = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_heat, width="stretch")
        
    with c2:
        st.subheader("Score Credit vs Montant Transaction")
        couleurs_risque = {'Risqué':'#ef4444', 'Standard':'#f97316', 'Premium':'#22c55e'}
        fig_scatter = px.scatter(df_f_clients, x='score_credit', y='montant_total', 
                                 color='categorie_risque', color_discrete_map=couleurs_risque,
                                 hover_data=['nom', 'taux_rejet'])
        st.plotly_chart(fig_scatter, width="stretch")
        
    st.subheader("Top 10 Clients a Risque")
    top_risques = df_f_clients.sort_values(by=['score_credit', 'taux_rejet'], ascending=[True, False]).head(10)
    
    def color_risque(val):
        if val == 'Risqué': return 'background-color: #fecaca; color: #991b1b; font-weight: bold'
        elif val == 'Standard': return 'background-color: #fed7aa; color: #9a3412'
        return 'background-color: #bbf7d0; color: #166534'
    
    df_style = top_risques[['id_client', 'nom', 'score_credit', 'taux_rejet', 'categorie_risque']].style.map(color_risque, subset=['categorie_risque'])
    st.dataframe(df_style, width="stretch")
    
    st.download_button(
        label="Exporter la liste filtree (CSV)",
        data=top_risques.to_csv(index=False).encode('utf-8'),
        file_name='clients_risques_financecore.csv',
        mime='text/csv'
    )