# -*- coding: utf-8 -*-
"""
Created on Sat Apr  4 18:30:30 2026

@author: boute
"""
# ================================
# Il est peut-être nécessaire de faire plusieurs pip install :
# - pip install requests
# - pip install mysql-connector
# ================================

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime
import os
import subprocess
import sys
import threading
import re

import json

# ================================
#        CONFIG COULEURS
# ================================
VERT_FONCE  = "#1e5631"
VERT_MOYEN  = "#2e8b57"
VERT_CLAIR  = "#b8e6c1"
BLANC       = "#ffffff"
GRIS        = "#f5f5f5"

# ================================
#          CONFIG GROQ
# ================================
GROQ_API_KEY = "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"
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

def build_system_prompt() -> str:
    schema_info = ""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        lines = []
        for table in tables:
            cursor.execute(f"DESCRIBE `{table}`")
            cols = cursor.fetchall()
            col_str = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
            lines.append(f"  - {table} : {col_str}")
        schema_info = "\n".join(lines)
        cursor.close()
        conn.close()
    except Exception as e:
        schema_info = f"  (erreur lors de la lecture du schéma : {e})"

    return (
        "Tu es un assistant expert en bases de données et en logistique verte, "
        "intégré dans l'application GreenSD.\n\n"
        "Voici le schéma EXACT et COMPLET de la base de données (tables et colonnes réelles) :\n"
        f"{schema_info}\n\n"
        "RÈGLES ABSOLUES :\n"
        "- Tu ne dois JAMAIS inventer ou supposer une table ou une colonne. "
        "Utilise UNIQUEMENT ce qui est listé ci-dessus.\n"
        "- Quand on te pose une question sur les données (ex : nombre de livreurs, liste des tournées...), "
        "trouve la bonne table dans le schéma ci-dessus et donne la requête SQL exacte avec le vrai nom de table.\n"
        "- Si tu ne trouves pas la table correspondante dans le schéma, dis-le clairement.\n"
        "- Réponds toujours en français, de manière concise et professionnelle.\n"
        "- IMPORTANT : les commandes SQL suivantes sont INTERDITES dans cette application : "
        "DELETE, DROP, TRUNCATE, ALTER, RENAME. Ne propose JAMAIS ces commandes dans tes réponses. "
        "Si on te demande de supprimer ou modifier la structure de la base, explique que c'est interdit "
        "et propose une alternative avec SELECT, INSERT ou UPDATE uniquement.\n\n"
        "MISE EN FORME :\n"
        "- Tu peux utiliser **texte** pour mettre en gras, __texte__ pour souligner, *texte* pour l'italique, "
        "et `code` pour les éléments de code ou noms de tables/colonnes. Ces balises seront rendues visuellement.\n\n"
        "GUIDE DE L'APPLICATION (onglets disponibles) :\n"
        "1. Accueil : présentation de GreenSD et accès aux fichiers CSV sources.\n"
        "2. Assistant IA : ce chatbot.\n"
        "3. Visualiser les tables : choisir une table dans le menu déroulant et cliquer sur 'Afficher' pour voir toutes ses données.\n"
        "4. Insertion/Modif/Supp : permet d'insérer, modifier ou supprimer des tuples dans une table.\n"
        "   - Charger une table : choisir la table dans le menu déroulant puis cliquer sur 'Charger'.\n"
        "   - Insérer : remplir les champs du formulaire (les champs * sont obligatoires, les champs 🔒 sont auto-générés) puis cliquer sur 'INSÉRER'.\n"
        "   - Modifier : cliquer sur une ligne du tableau pour la charger dans le formulaire, modifier les champs souhaités, puis cliquer sur 'MODIFIER'.\n"
        "   - Supprimer : cliquer sur une ligne du tableau pour la sélectionner, puis cliquer sur 'SUPPRIMER'. Une confirmation est demandée. Attention : les enregistrements liés par clé étrangère sont aussi supprimés.\n"
        "   - Vider : efface les champs du formulaire sans rien modifier en base.\n"
        "5. Requêtes SQL : saisir ou choisir une requête SQL parmi les exemples et cliquer sur 'Exécuter'. Seules SELECT, INSERT et UPDATE sont autorisées.\n"
        "6. Documents utiles : consulter et ouvrir les fichiers du projet (scripts Python, SQL)."
    )

def groq_chat(messages: list) -> str:
    try:
        import requests as _requests
    except ImportError:
        return (
            "[Erreur] Le module 'requests' n'est pas installé.\n"
            "Ouvrez un terminal et exécutez : pip install requests"
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        resp = _requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except _requests.exceptions.HTTPError as e:
        try:
            detail = resp.json()
            msg = detail.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return f"[Erreur HTTP {resp.status_code}] {msg}"
    except _requests.exceptions.ConnectionError:
        return "[Erreur réseau] Impossible de joindre l'API Groq. Vérifiez votre connexion internet."
    except _requests.exceptions.Timeout:
        return "[Erreur] La requête a expiré (timeout). Réessayez."
    except Exception as e:
        return f"[Erreur inattendue] {e}"


# ================================
#       CONNEXION MYSQL
# ================================
def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="greensd-tda"
    )

def get_table_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    cursor.close()
    conn.close()
    return tables

