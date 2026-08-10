// Central API response types — replace `any` across all pages

export interface Employe {
  employe_id:    number;
  matricule:     string;
  nom:           string;
  prenom:        string;
  nom_complet?:  string;
  poste:         string;
  type_contrat:  string;
  statut:        string;
  departement_id: number;
  nom_departement?: string;
  date_embauche: string;
  sexe?:         string;
  adresse_mail?: string;
}

export interface Departement {
  departement_id:   number;
  nom_departement:  string;
  sous_departement?: string;
}

export interface Pointage {
  pointage_id:    number;
  employe_id:     number;
  nom_complet?:   string;
  date_pointage:  string;
  heure_entree?:  string;
  heure_sortie?:  string;
  duree_travail?: number;
  retard_minutes?: number;
  statut:         string;
}

export interface Absence {
  absence_id:    number;
  employe_id:    number;
  nom_complet?:  string;
  date_absence:  string;
  justifiee:     boolean;
  motif?:        string;
  statut:        string;
}

export interface Conge {
  conge_id:      number;
  employe_id:    number;
  nom_complet?:  string;
  type_conge:    string;
  date_debut:    string;
  date_fin:      string;
  nb_jours:      number;
  statut:        string;
  commentaire?:  string;
}

export interface AlerteIA {
  alerte_id:   number;
  employe_id:  number;
  nom_complet?: string;
  type_alerte: string;
  niveau:      "Critique" | "Moyen" | "Info";
  message:     string;
  date_alerte: string;
  est_lue:     boolean;
}

export interface PredictionIA {
  employe_id:   number;
  nom:          string;
  probabilite:  number;
  niveau:       "Critique" | "Moyen";
  taux_absence: number;
  nb_absences:  number;
  nb_retards:   number;
}

export interface SoldeConge {
  employe_id:     number;
  solde_annuel:   number;
  solde_utilise:  number;
  solde_restant:  number;
}

export interface Formation {
  formation_id:  number;
  titre:         string;
  type_formation: string;
  organisateur:  string;
  date_debut:    string;
  date_fin:      string;
  nb_participants?: number;
}

export interface Mission {
  mission_id:  number;
  employe_id:  number;
  lieu:        string;
  type_mission: string;
  role:        string;
  statut:      string;
  date_debut:  string;
  date_fin:    string;
}

export interface AdminStats {
  total_employes:  number;
  total_users:     number;
  employes_actifs: number;
  total_conges:    number;
  total_absences:  number;
  total_pointages: number;
  total_alertes:   number;
  total_formations: number;
}

export interface HRStats {
  total_employes:    number;
  taux_presence:     number;
  taux_absenteisme:  number;
  conges_en_attente: number;
  alertes_actives:   number;
}

export interface Utilisateur {
  user_id:    number;
  employe_id: number;
  username:   string;
  role:       "admin" | "rh" | "employe";
  employe?:   Employe;
}

export interface AuthResponse {
  access_token: string;
  token_type:   string;
  user: {
    user_id:    number;
    role:       string;
    employe_id: number;
    employe:    Employe;
  };
}
