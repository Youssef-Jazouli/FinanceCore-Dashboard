import pandas as pd
import streamlit as st

@st.cache_data
def load_data(_engine):
    """
    Extrait et prepare les donnees depuis PostgreSQL.
    Le tiret bas (_) devant engine empeche Streamlit de le hasher.
    """
    if _engine is None:
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        # Requete SQL pour les transactions
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
        df_trans = pd.read_sql(query_trans, _engine)
        
        # Traitement des dates
        df_trans['date_transaction'] = pd.to_datetime(df_trans['date_transaction'])
        df_trans['annee'] = df_trans['date_transaction'].dt.year
        df_trans['mois_annee'] = df_trans['date_transaction'].dt.to_period('M').astype(str)

        # Requete SQL pour analyser le risque
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
        df_clients = pd.read_sql(query_clients, _engine)
        
        # Calcul du taux de rejet
        df_clients['taux_rejet'] = (df_clients['nb_rejets'] / df_clients['nb_transactions']).fillna(0) * 100
        
        # Fonction pour definir le niveau de risque
        def categoriser_risque(score):
            if score < 400: return 'Risqué'
            elif score >= 400 and score < 700: return 'Standard'
            else: return 'Premium'
            
        df_clients['categorie_risque'] = df_clients['score_credit'].apply(categoriser_risque)
        
        return df_trans, df_clients
    except Exception as e:
        st.error(f"Erreur SQL : {e}")
        return pd.DataFrame(), pd.DataFrame()