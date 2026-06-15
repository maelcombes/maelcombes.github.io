# ================================
# Il est peut-être nécessaire de faire un pip install
# - pip install mysql-connector
# ================================

#---------------ON IMPORTE LES LIBRAIRIES QUE L'ON A BESOIN POUR CE PROJET---------------

import mysql.connector
import csv
import pandas as pd
import tkinter
import datetime

#------------------------------ON SE CONNECTE A PHP MY ADMIN-----------------------------

db = mysql.connector.connect(host="127.0.0.1",user="root",password="",database="greensd-tda")
c = db.cursor(buffered=True)
    
#----------------------------------------------------------------------------------------
# NOUS AVONS FAIS LE CHOIX DE FAIRE LE NETTOYAGE DES DONNÉES A LA MAIN CAR NOUS NE SOMMES PAS TRÈS A L'AISE...
# ...AVEC L'UTILISATION DES FONCTIONS. 
# NOUS AVONS DONC EFFECTUÉ UN NETTOYAGE PLUS OPTIMAL SUIVANT LES DONNÉES NON CONFORMES.
#----------------------------------------------------------------------------------------

#----------------------------NETTOYAGE DU DATAFRAME LIVRAISON----------------------------

df_liv = pd.read_csv("livraison.csv", sep=";", encoding="ISO-8859-1")
df_liv["date_sortie"] = pd.to_datetime(df_liv["date_sortie"], format="%d/%m/%Y") 
df_liv["date_sortie"] = df_liv["date_sortie"].dt.strftime("%Y-%m-%d")
df_liv["client"] = df_liv["client"].str.replace("&", " and ").str.replace("Boulangerie du Centre ", "Boulangerie du centre ")
df_liv["ville_client"] = df_liv["ville_client"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.replace("Larochelle","La Rochelle")
df_liv["poids total"] = df_liv["poids total"].fillna("0").str.replace(r'\D+', '', regex=True).astype(float)
df_liv["véhicule"] = df_liv["véhicule"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.replace("Utilitaireelectrique","Utilitaire Electrique").str.replace("Tri Porteur","Triporteur")
df_liv["code_postal"] = df_liv["adresse_complete"].str.extract(r'(\d{5})')
df_liv["code_postal"] = df_liv["code_postal"].fillna("-")
df_liv["code_postal"] = df_liv["code_postal"].replace("-", None)
df_liv["adresse_complete"] = df_liv["adresse_complete"].str.replace("NIORT", "Niort")
df_liv["adresse"] = df_liv.apply(lambda x: str(x["adresse_complete"]).replace(str(x["code_postal"]), "").replace(str(x["ville_client"]), "").strip(),axis=1)
df_liv["adresse"] = df_liv["adresse"].str.replace(',', '').str.replace('-', '')
df_liv.drop(columns=["adresse_complete"], inplace = True)

#----------------------------NETTOYAGE DU DATAFRAME ENTRÉE-------------------------------

df_ent = pd.read_csv("entree.csv", sep=";", encoding="ISO-8859-1") 
df_ent["partenaire"] = df_ent["partenaire"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.replace("_"," ").str.replace("ô","o")
df_ent["date_entree"] = pd.to_datetime(df_ent["date_entree"], format="%d/%m/%Y")
df_ent["date_entree"] = df_ent["date_entree"].dt.strftime("%Y-%m-%d")

#----------------------------NETTOYAGE DU DATAFRAME VÉHICULE----------------------------

df_veh = pd.read_csv("vehicule_livreur.csv", sep=";", encoding="ISO-8859-1") 
df_veh["typeVeh"] = df_veh["typeVeh"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.replace("-"," ")
df_veh["typeVeh"] = df_veh["typeVeh"].fillna("-").str.replace("Utilitaireelectrique", "Utilitaire Electrique").astype(str)
df_veh["autonomie"] = df_veh["autonomie"].fillna("0").astype(float)
df_veh["capacite"] = df_veh["capacite"].fillna("0").astype(float)
df_veh["nb Vehicule"] = df_veh["nb Vehicule"].fillna("0").astype(int)
df_veh["nomLivreur"] = df_veh["nomLivreur"].fillna("-")
df_veh["nomLivreur"] = df_veh["nomLivreur"].str.strip().str.title().astype(str)
df_veh["prenomLivreur"] = df_veh["prenomLivreur"].fillna("-").astype(str)
df_veh["dateEmbauche"] = pd.to_datetime(df_veh["dateEmbauche"], format="%d/%m/%Y") 
df_veh["dateEmbauche"] = df_veh["dateEmbauche"].dt.strftime("%Y-%m-%d")
df_veh["dateEmbauche"] = df_veh["dateEmbauche"].fillna("-")

#----------------------------NETTOYAGE DU DATAFRAME TOURNEE----------------------------

df_tour = pd.read_csv("tournee.csv", sep=";", encoding="ISO-8859-1")
df_tour["dateTour"] = pd.to_datetime(df_tour["dateTour"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
df_tour["provenance2"] = df_tour["provenance2"].fillna("")
df_tour["provenance3"] = df_tour["provenance3"].fillna("")
df_tour["vehicule"] = df_tour["vehicule"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.strip()
df_tour["livreur"] = df_tour["livreur"].str.strip().str.title()
for col in ["provenance", "provenance1", "provenance2"]:
    if col in df_tour.columns:
        df_tour[[col+"_date", col+"_lieu"]] = df_tour[col].str.split(" - ", expand=True)
df_tour.drop(columns=["provenance1", "provenance2", "provenance3"], inplace=True)
for col in ["provenance1_date", "provenance2_date"]:
    df_tour[col] = pd.to_datetime(df_tour[col], format="%d/%m/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
df_tour["provenance2_date"] = df_tour["provenance2_date"].fillna("-")
df_tour["provenance2_lieu"] = df_tour["provenance2_lieu"].fillna("-")

#----------------------------NETTOYAGE DU DATAFRAME PARTENAIRE------------------------

df_par = pd.read_csv("partenaire.csv", sep=";", encoding="ISO-8859-1") 
df_par["ville"] = df_par["ville"].str.strip().str.title().str.replace(r"\d+", "", regex=True)
df_par["nomPartenaire"] = df_par["nomPartenaire"].str.strip().str.title().str.replace(r"\d+", "", regex=True).str.replace("ô","o")

#------------------CRÉATION D'UNE FONCTION QUI SUPPRIME LES DOUBLONS------------------

def doublons(table : pd.DataFrame, liste : list):
    poubelle = []
    for i in range(len(table)):
        for j in range(len(table)):
            if i < j :
                nb_conditions = 0
                for k in liste:
                    if table.iloc[i,k] == table.iloc[j,k]: 
                        nb_conditions += 1
                if nb_conditions == len(liste):
                    poubelle.append(i)
    table.drop(index = poubelle, inplace = True)

#---------------INSERTION DES DONNÉES DU DATAFRAME PARTENAIRE VERS PHP---------------

doublons(df_par, [0,1])
requete1 = """INSERT INTO partenaire (nom_partenaire, ville) VALUES (%s, %s)"""
for _, row in df_par.iterrows():
    valeurs1 = (row["nomPartenaire"], row["ville"])
    c.execute(requete1, valeurs1)

#----------------INSERTION DES DONNÉES DU DATAFRAME ENTREE VERS PHP---------------------

c.execute("SELECT nom_partenaire, id_partenaire FROM partenaire")
dict_par = {row[0]: row[1] for row in c.fetchall()}
df_ent["partenaire"] = df_ent["partenaire"].map(dict_par)
requete2 = """INSERT INTO entree (quantite_colis, date_entree, id_partenaire) VALUES (%s, %s, %s)"""
for _, row in df_ent.iterrows():
    valeurs2 = (row["quantite colis"], row["date_entree"], row["partenaire"])
    c.execute(requete2, valeurs2)

#---------------INSERTION DES DONNÉES DU DATAFRAME VEHICULE VERS PHP--------------------

requete3 = "INSERT INTO livreur (nom_livreur, prenom_livreur, date_embauche) VALUES (%s, %s, %s)"
for _, row in df_veh.iterrows():
    if row["nomLivreur"] != "-" and row["prenomLivreur"] != "-":
        c.execute(requete3, (row["nomLivreur"], row["prenomLivreur"], row["dateEmbauche"]))

requete4 = "INSERT INTO type_veh (libelle_type, autonomie_km, capacite_kg) VALUES (%s, %s, %s)"
id_types = []
for _, row in df_veh.iterrows():
    if row["typeVeh"] != "-" and row["autonomie"] > 0 and row["capacite"] > 0:
        c.execute(requete4, (row["typeVeh"], row["autonomie"], row["capacite"]))
        id_types.append(c.lastrowid)

for id_type in id_types:
    c.execute(
        "INSERT INTO vehicule (immatriculation, id_type_vehicule) VALUES (%s, %s)",
        ("__-___-__", id_type))

c.execute("SELECT id_type_vehicule, id_vehicule FROM vehicule")
dict_vehicule = {row[0]: row[1] for row in c.fetchall()}
        
#----------------INSERTION DES DONNÉES DU DATAFRAME TOURNEE VERS PHP--------------------        
        
c.execute("SELECT nom_livreur, id_livreur FROM livreur")
dict_liv = {row[0]: row[1] for row in c.fetchall()}
c.execute("SELECT libelle_type, id_type_vehicule FROM type_veh")
dict_veh = {row[0]: row[1] for row in c.fetchall()}

corrections_veh = {"Utilitaire Elec": "Utilitaire Electrique", "Velo Cargo": "Vélo Cargo", "Fourgon Elec": "Fourgon Electrique", "Moto Elec": "Moto Electrique", "Triporteur": "Triporteur"}
df_tour["vehicule"] = df_tour["vehicule"].replace(corrections_veh).map(dict_veh)
df_tour["livreur"] = df_tour["livreur"].map(dict_liv)
doublons(df_liv, [0,4,5])
for _, row in df_tour.iterrows():
    c.execute("INSERT INTO tournee (date_tour, distance_km, id_livreur, id_vehicule) VALUES (%s, %s, %s, %s)", 
              (row["dateTour"], row["autonomie"], row["livreur"], row["vehicule"]))

#---------------INSERTION DES DONNÉES DU DATAFRAME LIVRAISON VERS PHP------------------

requete5 = """INSERT INTO client (nom_client, adresse_client, ville_client, cp_client) VALUES (%s, %s, %s, %s)"""  
for _, row in df_liv.iterrows():
    cp = row["code_postal"]
    # Convertit NaN en None pour MySQL
    if pd.isna(cp) if not isinstance(cp, str) else cp in ["-", "nan", ""]:
        cp = None
    valeurs5 = (row["client"], row["adresse"], row["ville_client"], cp)
    c.execute(requete5, valeurs5)

requete6 = """INSERT INTO livraison (date_sortie, nb_colis, poids_total, id_tournee, id_client) 
VALUES (%s, %s, %s,
    (SELECT id_tournee FROM tournee 
     WHERE id_livreur = (SELECT id_livreur FROM livreur WHERE nom_livreur = %s LIMIT 1)
     AND DATE(date_tour) = DATE(%s)
     LIMIT 1),
    (SELECT id_client FROM client WHERE nom_client = %s LIMIT 1))"""

for _, row in df_liv.iterrows():
    valeurs6 = (row["date_sortie"], row["nb colis"], row["poids total"], row["livreur"], row["date_sortie"],  
     row["client"])
    c.execute(requete6, valeurs6)
    
#-------------------------GESTION DES CLÉS ÉTRANGÈRES DANS PHP-------------------------

c.execute("SELECT id_type_vehicule FROM type_veh ORDER BY id_type_vehicule DESC LIMIT 5")
ids_vehicule = [row[0] for row in c .fetchall()]

requete7 = "INSERT INTO polluer (id_type_vehicule, id_annee, co2_g_km) VALUES (%s, %s, %s)"
for id_veh in ids_vehicule:
    c.execute(requete7, (id_veh, "____", 0))

c.execute("SELECT id_livraison, poids_total, nb_colis FROM livraison ORDER BY id_livraison DESC LIMIT 4")
livraisons = list(reversed(c.fetchall()))

c.execute("SELECT id_entree FROM entree ORDER BY id_entree DESC LIMIT 4")
entrees = list(reversed([row[0] for row in c.fetchall()]))

requete = "INSERT INTO colis (poids, volume, id_entree, id_livraison) VALUES (%s, %s, %s, %s)"

for i, (id_livraison, poids_total, nb_colis) in enumerate(livraisons):
    if nb_colis and nb_colis > 0:
        poids_colis = round(poids_total / nb_colis, 2)
    else:
        poids_colis = None

    id_entree = entrees[i] if i < len(entrees) else None

    c.execute(requete, (poids_colis, None, id_entree, id_livraison))
   
#------------------------------------------------------------------------------------

db.commit()
c.close()
db.close()