# ================================
#  RÉCUPÈRE LES INFOS DES COLONNES
# ================================
def get_columns_info(table_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COLUMN_NAME       AS name,
            DATA_TYPE         AS data_type,
            COLUMN_KEY        AS col_key,
            EXTRA             AS extra,
            IS_NULLABLE       AS is_nullable,
            CHARACTER_MAXIMUM_LENGTH AS max_length
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = %s
        ORDER BY ORDINAL_POSITION
    """, (table_name,))
    cols_raw = cursor.fetchall()

    cursor.execute("""
        SELECT
            kcu.COLUMN_NAME           AS col_name,
            kcu.REFERENCED_TABLE_NAME AS ref_table,
            kcu.REFERENCED_COLUMN_NAME AS ref_col
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
        JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
         AND tc.TABLE_SCHEMA    = kcu.TABLE_SCHEMA
         AND tc.TABLE_NAME      = kcu.TABLE_NAME
        WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
          AND kcu.TABLE_SCHEMA   = DATABASE()
          AND kcu.TABLE_NAME     = %s
    """, (table_name,))
    fk_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    fk_map = {r["col_name"]: r for r in fk_rows}

    columns = []
    for c in cols_raw:
        fk_info = fk_map.get(c["name"], {})
        columns.append({
            "name"       : c["name"],
            "data_type"  : c["data_type"].lower(),
            "is_pk"      : c["col_key"] == "PRI",
            "is_auto"    : "auto_increment" in (c["extra"] or "").lower(),
            "is_nullable": c["is_nullable"] == "YES",
            "max_length" : c["max_length"],
            "is_fk"      : bool(fk_info),
            "fk_table"   : fk_info.get("ref_table"),
            "fk_col"     : fk_info.get("ref_col"),
        })
    return columns

# ================================
#     VALIDATION D'UNE VALEUR
# ================================
INT_TYPES      = {"int", "tinyint", "smallint", "mediumint", "bigint"}
DECIMAL_TYPES  = {"decimal", "float", "double", "numeric"}
DATE_TYPES     = {"date"}
DATETIME_TYPES = {"datetime", "timestamp"}
STRING_TYPES   = {"varchar", "char", "text", "tinytext", "mediumtext", "longtext", "enum", "set"}

def validate_value(value, col_info):
    name     = col_info["name"]
    dtype    = col_info["data_type"]
    nullable = col_info["is_nullable"]
    max_len  = col_info["max_length"]

    if value.strip() == "":
        if nullable:
            return True, None
        return False, f"« {name} » est obligatoire (NOT NULL)."

    if dtype in INT_TYPES:
        try:
            return True, int(value)
        except ValueError:
            return False, f"« {name} » doit être un entier (ex : 42)."

    if dtype in DECIMAL_TYPES:
        try:
            return True, float(value.replace(",", "."))
        except ValueError:
            return False, f"« {name} » doit être un nombre décimal (ex : 3.14)."

    if dtype in DATE_TYPES:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                d = datetime.strptime(value.strip(), fmt)
                return True, d.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return False, f"« {name} » doit être une date (YYYY-MM-DD ou DD/MM/YYYY)."

    if dtype in DATETIME_TYPES:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                d = datetime.strptime(value.strip(), fmt)
                return True, d.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return False, (f"« {name} » doit être une date+heure "
                       "(YYYY-MM-DD HH:MM:SS ou DD/MM/YYYY HH:MM).")

    if dtype in STRING_TYPES:
        if max_len and len(value) > max_len:
            return False, (f"« {name} » dépasse la longueur maximale "
                           f"({len(value)}/{max_len} caractères).")
        return True, value

    return True, value


# ================================
#   OUVRE UN FICHIER CSV
# ================================
def open_csv_file(filepath, filename=""):
    from tkinter import filedialog
    if not os.path.isfile(filepath):
        rep = messagebox.askyesno(
            "Fichier introuvable",
            f"Le fichier « {filename or os.path.basename(filepath)} » est introuvable dans le dossier du script.\n\n"
            "Voulez-vous le localiser manuellement ?"
        )
        if rep:
            filepath = filedialog.askopenfilename(
                title=f"Localiser {filename or 'le fichier CSV'}",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
            )
            if not filepath:
                return
        else:
            return
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform.startswith("darwin"):
            subprocess.call(["open", filepath])
        else:
            subprocess.call(["xdg-open", filepath])
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier :\n{e}")


# ================================
#     APPLICATION TKINTER
# ================================
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application Gestion Base de Données")
        self.geometry("1200x750")
        self.configure(bg=GRIS)
        self._chat_history = [
            {"role": "system", "content": build_system_prompt()}
        ]
        self._chat_welcome_shown = False
        self.create_menu()
        self.create_main_frame()

    # ─── MENU ────────────────────────────────────────────────────
    def create_menu(self):
        self.menu_frame = tk.Frame(self, bg=VERT_FONCE, width=220)
        self.menu_frame.pack(side="left", fill="y")
        self.menu_frame.pack_propagate(False)

        logo_canvas = tk.Canvas(self.menu_frame, width=220, height=130,
                                bg=VERT_FONCE, highlightthickness=0,
                                cursor="hand2")
        logo_canvas.pack(pady=(30, 0))
        self._draw_logo(logo_canvas)
        logo_canvas.bind("<Button-1>", lambda e: self.page_accueil())

        center_frame = tk.Frame(self.menu_frame, bg=VERT_FONCE)
        center_frame.pack(fill="both", expand=True)

        tk.Label(center_frame, text="MENU", font=("Arial", 14, "bold"),
                 bg=VERT_FONCE, fg=BLANC).pack(pady=(20, 10))

        for text, cmd in [
            ("Accueil",               self.page_accueil),
            ("Assistant IA",          self.page_guide),
            ("Visualiser les tables", self.page_visualiser),
            ("Insertion/Modif/Supp",  self.page_crud),
            ("Requêtes SQL",          self.page_requete),
            ("Documents utiles",      self.page_documents),
        ]:
            btn = tk.Button(center_frame, text=text, font=("Arial", 13, "bold"),
                            bg=VERT_MOYEN, fg=BLANC,
                            activebackground=VERT_CLAIR,
                            activeforeground=BLANC,
                            relief="flat", command=cmd,
                            width=16)
            btn.pack(fill="x", padx=20, pady=2, expand=True, ipady=10)

        tk.Label(self.menu_frame, text="Made by\nMaël et Clément",
                 font=("Georgia", 9, "italic"), bg=VERT_FONCE, fg=BLANC,
                 justify="center").pack(side="bottom", pady=15)

    def _draw_logo(self, c):
        leaf_pts = [
            30, 118, 18, 90, 14, 65, 20, 45, 35, 28,
            55, 20, 72, 22, 82, 35, 84, 55, 78, 78,
            62, 98, 46, 112,
        ]
        c.create_polygon(leaf_pts, fill="#27500A", outline="#FFFFFF",
                         width=1, smooth=True)

        leaf2_pts = [
            36, 115, 24, 88, 22, 66, 28, 48, 42, 34,
            58, 26, 70, 30, 76, 46, 72, 68, 58, 90,
            44, 108,
        ]
        c.create_polygon(leaf2_pts, fill="#3B6D11", outline="", smooth=True)

        c.create_line(48, 112, 62, 28, fill="#FFFFFF", width=1,
                      smooth=True, capstyle="round")
        c.create_line(56, 90, 72, 72, fill="#FFFFFF", width=1,
                      capstyle="round", dash=(3, 3))
        c.create_line(54, 72, 72, 55, fill="#FFFFFF", width=1,
                      capstyle="round", dash=(3, 3))
        c.create_line(54, 55, 70, 40, fill="#FFFFFF", width=1,
                      capstyle="round", dash=(3, 3))

        c.create_rectangle(20, 95, 62, 116, fill="#173404",
                            outline="#FFFFFF", width=1)
        c.create_rectangle(56, 100, 78, 116, fill="#173404",
                            outline="#FFFFFF", width=1)
        c.create_rectangle(59, 103, 72, 111, fill="#FFFFFF", outline="")
        c.create_oval(26, 111, 38, 123, fill="#0a1f06",
                      outline="#FFFFFF", width=1)
        c.create_oval(30, 115, 34, 119, fill="#b8e6c1", outline="")
        c.create_oval(62, 111, 74, 123, fill="#0a1f06",
                      outline="#FFFFFF", width=1)
        c.create_oval(66, 115, 70, 119, fill="#b8e6c1", outline="")

        c.create_text(140, 42, text="green", anchor="center",
                      font=("Georgia", 20, "bold italic"), fill="#FFFFFF")
        c.create_text(140, 76, text="SD", anchor="center",
                      font=("Courier", 26, "bold"), fill="#F5F5F0")
        c.create_line(100, 92, 185, 92, fill="#b8e6c1", width=1)
        c.create_text(140, 106, text="logistique verte", anchor="center",
                      font=("Georgia", 8, "italic"), fill="#FFFFFF")

    # ─── FRAME PRINCIPAL ─────────────────────────────────────────
    def create_main_frame(self):
        self.main_frame = tk.Frame(self, bg=BLANC)
        self.main_frame.pack(side="right", fill="both", expand=True)
        self.page_accueil()

    def clear_main(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    # ─── PAGE ACCUEIL ────────────────────────────────────────────
    def page_accueil(self):
        self.clear_main()

        # ── Scroll vertical sur toute la page ──────────────────────
        outer = tk.Frame(self.main_frame, bg=BLANC)
        outer.pack(fill="both", expand=True)

        v_scroll = tk.Scrollbar(outer, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        page_canvas = tk.Canvas(outer, bg=BLANC, highlightthickness=0,
                                yscrollcommand=v_scroll.set)
        page_canvas.pack(side="left", fill="both", expand=True)
        v_scroll.config(command=page_canvas.yview)

        page_frame = tk.Frame(page_canvas, bg=BLANC)
        page_win = page_canvas.create_window((0, 0), window=page_frame, anchor="nw")

        def _on_page_configure(event=None):
            page_canvas.configure(scrollregion=page_canvas.bbox("all"))
        def _on_canvas_resize(event=None):
            page_canvas.itemconfig(page_win, width=event.width)

        page_frame.bind("<Configure>", _on_page_configure)
        page_canvas.bind("<Configure>", _on_canvas_resize)

        # Scroll à la molette
        def _on_mousewheel(event):
            page_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        page_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── Contenu dans page_frame ────────────────────────────────
        tk.Label(page_frame, text="Bienvenue dans l'application",
                 font=("Arial", 28, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=40)

        intro_frame = tk.Frame(page_frame, bg=BLANC)
        intro_frame.pack(fill="x", padx=40, pady=10)
        intro_text = tk.Text(intro_frame, wrap="word", font=("Arial", 12),
                             bg=BLANC, relief="flat",
                             spacing1=4, spacing3=4, height=12)
        intro_text.pack(fill="both")

        intro_text.tag_configure("bold", font=("Arial", 12, "bold"))
        intro_text.tag_configure("bullet", lmargin1=20, lmargin2=30)

        intro_text.insert("end", "GreenSD", "bold")
        intro_text.insert("end", " est une entreprise de transport et de logistique spécialisée dans la livraison bas-carbone en zone urbaine et dans l'utilisation de véhicules électriques et vélos-cargo.\n\n")
        intro_text.insert("end", "L'entreprise voulait optimiser ses tournées de livraison de marchandises et le suivi de l'empreinte carbone par colis. Elle souhaitait informatiser et centraliser la gestion de ses flux logistiques.\n\n")
        intro_text.insert("end", "En effet, l'entreprise voulait suivre :\n")
        for b in [
            "les livraisons entrantes venant des entrepôts partenaires vers l'entrepôt de l'entreprise,",
            "les livraisons sortantes vers les clients finaux via des colis transportés,",
            "les véhicules écologiques utilisés (type, autonomie en km, capacité en kg),",
            "les tournées (trajets journaliers),",
            "les conducteurs-livreurs et leurs affectations aux tournées,",
            "les émissions CO2 estimées, calculées selon des coefficients fournis chaque année.",
        ]:
            intro_text.insert("end", f"  •  {b}\n", "bullet")
        intro_text.insert("end", "\n")
        intro_text.insert("end", "Les données réelles de l'activité 2026", "bold")
        intro_text.insert("end", " sont stockées dans 5 fichiers CSV extraits d'un logiciel métier et sont consultables ci-dessous ! Ces données étaient en vrac, imparfaites et donc très mal structurées. Elles ont nécessité un nettoyage et une réorganisation avant d'être stockées dans une base de données relationnelles.\n\n")
        intro_text.config(state="disabled")

        csv_section = tk.Frame(page_frame, bg=BLANC)
        csv_section.pack(fill="x", padx=40, pady=(0, 30))

        tk.Label(csv_section, text="Fichiers CSV disponibles",
                 font=("Arial", 14, "bold"), fg=VERT_FONCE, bg=BLANC).pack(anchor="w", pady=(0, 8))

        sep = tk.Frame(csv_section, bg=VERT_CLAIR, height=2)
        sep.pack(fill="x", pady=(0, 12))

        # Canvas scrollable horizontalement pour grands écrans
        wrapper = tk.Frame(csv_section, bg=BLANC)
        wrapper.pack(fill="both", expand=True)

        h_scroll = tk.Scrollbar(wrapper, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        scroll_canvas = tk.Canvas(wrapper, bg=BLANC, highlightthickness=0,
                                  xscrollcommand=h_scroll.set)
        scroll_canvas.pack(side="top", fill="both", expand=True)
        h_scroll.config(command=scroll_canvas.xview)

        csv_grid = tk.Frame(scroll_canvas, bg=BLANC)
        win_id = scroll_canvas.create_window((0, 0), window=csv_grid, anchor="nw")

        def _update_scroll(event=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            grid_w = csv_grid.winfo_reqwidth()
            canvas_w = scroll_canvas.winfo_width()
            x = max(0, (canvas_w - grid_w) // 2)
            scroll_canvas.coords(win_id, x, 4)

        csv_grid.bind("<Configure>", _update_scroll)
        scroll_canvas.bind("<Configure>", _update_scroll)

        base_dir = os.path.dirname(os.path.abspath(__file__))

        csv_files = [
            ("livraison",        "livraison.csv"),
            ("entree",           "entree.csv"),
            ("partenaire",       "partenaire.csv"),
            ("vehicule livreur", "vehicule_livreur.csv"),
            ("tournee",          "tournee.csv"),
        ]

        for i, (label, filename) in enumerate(csv_files):
            filepath = os.path.join(base_dir, filename)

            card = tk.Frame(csv_grid, bg=GRIS, bd=0,
                            highlightthickness=2,
                            highlightbackground=VERT_CLAIR)
            card.grid(row=0, column=i, padx=12, pady=8,
                      ipadx=16, ipady=8, sticky="n")

            icon_c = tk.Canvas(card, width=64, height=74,
                               bg=GRIS, highlightthickness=0)
            icon_c.pack(pady=(14, 6))
            icon_c.create_rectangle(6, 0, 58, 74, fill="#e8f5e9",
                                    outline=VERT_MOYEN, width=2)
            icon_c.create_polygon(42, 0, 58, 0, 58, 18,
                                  fill=VERT_MOYEN, outline="")
            icon_c.create_polygon(42, 0, 42, 18, 58, 18,
                                  fill="#c8e6c9", outline=VERT_MOYEN, width=1)
            icon_c.create_text(32, 50, text="CSV",
                               font=("Arial", 16, "bold"), fill=VERT_FONCE)

            tk.Label(card, text=label, font=("Arial", 14, "bold"),
                     fg=VERT_FONCE, bg=GRIS).pack()
            tk.Label(card, text=".csv", font=("Arial", 11),
                     fg="#888888", bg=GRIS).pack(pady=(2, 8))

            btn = tk.Button(card, text="📂  Ouvrir",
                            bg=VERT_MOYEN, fg=BLANC,
                            font=("Arial", 12, "bold"), relief="flat",
                            cursor="hand2",
                            command=lambda p=filepath, n=filename: open_csv_file(p, n))
            btn.pack(padx=16, pady=(4, 14), fill="x", ipady=8)

            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=VERT_FONCE))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=VERT_MOYEN))

    # ─── PAGE VISUALISER ─────────────────────────────────────────
    def page_visualiser(self):
        self.clear_main()
        tk.Label(self.main_frame, text="Visualisation des tables",
                 font=("Arial", 24, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=20)

        top = tk.Frame(self.main_frame, bg=BLANC)
        top.pack(pady=10)
        tk.Label(top, text="Choisissez une table :", bg=BLANC,
                 font=("Arial", 12)).pack(side="left", padx=10)
        self.table_choice = ttk.Combobox(top, values=get_table_list(),
                                         state="readonly", width=25)
        self.table_choice.pack(side="left", padx=10)
        tk.Button(top, text="Afficher", bg=VERT_MOYEN, fg=BLANC,
                  relief="flat", command=self.load_table).pack(side="left", padx=10)

        self.table_frame = tk.Frame(self.main_frame, bg=BLANC)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def load_table(self):
        table = self.table_choice.get()
        if not table:
            return
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        cursor.close(); conn.close()

        for w in self.table_frame.winfo_children():
            w.destroy()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Visualiser.Treeview.Heading",
                        background=VERT_FONCE, foreground=BLANC,
                        font=("Arial", 10, "bold"), relief="flat", padding=6)
        style.map("Visualiser.Treeview.Heading",
                  background=[("active", VERT_MOYEN)])
        style.configure("Visualiser.Treeview",
                        font=("Arial", 10), rowheight=28, borderwidth=0)
        style.map("Visualiser.Treeview",
                  background=[("selected", VERT_MOYEN)],
                  foreground=[("selected", BLANC)])

        tree = ttk.Treeview(self.table_frame, columns=cols,
                            show="headings", style="Visualiser.Treeview")
        tree.pack(fill="both", expand=True, side="left")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")

        tree.tag_configure("pair",   background="#e8f5e9")
        tree.tag_configure("impair", background=BLANC)

        for i, row in enumerate(rows):
            tag = "pair" if i % 2 == 0 else "impair"
            tree.insert("", "end", values=row, tags=(tag,))

        sb = ttk.Scrollbar(self.table_frame, command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

    # ─── PAGE CRUD ───────────────────────────────────────────────
    def page_crud(self):
        self.clear_main()
        self.crud_cols_info  = []
        self.crud_entry_vars = {}

        tk.Label(self.main_frame,
                 text="Insertion / Modification / Suppression",
                 font=("Arial", 22, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=20)

        choose = tk.Frame(self.main_frame, bg=BLANC)
        choose.pack(pady=10)
        tk.Label(choose, text="Table :", bg=BLANC,
                 font=("Arial", 12)).pack(side="left", padx=10)
        self.crud_table_choice = ttk.Combobox(choose, values=get_table_list(),
                                               state="readonly", width=25)
        self.crud_table_choice.pack(side="left", padx=10)
        tk.Button(choose, text="Charger", bg=VERT_MOYEN, fg=BLANC,
                  relief="flat", command=self.load_crud_table).pack(side="left", padx=10)

        self.crud_table_frame  = tk.Frame(self.main_frame, bg=BLANC)
        self.crud_table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.crud_fields_frame = tk.Frame(self.main_frame, bg=BLANC)
        self.crud_fields_frame.pack(pady=10)

    def load_crud_table(self):
        table = self.crud_table_choice.get()
        if not table:
            return

        self.crud_cols_info = get_columns_info(table)

        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        cursor.close(); conn.close()

        for w in self.crud_table_frame.winfo_children():
            w.destroy()
        for w in self.crud_fields_frame.winfo_children():
            w.destroy()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Crud.Treeview.Heading",
                        background=VERT_FONCE, foreground=BLANC,
                        font=("Arial", 10, "bold"), relief="flat", padding=6)
        style.map("Crud.Treeview.Heading",
                  background=[("active", VERT_MOYEN)])
        style.configure("Crud.Treeview",
                        font=("Arial", 10), rowheight=28, borderwidth=0)
        style.map("Crud.Treeview",
                  background=[("selected", VERT_MOYEN)],
                  foreground=[("selected", BLANC)])

        self.crud_tree = ttk.Treeview(self.crud_table_frame,
                                       columns=cols, show="headings",
                                       height=10, style="Crud.Treeview")
        self.crud_tree.pack(side="left", fill="both", expand=True)

        for col in cols:
            self.crud_tree.heading(col, text=col)
            self.crud_tree.column(col, width=120, anchor="center")

        self.crud_tree.tag_configure("pair",   background="#e8f5e9")
        self.crud_tree.tag_configure("impair", background=BLANC)

        for i, row in enumerate(rows):
            tag = "pair" if i % 2 == 0 else "impair"
            self.crud_tree.insert("", "end", values=row, tags=(tag,))

        sb = ttk.Scrollbar(self.crud_table_frame, command=self.crud_tree.yview)
        sb.pack(side="right", fill="y")
        self.crud_tree.configure(yscrollcommand=sb.set)
        self.crud_tree.bind("<<TreeviewSelect>>", self.populate_fields)

        tk.Label(self.crud_fields_frame, text="Édition du tuple",
                 bg=BLANC, font=("Arial", 16, "bold")).pack()

        tk.Label(self.crud_fields_frame,
                 text="🔒 = clé primaire auto (non modifiable)  |  * = obligatoire  |  FK = clé étrangère",
                 bg=BLANC, font=("Arial", 9), fg="gray").pack()

        self.crud_entry_vars = {}

        form_and_btns = tk.Frame(self.crud_fields_frame, bg=BLANC)
        form_and_btns.pack(pady=8)

        form = tk.Frame(form_and_btns, bg=BLANC)
        form.pack(side="left", padx=(0, 20))

        for i, ci in enumerate(self.crud_cols_info):
            label_text = ci["name"]
            if ci["is_auto"]:
                label_text += "  🔒"
            elif not ci["is_nullable"]:
                label_text += "  *"
            if ci["is_fk"]:
                label_text += f"  (FK→{ci['fk_table']})"

            type_hint = f"[{ci['data_type']}]"
            if ci["data_type"] in DATE_TYPES:
                type_hint = "[date: YYYY-MM-DD]"
            elif ci["data_type"] in DATETIME_TYPES:
                type_hint = "[datetime: YYYY-MM-DD HH:MM:SS]"
            elif ci["data_type"] in DECIMAL_TYPES:
                type_hint = "[décimal]"
            elif ci["data_type"] in INT_TYPES:
                type_hint = "[entier]"
            elif ci["max_length"]:
                type_hint = f"[texte max {ci['max_length']}]"

            tk.Label(form, text=label_text, bg=BLANC,
                     font=("Arial", 10, "bold")).grid(row=i, column=0,
                                                       sticky="w", padx=10, pady=3)
            tk.Label(form, text=type_hint, bg=BLANC,
                     font=("Arial", 9), fg="#555").grid(row=i, column=1,
                                                         sticky="w", padx=4, pady=3)

            var = tk.StringVar()
            self.crud_entry_vars[ci["name"]] = var

            state = "disabled" if ci["is_auto"] else "normal"
            bg    = "#ddd" if ci["is_auto"] else GRIS
            tk.Entry(form, textvariable=var, bg=bg, state=state,
                     width=28).grid(row=i, column=2, padx=10, pady=3)

        btn_frame = tk.Frame(form_and_btns, bg=BLANC)
        btn_frame.pack(side="left", anchor="center", padx=20)

        for txt, cmd, color in [
            ("INSÉRER",   self.crud_insert, VERT_MOYEN),
            ("MODIFIER",  self.crud_update, VERT_MOYEN),
            ("SUPPRIMER", self.crud_delete, "#a83232"),
        ]:
            tk.Button(btn_frame, text=txt, bg=color, fg=BLANC,
                      font=("Arial", 11), width=12, relief="flat",
                      command=cmd).pack(pady=6, ipady=6)

    def populate_fields(self, event):
        selected = self.crud_tree.selection()
        if not selected:
            return
        values = self.crud_tree.item(selected[0], "values")
        for ci, val in zip(self.crud_cols_info, values):
            var = self.crud_entry_vars.get(ci["name"])
            if var is None:
                continue
            entry_widget = self._get_entry_widget(ci["name"])
            if ci["is_auto"] and entry_widget:
                entry_widget.config(state="normal")
                var.set(val)
                entry_widget.config(state="disabled")
            else:
                var.set(val)

    def _get_entry_widget(self, col_name):
        for frame in self.crud_fields_frame.winfo_children():
            if isinstance(frame, tk.Frame):
                for child in frame.winfo_children():
                    if isinstance(child, tk.Entry):
                        var = child.cget("textvariable")
                        if var == str(self.crud_entry_vars.get(col_name)):
                            return child
        return None

    def clear_fields(self):
        for ci in self.crud_cols_info:
            var = self.crud_entry_vars.get(ci["name"])
            if var:
                w = self._get_entry_widget(ci["name"])
                if ci["is_auto"] and w:
                    w.config(state="normal")
                    var.set("")
                    w.config(state="disabled")
                else:
                    var.set("")

    def _validate_form(self, skip_auto=False):
        values = {}
        for ci in self.crud_cols_info:
            if skip_auto and ci["is_auto"]:
                continue
            raw = self.crud_entry_vars[ci["name"]].get()
            ok, result = validate_value(raw, ci)
            if not ok:
                messagebox.showerror("Erreur de saisie", result)
                return False, None
            values[ci["name"]] = result
        return True, values

    def _check_doublon(self, table, values, exclude_pk_col=None, exclude_pk_value=None):
        if not values:
            return False
        cols_list = list(values.keys())
        vals_list = list(values.values())
        where_clause = " AND ".join([f"{c} <=> %s" for c in cols_list])
        sql = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        params = vals_list
        if exclude_pk_col and exclude_pk_value is not None:
            sql += f" AND {exclude_pk_col} != %s"
            params = vals_list + [exclude_pk_value]
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            count = cursor.fetchone()[0]
            cursor.close(); conn.close()
            return count > 0
        except mysql.connector.Error:
            return False

    def crud_insert(self):
        table = self.crud_table_choice.get()
        if not table:
            return
        ok, values = self._validate_form(skip_auto=True)
        if not ok:
            return

        if self._check_doublon(table, values):
            messagebox.showwarning(
                "Doublon détecté",
                "Un tuple identique existe déjà dans la table.\nInsertion annulée."
            )
            return

        cols_list = list(values.keys())
        vals_list = list(values.values())
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            sql = (f"INSERT INTO {table} ({', '.join(cols_list)}) "
                   f"VALUES ({', '.join(['%s'] * len(cols_list))})")
            cursor.execute(sql, vals_list)
            conn.commit()
            new_id = cursor.lastrowid
            cursor.close(); conn.close()
            messagebox.showinfo("Succès", f"Tuple inséré avec succès (ID={new_id}).")
            self.load_crud_table()
        except mysql.connector.Error as e:
            messagebox.showerror("Erreur MySQL", str(e))

    def crud_update(self):
        table = self.crud_table_choice.get()
        if not table:
            return
        pk_col  = next((ci for ci in self.crud_cols_info if ci["is_pk"]), None)
        if pk_col is None:
            messagebox.showerror("Erreur", "Aucune clé primaire détectée.")
            return
        pk_raw = self.crud_entry_vars[pk_col["name"]].get()
        if pk_raw.strip() == "":
            messagebox.showwarning("Attention",
                                   "Sélectionnez d'abord un tuple dans le tableau.")
            return
        ok_pk, pk_value = validate_value(pk_raw, pk_col)
        if not ok_pk:
            messagebox.showerror("Erreur de saisie", pk_value)
            return
        values = {}
        for ci in self.crud_cols_info:
            if ci["is_pk"]:
                continue
            raw = self.crud_entry_vars[ci["name"]].get()
            ok, result = validate_value(raw, ci)
            if not ok:
                messagebox.showerror("Erreur de saisie", result)
                return
            values[ci["name"]] = result
        if not values:
            messagebox.showinfo("Info", "Aucune colonne à mettre à jour.")
            return

        if self._check_doublon(table, values,
                               exclude_pk_col=pk_col["name"],
                               exclude_pk_value=pk_value):
            messagebox.showwarning(
                "Doublon détecté",
                "Un tuple identique existe déjà dans la table.\nModification annulée."
            )
            return

        set_clause = ", ".join([f"{c} = %s" for c in values])
        vals_list  = list(values.values()) + [pk_value]
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col['name']} = %s"
            cursor.execute(sql, vals_list)
            conn.commit()
            affected = cursor.rowcount
            cursor.close(); conn.close()
            if affected == 0:
                messagebox.showwarning("Attention", "Aucun tuple modifié (ID introuvable ?).")
            else:
                messagebox.showinfo("Succès", "Tuple modifié avec succès.")
            self.load_crud_table()
        except mysql.connector.Error as e:
            messagebox.showerror("Erreur MySQL", str(e))

    def crud_delete(self):
        table = self.crud_table_choice.get()
        if not table:
            return
        pk_col = next((ci for ci in self.crud_cols_info if ci["is_pk"]), None)
        if pk_col is None:
            messagebox.showerror("Erreur", "Aucune clé primaire détectée.")
            return
        pk_raw = self.crud_entry_vars[pk_col["name"]].get()
        if pk_raw.strip() == "":
            messagebox.showwarning("Attention",
                                   "Sélectionnez d'abord un tuple dans le tableau.")
            return
        ok, pk_value = validate_value(pk_raw, pk_col)
        if not ok:
            messagebox.showerror("Erreur", ok)
            return
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT kcu.TABLE_NAME AS child_table,
                   kcu.COLUMN_NAME AS child_col
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
              ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
             AND tc.TABLE_SCHEMA    = kcu.TABLE_SCHEMA
             AND tc.TABLE_NAME      = kcu.TABLE_NAME
            WHERE tc.CONSTRAINT_TYPE        = 'FOREIGN KEY'
              AND kcu.TABLE_SCHEMA          = DATABASE()
              AND kcu.REFERENCED_TABLE_NAME = %s
              AND kcu.REFERENCED_COLUMN_NAME = %s
        """, (table, pk_col["name"]))
        children = cursor.fetchall()
        cursor.close()
        conn.close()
        msg = f"Supprimer le tuple {pk_col['name']} = {pk_value} ?"
        if children:
            tables_str = ", ".join(set(c["child_table"] for c in children))
            msg += f"\n\nAttention : les enregistrements liés dans les tables suivantes seront aussi supprimés :\n{tables_str}"
        confirm = messagebox.askyesno("Confirmation", msg)
        if not confirm:
            return
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for child in children:
                cursor.execute(
                    f"DELETE FROM {child['child_table']} WHERE {child['child_col']} = %s",
                    (pk_value,)
                )
            cursor.execute(
                f"DELETE FROM {table} WHERE {pk_col['name']} = %s",
                (pk_value,)
            )
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Succès", "Tuple supprimé avec toutes ses dépendances.")
            self.load_crud_table()
        except mysql.connector.Error as e:
            try:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                conn.commit()
                cursor.close()
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Erreur MySQL", str(e))

    # ─── PAGE REQUÊTE SQL ────────────────────────────────────────
    def page_requete(self):
        self.clear_main()
        tk.Label(self.main_frame, text="Requêtes SQL",
                 font=("Arial", 22, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=(20, 5))

        examples_outer = tk.Frame(self.main_frame, bg=BLANC)
        examples_outer.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(examples_outer, text="Exemples de requêtes :",
                 font=("Arial", 12, "bold"), fg=VERT_FONCE, bg=BLANC).pack(anchor="w", pady=(15, 6))

        scroll_wrapper = tk.Frame(examples_outer, bg=BLANC)
        scroll_wrapper.pack(fill="x")

        examples_canvas = tk.Canvas(scroll_wrapper, bg=BLANC, height=110,
                                    highlightthickness=0)
        examples_canvas.pack(fill="x")

        h_scroll_spacer_top = tk.Frame(scroll_wrapper, bg=BLANC, height=10)
        h_scroll_spacer_top.pack(fill="x")

        h_scroll = tk.Scrollbar(scroll_wrapper, orient="horizontal",
                                command=examples_canvas.xview)
        h_scroll.pack(fill="x")

        h_scroll_spacer_bot = tk.Frame(scroll_wrapper, bg=BLANC, height=10)
        h_scroll_spacer_bot.pack(fill="x")

        examples_canvas.configure(xscrollcommand=h_scroll.set)

        btns_frame = tk.Frame(examples_canvas, bg=BLANC)
        examples_canvas.create_window((0, 0), window=btns_frame, anchor="nw")

        EXEMPLES = [
            ("1 · Livraisons\npar livreur",
             "SELECT nom_livreur, prenom_livreur, COUNT(*) AS nb_livraisons\nFROM livreur, tournee, livraison\nWHERE tournee.id_livreur = livreur.id_livreur AND livraison.id_tournee = tournee.id_tournee\nGROUP BY nom_livreur, prenom_livreur\nORDER BY nb_livraisons DESC;"),
            ("2 · Clients\n> 10 colis",
             "SELECT nom_client, ville_client, SUM(nb_colis) AS total_colis\nFROM client, livraison\nWHERE livraison.id_client = client.id_client\nGROUP BY nom_client, ville_client\nHAVING SUM(nb_colis) > 10\nORDER BY total_colis DESC;"),
            ("3 · Créer vue\ntournées",
             "CREATE OR REPLACE VIEW vue_tournees AS\nSELECT tournee.id_tournee, tournee.date_tour, tournee.distance_km, livreur.nom_livreur, livreur.prenom_livreur, type_veh.libelle_type AS type_vehicule\nFROM tournee, livreur, vehicule, type_veh\nWHERE livreur.id_livreur = tournee.id_livreur AND vehicule.id_vehicule = tournee.id_vehicule AND type_veh.id_type_vehicule = vehicule.id_type_vehicule;"),
            ("4 · Distance\npar véhicule",
             "SELECT type_vehicule, COUNT(*) AS nb_tournees, SUM(distance_km) AS km_total\nFROM vue_tournees\nGROUP BY type_vehicule\nORDER BY km_total DESC;"),
            ("5 · Livreurs sans\ntournée",
             "SELECT nom_livreur, prenom_livreur\nFROM livreur\nWHERE id_livreur NOT IN (SELECT id_livreur FROM tournee);"),
            ("6 · Ajout\npartenaire",
             "INSERT INTO partenaire (nom_partenaire, ville)\nVALUES ('Ferme Bio des Landes', 'Mont-de-Marsan');"),
            ("7 · Corriger\nadresse client",
             "UPDATE client\nSET adresse_client = '12 Rue des Pyrénées', cp_client = '64000', ville_client = 'Pau'\nWHERE nom_client = 'Boulangerie du centre';"),
            ("8 · Suppr. entrées\nsans partenaire",
             "DELETE FROM entree\nWHERE id_partenaire IS NULL;"),
            ("9 · Tournées\n> 100 km",
             "SELECT date_tour, nom_livreur, prenom_livreur, type_vehicule, distance_km\nFROM vue_tournees\nWHERE distance_km > 100\nORDER BY distance_km DESC;"),
            ("10 · Colis par\npartenaire",
             "SELECT partenaire.nom_partenaire, partenaire.ville, COUNT(*) AS nb_entrees, SUM(quantite_colis) AS total_colis_envoyes\nFROM partenaire, entree\nWHERE entree.id_partenaire = partenaire.id_partenaire\nGROUP BY partenaire.nom_partenaire, partenaire.ville;"),
        ]

        for label, sql in EXEMPLES:
            card = tk.Frame(btns_frame, bg=GRIS,
                            highlightthickness=1, highlightbackground=VERT_CLAIR)
            card.pack(side="left", padx=6, pady=4, ipadx=4, ipady=4)
            btn = tk.Button(card, text=label, font=("Arial", 9, "bold"),
                            bg=GRIS, fg=VERT_FONCE, relief="flat",
                            cursor="hand2", justify="center", width=13,
                            command=lambda q=sql: self._charger_exemple(q))
            btn.pack(padx=6, pady=6)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=VERT_CLAIR))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=GRIS))

        btns_frame.update_idletasks()
        examples_canvas.configure(scrollregion=examples_canvas.bbox("all"))

        top = tk.Frame(self.main_frame, bg=BLANC)
        top.pack(fill="x", padx=20)
        tk.Label(top, text="Saisissez votre requête SQL :",
                 font=("Arial", 12, "bold"), bg=BLANC).pack(anchor="w", pady=(0, 5))
        self.sql_entry = tk.Text(top, height=5, font=("Courier", 11),
                                 bg=GRIS, relief="flat", wrap="word")
        self.sql_entry.pack(fill="x")

        tk.Button(self.main_frame, text="Exécuter", bg=VERT_MOYEN, fg=BLANC,
                  font=("Arial", 11, "bold"), relief="flat",
                  command=self.run_requete).pack(pady=10)

        # ── Frame résultat sans aucune bordure visible ────────────
        self.sql_result_frame = tk.Frame(self.main_frame, bg=BLANC,
                                         highlightthickness=0, bd=0,
                                         relief="flat")
        self.sql_result_frame.pack(fill="both", expand=True, padx=20, pady=10)

    def _charger_exemple(self, sql):
        self.sql_entry.delete("1.0", "end")
        self.sql_entry.insert("1.0", sql)

    def run_requete(self):
        query = self.sql_entry.get("1.0", "end").strip()
        if not query:
            return

        for w in self.sql_result_frame.winfo_children():
            w.destroy()

        mots_interdits = ["delete", "drop", "truncate", "alter", "rename"]
        premier_mot = query.split()[0].lower() if query.split() else ""
        if premier_mot in mots_interdits:
            msg = f"Commande {premier_mot.upper()} interdite. Seules SELECT, INSERT et UPDATE sont autorisées pour des raisons de sécurité de notre base de données."
            tk.Label(self.sql_result_frame, text=msg,
                     font=("Arial", 12, "bold"), fg="#a83232", bg=BLANC,
                     wraplength=800, justify="left").pack(pady=20)
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            if cursor.description:
                cols = [d[0] for d in cursor.description]
                rows = cursor.fetchall()

                # ── Style épuré sans bordures grises ─────────────
                style = ttk.Style()
                style.theme_use("default")

                style.configure("Green.Treeview",
                                background=BLANC,
                                foreground="#222222",
                                rowheight=30,
                                fieldbackground=BLANC,
                                font=("Arial", 10),
                                borderwidth=0,
                                relief="flat")

                style.configure("Green.Treeview.Heading",
                                background=VERT_FONCE,
                                foreground=BLANC,
                                font=("Arial", 13, "bold"),
                                borderwidth=0,
                                relief="flat",
                                padding=(0, 10))

                style.map("Green.Treeview.Heading",
                          background=[('active', VERT_FONCE)])

                style.layout("Green.Treeview", [
                    ('Treeview.treearea', {'sticky': 'nswe'})
                ])

                # Conteneur interne sans bordure
                tree_container = tk.Frame(self.sql_result_frame,
                                          bg=BLANC,
                                          highlightthickness=0,
                                          bd=0)
                tree_container.pack(fill="both", expand=True)

                tree = ttk.Treeview(tree_container,
                                    columns=cols,
                                    show="headings",
                                    style="Green.Treeview")
                tree.pack(fill="both", expand=True, side="left")
                tree.configure(takefocus=0)

                tree.tag_configure('evenrow', background="#f1f8e9")
                tree.tag_configure('oddrow',  background=BLANC)

                for col in cols:
                    tree.heading(col, text=col)
                    tree.column(col, width=120, anchor="center")

                for i, row in enumerate(rows):
                    tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                    tree.insert("", "end", values=row, tags=(tag,))

                sb = ttk.Scrollbar(tree_container, command=tree.yview)
                sb.pack(side="right", fill="y")
                tree.configure(yscrollcommand=sb.set)

            # ── Message de statut — toujours affiché ─────────────
            if cursor.description:
                nb  = len(rows)
                msg = f"✅  Requête exécutée avec succès — {nb} ligne(s) retournée(s)."
            else:
                conn.commit()
                msg = "✅  Requête exécutée avec succès."

            tk.Label(self.sql_result_frame, text=msg,
                     font=("Arial", 10, "bold"), fg=VERT_MOYEN, bg=BLANC).pack(pady=(8, 4))

            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            tk.Label(self.sql_result_frame,
                     text=f"❌  Erreur MySQL : {e}",
                     font=("Arial", 11), fg="#a83232", bg=BLANC,
                     wraplength=800, justify="left").pack(pady=20)

    # ─── PAGE ASSISTANT IA ───────────────────────────────────────
    def page_guide(self):
        self.clear_main()

        header = tk.Frame(self.main_frame, bg=BLANC)
        header.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(header, text="🤖  Assistant IA — GreenSD",
                 font=("Arial", 22, "bold"), fg=VERT_FONCE, bg=BLANC).pack(side="left")

        tk.Button(header, text="🗑  Nouvelle conversation",
                  bg=VERT_MOYEN, fg=BLANC, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self._reset_conversation).pack(side="right", ipadx=8, ipady=4)

        tk.Label(self.main_frame,
                 text="Posez vos questions sur la base de données, les requêtes SQL ou l'application.",
                 font=("Arial", 10, "italic"), fg="#888888", bg=BLANC).pack(anchor="w", padx=20, pady=(0, 10))

        chat_outer = tk.Frame(self.main_frame, bg=BLANC)
        chat_outer.pack(fill="both", expand=True, padx=0, pady=0)

        self._chat_canvas = tk.Canvas(chat_outer, bg="#e8f5e9", highlightthickness=0)
        sb_chat = tk.Scrollbar(chat_outer, orient="vertical",
                               command=self._chat_canvas.yview)
        self._chat_canvas.configure(yscrollcommand=sb_chat.set)
        sb_chat.pack(side="right", fill="y")
        self._chat_canvas.pack(side="left", fill="both", expand=True)

        self._messages_frame = tk.Frame(self._chat_canvas, bg="#e8f5e9")
        self._chat_window = self._chat_canvas.create_window(
            (0, 0), window=self._messages_frame, anchor="nw"
        )

        def _on_frame_configure(e):
            self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._messages_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(e):
            self._chat_canvas.itemconfig(self._chat_window, width=e.width)
        self._chat_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            self._chat_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self._chat_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        if not self._chat_welcome_shown:
            self._chat_welcome_shown = True
            welcome = (
                "Bonjour ! Je suis l'assistant IA de GreenSD, propulsé par Groq 🌿\n\n"
                "Je peux vous aider avec :\n"
                "  • Des questions sur la base de données GreenSD\n"
                "  • La rédaction ou l'explication de requêtes SQL\n"
                "  • Le fonctionnement des tables et des colonnes\n"
                "  • L'utilisation de l'application\n\n"
                "Que puis-je faire pour vous ?"
            )
            self._add_message(welcome, role="assistant")
        else:
            for msg in self._chat_history[1:]:
                self._add_message(msg["content"], role=msg["role"])

        input_bar = tk.Frame(self.main_frame, bg=VERT_CLAIR,
                             highlightthickness=2,
                             highlightbackground=VERT_FONCE)
        input_bar.pack(fill="x", padx=0, pady=0, side="bottom")

        self._user_input = tk.Text(input_bar, height=3,
                                   font=("Arial", 11),
                                   bg=BLANC, relief="flat", wrap="word",
                                   padx=10, pady=8)
        self._user_input.pack(side="left", fill="both", expand=True,
                              padx=(10, 4), pady=8)
        self._user_input.bind("<Return>", self._on_enter_key)
        self._user_input.bind("<Shift-Return>", lambda e: None)

        send_btn = tk.Button(input_bar, text="Envoyer ➤",
                             bg=VERT_FONCE, fg=BLANC,
                             font=("Arial", 11, "bold"), relief="flat",
                             cursor="hand2", command=self._send_message)
        send_btn.pack(side="right", padx=10, pady=8, ipadx=10, ipady=6)
        send_btn.bind("<Enter>", lambda e: send_btn.config(bg=VERT_MOYEN))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg=VERT_FONCE))

    def _on_enter_key(self, event):
        self._send_message()
        return "break"

    def _add_message(self, text: str, role: str):
        is_user = (role == "user")

        PAD_X       = 14
        PAD_Y       = 10
        bubble_bg   = VERT_FONCE if is_user else BLANC
        bubble_fg   = BLANC      if is_user else "#222222"
        anchor_side = "e"        if is_user else "w"
        bg_chat     = "#e8f5e9"

        row_frame = tk.Frame(self._messages_frame, bg=bg_chat)
        row_frame.pack(fill="x", padx=16, pady=4)

        author       = "Vous" if is_user else "🤖 Assistant"
        author_color = VERT_MOYEN if is_user else "#555555"
        tk.Label(row_frame, text=author,
                 font=("Arial", 8, "bold"), fg=author_color,
                 bg=bg_chat).pack(anchor=anchor_side, pady=(2, 0))

        bubble_frame = tk.Frame(row_frame, bg=bubble_bg,
                                padx=PAD_X, pady=PAD_Y)
        bubble_frame.pack(anchor=anchor_side, pady=(0, 6))

        lbl = tk.Label(bubble_frame,
                       text=text,
                       font=("Arial", 10),
                       bg=bubble_bg,
                       fg=bubble_fg,
                       justify="left",
                       wraplength=700,
                       anchor="w")
        lbl.pack(side="left")

        self._messages_frame.update_idletasks()
        self._chat_canvas.configure(scrollregion=self._chat_canvas.bbox("all"))
        self._chat_canvas.yview_moveto(1.0)

    def _add_typing_indicator(self):
        self._typing_frame = tk.Frame(self._messages_frame, bg="#e8f5e9")
        self._typing_frame.pack(fill="x", padx=16, pady=6, anchor="w")
        self._typing_label = tk.Label(
            self._typing_frame,
            text="🤖 Assistant est en train d'écrire…",
            font=("Arial", 9, "italic"), fg="#999999", bg="#e8f5e9"
        )
        self._typing_label.pack(anchor="w")
        self._messages_frame.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    def _remove_typing_indicator(self):
        if hasattr(self, "_typing_frame") and self._typing_frame.winfo_exists():
            self._typing_frame.destroy()

    def _send_message(self):
        user_text = self._user_input.get("1.0", "end").strip()
        if not user_text:
            return

        self._user_input.delete("1.0", "end")
        self._add_message(user_text, role="user")
        self._chat_history.append({"role": "user", "content": user_text})
        self._add_typing_indicator()

        def call_api():
            response = groq_chat(self._chat_history)
            self.after(0, self._on_api_response, response)

        threading.Thread(target=call_api, daemon=True).start()

    def _on_api_response(self, response: str):
        self._remove_typing_indicator()
        self._add_message(response, role="assistant")
        self._chat_history.append({"role": "assistant", "content": response})

    def _reset_conversation(self):
        self._chat_history = [
            {"role": "system", "content": build_system_prompt()}
        ]
        self._chat_welcome_shown = False
        self.page_guide()

    # ─── PAGE DOCUMENTS UTILES ───────────────────────────────────
    def page_documents(self):
        self.clear_main()
        tk.Label(self.main_frame, text="Documents utiles",
                 font=("Arial", 24, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=(30, 10))

        DOCS = [
            ("greensd.py",            "Script Python — nettoyage et insertion des données",    False),
            ("greensd_ihm.py",        "Script Python — interface graphique (IHM)",             False),
            ("greensd_create.sql",    "Script SQL — création des tables",                      False),
            ("greensd_insert.sql",    "Script SQL — insertion des données de test",            False),
            ("greensd_requetes.sql",  "Fichier SQL — requêtes du projet",                      False),
            ("greensd_final.sql",     "Fichier SQL — script final du projet",                  False),
        ]
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Vert.TNotebook", background=BLANC, borderwidth=0)
        style.configure("Vert.TNotebook.Tab",
                        background=VERT_FONCE, foreground=BLANC,
                        font=("Arial", 10, "bold"), padding=[12, 6])
        style.map("Vert.TNotebook.Tab",
                  background=[("selected", VERT_MOYEN), ("active", VERT_CLAIR)],
                  foreground=[("selected", BLANC), ("active", VERT_FONCE)])

        notebook = ttk.Notebook(self.main_frame, style="Vert.TNotebook")
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        for filename, description, is_binary in DOCS:
            tab = tk.Frame(notebook, bg=BLANC)
            notebook.add(tab, text=filename)

            tk.Label(tab, text=description,
                     font=("Arial", 10, "italic"), fg="#888888", bg=BLANC).pack(anchor="w", padx=10, pady=(8, 4))

            frame_text = tk.Frame(tab, bg=BLANC)
            frame_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            sb_y = tk.Scrollbar(frame_text)
            sb_y.pack(side="right", fill="y")
            sb_x = tk.Scrollbar(frame_text, orient="horizontal")
            sb_x.pack(side="bottom", fill="x")

            text_widget = tk.Text(frame_text, font=("Courier", 10),
                                  bg=GRIS, relief="flat", wrap="none",
                                  yscrollcommand=sb_y.set,
                                  xscrollcommand=sb_x.set)
            text_widget.pack(fill="both", expand=True)
            sb_y.config(command=text_widget.yview)
            sb_x.config(command=text_widget.xview)

            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                filepath = os.path.join(script_dir, filename)
                if is_binary:
                    text_widget.insert("1.0",
                        f"📁  Fichier « {filename} »\n\n"
                        "⚠️  IMPORTANT :\n\n"
                        "1. Installez le logiciel Looping.\n"
                        "2. Puis, ouvrez le.\n"
                        "3. Enfin, revenez ici et cliquez sur le bouton vert.\n\n"
                        "👉 Cela affichera le MCD automatiquement.")
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    text_widget.insert("1.0", content)
            except FileNotFoundError:
                text_widget.insert("1.0",
                    f"⚠  Fichier « {filename} » introuvable.\n"
                    "Placez-le dans le même dossier que ce script.")
            except Exception as e:
                text_widget.insert("1.0", f"Erreur lors de la lecture : {e}")

            text_widget.config(state="disabled")

            btn_frame = tk.Frame(tab, bg=BLANC)
            btn_frame.pack(pady=(0, 10))
            tk.Button(btn_frame, text=f"Ouvrir  {filename}",
                      bg=VERT_MOYEN, fg=BLANC, font=("Arial", 10, "bold"),
                      relief="flat", cursor="hand2",
                      command=lambda f=filename: open_csv_file(
                          os.path.join(os.path.dirname(os.path.abspath(__file__)), f)
                      )).pack()
            # ── Onglet Vidéo ─────────────────────────────────────────
        VIDEO_URL = "https://youtu.be/FeaIrFtMrAk"

        tab_video = tk.Frame(notebook, bg=BLANC)
        notebook.add(tab_video, text="Vidéo")

        tk.Label(tab_video,
                 text="🎬  Vidéo de présentation du projet",
                 font=("Arial", 10, "italic"), fg="#888888", bg=BLANC).pack(anchor="w", padx=10, pady=(8, 4))

        center = tk.Frame(tab_video, bg=BLANC)
        center.pack(expand=True, fill="both")

        tk.Label(center,
                 text="🎬  Vidéo",
                 font=("Arial", 18, "bold"), fg=VERT_FONCE, bg=BLANC).pack(pady=(60, 10))

        tk.Label(center,
                 text=VIDEO_URL,
                 font=("Courier", 11), fg=VERT_MOYEN, bg=BLANC,
                 cursor="hand2").pack(pady=(0, 20))

        def open_video():
            import webbrowser
            webbrowser.open(VIDEO_URL)

        btn_video = tk.Button(center,
                              text="▶  Ouvrir la vidéo dans le navigateur",
                              bg=VERT_MOYEN, fg=BLANC,
                              font=("Arial", 13, "bold"),
                              relief="flat", cursor="hand2",
                              command=open_video)
        btn_video.pack(ipadx=20, ipady=12)
        btn_video.bind("<Enter>", lambda e: btn_video.config(bg=VERT_FONCE))
        btn_video.bind("<Leave>", lambda e: btn_video.config(bg=VERT_MOYEN))


# ================================
#       LANCEMENT
# ================================
if __name__ == "__main__":
    app = Application()
    app.mainloop()