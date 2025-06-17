import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import io
import os

# === Titre de l'App ===
st.set_page_config(page_title="Mon Projet Data")

# === Menu de navigation ===
menu = ["Accueil", "Dashboard", "Données brutes", "Rapport"]
choix = st.sidebar.selectbox("Sélectionnez une page", menu)

# === Fonction pour charger les données ===
@st.cache_data
def load_data():
    df = pd.read_csv("data/data.csv")  # Vérifie bien le chemin
    df['Quantite'] = 1
    df['TotalAmount'] = df['Prix_Produit'] * df['Quantite'] + df['Frais_Livraison']
    df['Date_Commande'] = pd.to_datetime(df['Date_Commande'], errors='coerce')
    df['Mois'] = df['Date_Commande'].dt.to_period('M').astype(str)
    return df

df = load_data()

# === Page d'accueil ===
if choix == "Accueil":
    st.title("Bienvenue dans l'application de visualisation des données")
    st.write("Cette app vous permet d'explorer les données de ventes et de visualiser les KPI clés.")

# === Filtrage (communs au Dashboard et Rapport) ===
st.sidebar.header("Filtrer par période")
date_debut = st.sidebar.date_input('Date de début', df['Date_Commande'].min().date())
date_fin = st.sidebar.date_input('Date de fin', df['Date_Commande'].max().date())
df_filtré = df[(df['Date_Commande'] >= pd.to_datetime(date_debut)) & (df['Date_Commande'] <= pd.to_datetime(date_fin))]

st.sidebar.header("Filtrer par catégorie")
categories_disponibles = df['Catégorie_Produit'].unique()
categorie_selectionnée = st.sidebar.selectbox('Choisir une catégorie', categories_disponibles)
df_filtré = df_filtré[df_filtré['Catégorie_Produit'] == categorie_selectionnée]

# === KPIs ===
nb_commandes = df_filtré.shape[0]
chiffre_affaires = df_filtré['TotalAmount'].sum()
panier_moyen = chiffre_affaires / nb_commandes if nb_commandes > 0 else 0

ca_par_mois = df_filtré.groupby('Mois')['TotalAmount'].sum().reset_index()
ca_par_categorie = df_filtré.groupby('Catégorie_Produit')['TotalAmount'].sum().reset_index()

fig1 = px.line(ca_par_mois, x='Mois', y='TotalAmount',
               title="Chiffre d'affaires par mois",
               labels={'Mois': 'Mois', 'TotalAmount': 'Chiffre d’affaires (€)'},
               markers=True)

fig2 = px.pie(ca_par_categorie, names='Catégorie_Produit', values='TotalAmount',
              title="Répartition du chiffre d’affaires par catégorie")

# === DASHBOARD ===
if choix == "Dashboard":
    st.title("Dashboard des KPI")
    st.subheader("Aperçu des données")
    st.dataframe(df_filtré.head())

    st.subheader("Indicateurs clés")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nombre de commandes", f"{nb_commandes:,}")
    col2.metric("Chiffre d'affaires", f"{chiffre_affaires:,.2f} €")
    col3.metric("Panier moyen", f"{panier_moyen:,.2f} €")

    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)

# === DONNÉES BRUTES ===
elif choix == "Données brutes":
    st.title("Données Brutes")
    st.dataframe(df.head())

# === FONCTION DE GENERATION DU PDF ===
def generate_pdf(df, ca_par_mois, ca_par_categorie):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # === Utiliser une police compatible Unicode ===
    font_path = "fonts/DejaVuSans.ttf"  # Assure-toi que ce chemin est bon
    if not os.path.exists(font_path):
        st.error("Police DejaVuSans.ttf manquante. Place-la dans le dossier 'fonts/'")
        return None

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 12)

    # === Titre du rapport ===
    pdf.cell(200, 10, txt="Rapport d'Analyse des Ventes", ln=True, align="C")
    pdf.ln(10)

    # === Résumé des KPIs ===
    total_ca = df['TotalAmount'].sum()
    nb_commandes = df.shape[0]
    panier_moyen = total_ca / nb_commandes if nb_commandes > 0 else 0

    pdf.cell(200, 10, txt="Résumé des KPIs :", ln=True)
    pdf.cell(200, 10, txt=f"Nombre de commandes : {nb_commandes:,}", ln=True)
    pdf.cell(200, 10, txt=f"Chiffre d'affaires total : {total_ca:,.2f} €", ln=True)
    pdf.cell(200, 10, txt=f"Panier moyen : {panier_moyen:,.2f} €", ln=True)
    pdf.ln(10)

    # === Graphique 1 ===
    fig1 = px.line(ca_par_mois, x='Mois', y='TotalAmount',
                   title="Chiffre d'Affaires par Mois", markers=True)
    fig1.write_image("ca_par_mois.png")
    pdf.image("ca_par_mois.png", x=10, w=180)
    pdf.ln(10)

    # === Graphique 2 ===
    fig2 = px.pie(ca_par_categorie, names='Catégorie_Produit', values='TotalAmount',
                  title="Répartition du Chiffre d'Affaires par Catégorie")
    fig2.write_image("ca_par_categorie.png")
    pdf.image("ca_par_categorie.png", x=10, w=180)
    pdf.ln(10)

    # === PDF en mémoire ===
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# === RAPPORT PDF ===
if choix == "Rapport":  # Ce bloc était mal indenté avant
    st.title("Rapport d'Analyse")
    st.write("Cliquez ci-dessous pour télécharger le rapport PDF.")

    pdf_file = generate_pdf(df_filtré, ca_par_mois, ca_par_categorie)

    if pdf_file:
        st.download_button(
            label="📄 Télécharger le rapport PDF",
            data=pdf_file,
            file_name="rapport_ventes.pdf",
            mime="application/pdf"
        )
