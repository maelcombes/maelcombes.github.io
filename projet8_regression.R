#FichierR_MaelCombesPeirache_AudisJulie

# Chargement des fichier
donnees_entrainement <- read.csv2("train.csv")
donnees_a_predire    <- read.csv2("to_predict.csv")

for (type_bien in c("Maison", "Appartement")) {
  
  # Trie le type de bien
  entrainement_type <- donnees_entrainement[donnees_entrainement$Type.local == type_bien, ]
  a_predire_type    <- donnees_a_predire[donnees_a_predire$Type.local == type_bien, ]
  
  # Codes postaux avec au moins 5 ventes
  codes_postaux_suffisants <- names(which(table(entrainement_type$Code.postal) >= 5))
  
  # Modèle global pour les codes postaux ayant moins de 5 valeurs
  log_surface_global <- log(entrainement_type$Surface.reelle.bati)
  log_prix_global <- log(entrainement_type$Valeur.fonciere)
  
  # Variance 
  variance_surface_global <- sum((log_surface_global - mean(log_surface_global))^2)
  # Covariance 
  covariance_global <- sum((log_surface_global - mean(log_surface_global)) * (log_prix_global - mean(log_prix_global)))
  
  pente_globale <- covariance_global / variance_surface_global
  ordonnee_globale <- mean(log_prix_global) - pente_globale * mean(log_surface_global)
  
  # applique a chauqe ligne
  for (i in 1:nrow(a_predire_type)) {
    
    # Par défaut on utilise le modèle global
    pente_utilisee <- pente_globale
    ordonnee_origine_utilisee <- ordonnee_globale
    
    # Si le code postal a assez de ventes, on calcule un modèle local
    if (a_predire_type$Code.postal[i] %in% codes_postaux_suffisants) {
      
      ventes_meme_cp <- entrainement_type[entrainement_type$Code.postal == a_predire_type$Code.postal[i], ]
      
      log_surface_cp <- log(ventes_meme_cp$Surface.reelle.bati)
      log_prix_cp <- log(ventes_meme_cp$Valeur.fonciere)
      
      # Variance 
      variance_surface_cp <- sum((log_surface_cp - mean(log_surface_cp))^2)
      # Covariance
      covariance_cp <- sum((log_surface_cp - mean(log_surface_cp)) * (log_prix_cp - mean(log_prix_cp)))
      
      pente_utilisee <- covariance_cp / variance_surface_cp
      ordonnee_utilisee <- mean(log_prix_cp) - pente_utilisee * mean(log_surface_cp)
    }
    
    # on repasse en valeur réelle avec exp()
    donnees_a_predire$Valeur.fonciere[donnees_a_predire$Type.local == type_bien][i] <- exp(pente_utilisee * log(a_predire_type$Surface.reelle.bati[i]) + ordonnee_utilisee)
  }
}

# Export
write.csv2(
  data.frame(id = donnees_a_predire$id, Valeur.fonciere = donnees_a_predire$Valeur.fonciere),
  "prediction.csv",
  row.names = FALSE
)

