from enum import Enum

class TypeFormationEnum(str, Enum):
    PRESENTIEL = "présentiel"
    EN_LIGNE = "en_ligne"

class PermissionEnum(str, Enum):
    """Permissions pour contrôler l'accès aux fonctionnalités."""
    # Utilisateurs
    LIRE_UTILISATEUR = "lire_utilisateur"  # Accès en lecture aux utilisateurs
    MODIFIER_UTILISATEUR = "modifier_utilisateur"  # Modifier les utilisateurs
    CREER_UTILISATEUR = "creer_utilisateur"  # Créer un utilisateur
    SUPPRIMER_UTILISATEUR = "supprimer_utilisateur"  # Supprimer un utilisateur
    REINITIALISER_MOT_DE_PASSE = "reinitialiser_mot_de_passe"  # Réinitialiser le mot de passe
    CHANGER_MOT_DE_PASSE = "changer_mot_de_passe"  # Changer son propre mot de passe

    # Permissions
    LIRE_PERMISSION = "lire_permission"  # Accès en lecture aux permissions
    MODIFIER_PERMISSION = "modifier_permission"  # Modifier les permissions
    CREER_PERMISSION = "creer_permission"  # Créer une permission
    SUPPRIMER_PERMISSION = "supprimer_permission"  # Supprimer une permission

    # Rôles
    LIRE_ROLE = "lire_role"  # Accès en lecture aux rôles
    MODIFIER_ROLE = "modifier_role"  # Modifier les rôles
    CREER_ROLE = "creer_role"  # Créer un rôle
    SUPPRIMER_ROLE = "supprimer_role"  # Supprimer un rôle

    # Formations
    LIRE_FORMATION = "lire_formation"  # Accès en lecture aux formations
    MODIFIER_FORMATION = "modifier_formation"  # Modifier les formations
    CREER_FORMATION = "creer_formation"  # Créer une formation
    SUPPRIMER_FORMATION = "supprimer_formation"  # Supprimer une formation

    # Inscriptions
    LIRE_INSCRIPTION = "lire_inscription"  # Accès en lecture aux inscriptions
    MODIFIER_INSCRIPTION = "modifier_inscription"  # Modifier les inscriptions
    CREER_INSCRIPTION = "creer_inscription"  # Créer une inscription
    SUPPRIMER_INSCRIPTION = "supprimer_inscription"  # Supprimer une inscription

    # Paiements
    LIRE_PAIEMENT = "lire_paiement"  # Accès en lecture aux paiements
    MODIFIER_PAIEMENT = "modifier_paiement"  # Modifier les paiements
    CREER_PAIEMENT = "creer_paiement"  # Créer un paiement
    SUPPRIMER_PAIEMENT = "supprimer_paiement"  # Supprimer un paiement

    # Modules
    LIRE_MODULE = "lire_module"  # Accès en lecture aux modules
    MODIFIER_MODULE = "modifier_module"  # Modifier les modules
    CREER_MODULE = "creer_module"  # Créer un module
    SUPPRIMER_MODULE = "supprimer_module"  # Supprimer un module

    # Ressources
    LIRE_RESSOURCE = "lire_ressource"  # Accès en lecture aux ressources
    MODIFIER_RESSOURCE = "modifier_ressource"  # Modifier les ressources
    CREER_RESSOURCE = "creer_ressource"  # Créer une ressource
    SUPPRIMER_RESSOURCE = "supprimer_ressource"  # Supprimer une ressource

    # Chefs-d'œuvre
    LIRE_CHEF_D_OEUVRE = "lire_chef_d_oeuvre"  # Accès en lecture aux chefs-d'œuvre
    MODIFIER_CHEF_D_OEUVRE = "modifier_chef_d_oeuvre"  # Modifier les chefs-d'œuvre
    CREER_CHEF_D_OEUVRE = "creer_chef_d_oeuvre"  # Créer un chef-d'œuvre
    SUPPRIMER_CHEF_D_OEUVRE = "supprimer_chef_d_oeuvre"  # Supprimer un chef-d'œuvre

    # Projets collectifs
    LIRE_PROJET_COLLECTIF = "lire_projet_collectif"  # Accès en lecture aux projets collectifs
    MODIFIER_PROJET_COLLECTIF = "modifier_projet_collectif"  # Modifier les projets collectifs
    CREER_PROJET_COLLECTIF = "creer_projet_collectif"  # Créer un projet collectif
    SUPPRIMER_PROJET_COLLECTIF = "supprimer_projet_collectif"  # Supprimer un projet collectif

    # Évaluations
    LIRE_EVALUATION = "lire_evaluation"  # Accès en lecture aux évaluations
    MODIFIER_EVALUATION = "modifier_evaluation"  # Modifier les évaluations
    CREER_EVALUATION = "creer_evaluation"  # Créer une évaluation
    SUPPRIMER_EVALUATION = "supprimer_evaluation"  # Supprimer une évaluation

    # Questions
    LIRE_QUESTION = "lire_question"  # Accès en lecture aux questions
    MODIFIER_QUESTION = "modifier_question"  # Modifier les questions
    CREER_QUESTION = "creer_question"  # Créer une question
    SUPPRIMER_QUESTION = "supprimer_question"  # Supprimer une question

    # Propositions
    LIRE_PROPOSITION = "lire_proposition"  # Accès en lecture aux propositions
    MODIFIER_PROPOSITION = "modifier_proposition"  # Modifier les propositions
    CREER_PROPOSITION = "creer_proposition"  # Créer une proposition
    SUPPRIMER_PROPOSITION = "supprimer_proposition"  # Supprimer une proposition

    # Résultats d'évaluations
    LIRE_RESULTAT_EVALUATION = "lire_resultat_evaluation"  # Accès en lecture aux résultats d'évaluations
    MODIFIER_RESULTAT_EVALUATION = "modifier_resultat_evaluation"  # Modifier les résultats d'évaluations
    CREER_RESULTAT_EVALUATION = "creer_resultat_evaluation"  # Créer un résultat d'évaluation
    SUPPRIMER_RESULTAT_EVALUATION = "supprimer_resultat_evaluation"  # Supprimer un résultat d'évaluation

    # Génotypes
    LIRE_GENOTYPE = "lire_genotype"  # Accès en lecture aux génotypes
    MODIFIER_GENOTYPE = "modifier_genotype"  # Modifier les génotypes
    CREER_GENOTYPE = "creer_genotype"  # Créer un génotype
    SUPPRIMER_GENOTYPE = "supprimer_genotype"  # Supprimer un génotype

    # Ascendances génotype
    LIRE_ASCENDANCE_GENOTYPE = "lire_ascendance_genotype"  # Accès en lecture aux ascendances de génotype
    MODIFIER_ASCENDANCE_GENOTYPE = "modifier_ascendance_genotype"  # Modifier les ascendances de génotype
    CREER_ASCENDANCE_GENOTYPE = "creer_ascendance_genotype"  # Créer une ascendance de génotype
    SUPPRIMER_ASCENDANCE_GENOTYPE = "supprimer_ascendance_genotype"  # Supprimer une ascendance de génotype

    # Santés génotype
    LIRE_SANTE_GENOTYPE = "lire_sante_genotype"  # Accès en lecture aux santés de génotype
    MODIFIER_SANTE_GENOTYPE = "modifier_sante_genotype"  # Modifier les santés de génotype
    CREER_SANTE_GENOTYPE = "creer_sante_genotype"  # Créer une santé de génotype
    SUPPRIMER_SANTE_GENOTYPE = "supprimer_sante_genotype"  # Supprimer une santé de génotype

    # Éducations génotype
    LIRE_EDUCATION_GENOTYPE = "lire_education_genotype"  # Accès en lecture aux éducations de génotype
    MODIFIER_EDUCATION_GENOTYPE = "modifier_education_genotype"  # Modifier les éducations de génotype
    CREER_EDUCATION_GENOTYPE = "creer_education_genotype"  # Créer une éducation de génotype
    SUPPRIMER_EDUCATION_GENOTYPE = "supprimer_education_genotype"  # Supprimer une éducation de génotype

    # Plans d'intervention
    LIRE_PLAN_INTERVENTION = "lire_plan_intervention"  # Accès en lecture aux plans d'intervention
    MODIFIER_PLAN_INTERVENTION = "modifier_plan_intervention"  # Modifier les plans d'intervention
    CREER_PLAN_INTERVENTION = "creer_plan_intervention"  # Créer un plan d'intervention
    SUPPRIMER_PLAN_INTERVENTION = "supprimer_plan_intervention"  # Supprimer un plan d'intervention

    # Accréditations
    LIRE_ACCREDITATION = "lire_accreditation"  # Accès en lecture aux accréditations
    MODIFIER_ACCREDITATION = "modifier_accreditation"  # Modifier les accréditations
    CREER_ACCREDITATION = "creer_accreditation"  # Créer une accréditation
    SUPPRIMER_ACCREDITATION = "supprimer_accreditation"  # Supprimer une accréditation

    # Actualités
    LIRE_ACTUALITE = "lire_actualite"  # Accès en lecture aux actualités
    MODIFIER_ACTUALITE = "modifier_actualite"  # Modifier les actualités
    CREER_ACTUALITE = "creer_actualite"  # Créer une actualité
    SUPPRIMER_ACTUALITE = "supprimer_actualite"  # Supprimer une actualité

    # Fichiers
    LIRE_FICHIER = "lire_fichier"  # Accès en lecture aux fichiers
    TELEVERSER_FICHIER = "televerser_fichier"  # Téléverser un fichier
    SUPPRIMER_FICHIER = "supprimer_fichier"  # Supprimer un fichier
    
class StatutCompteEnum(str, Enum):
    """Statuts pour les utilisateurs."""
    ACTIF = "actif"  # actif
    INACTIF = "inactif"  # inactif
    SUPPRIMER = "supprimer"  # supprimer
    
class StatutFormationEnum(str, Enum):
    EN_ATTENTE = "En attente"    # La formation est créée mais pas encore validée ou approuvée.
    PLANIFIEE = "Planifiée"      # Une date de début est prévue mais elle n’a pas encore commencé.
    EN_COURS = "En cours"        # La formation est actuellement en cours.
    EN_PAUSE = "En pause"        # La formation a été temporairement suspendue (vacances, interruption, etc.).
    TERMINEE = "Terminée"        # La formation est terminée avec succès.
    ANNULEE = "Annulée"          # La formation a été annulée (manque de participants, problème logistique…).
    ARCHIVEE = "Archivée"        # La formation est ancienne, clôturée, et stockée à des fins historiques.
    REJETEE = "Rejetée"          # Rejetée après validation (contenu, qualité ou autres raisons).
    
class StatutInscriptionEnum(str, Enum):
    """Statuts pour les inscriptions aux formations."""
    EN_COURS = "En cours"  # en attente
    TERMINER = "terminé"  # terminé
    
class StatutProjetIndividuelEnum(str, Enum):
    """Statuts pour les projets individuel."""
    EN_COURS = "En cours"  # En cours d'exécution
    TERMINE = "termine"  # Terminé avec succès
    ABANDON = "abandon"  # Abandonné
    EN_CORRECTION = "En correction"  # En attente de validation
    
class StatutProjetCollectifEnum(str, Enum):
    """Statuts pour les projets collectif."""
    EN_ATTENTE = "En attente"    # La formation est créée mais pas encore validée ou approuvée.
    PLANIFIEE = "Planifiée"      # Une date de début est prévue mais elle n’a pas encore commencé.
    EN_COURS = "En cours"        # La formation est actuellement en cours.
    EN_PAUSE = "En pause"        # La formation a été temporairement suspendue (vacances, interruption, etc.).
    TERMINEE = "Terminée"        # La formation est terminée avec succès.
    ANNULEE = "Annulée"          # La formation a été annulée (manque de participants, problème logistique…).
    ARCHIVEE = "Archivée"        # La formation est ancienne, clôturée, et stockée à des fins historiques.
    

class MethodePaiementEnum(str, Enum):
    CARTE_BANCAIRE = "CARTE_BANCAIRE"
    MOBILE_MONEY = "MOBILE_MONEY"
    VIREMENT_BANCAIRE = "VIREMENT_BANCAIRE"
    ESPECES = "ESPECES"
    PESUPAY = "PESUPAY"
    
class StatutPaiementEnum(str, Enum):
    VERSEMENT_PARTIEL = "Versement partiel"  # Paiement partiel effectué
    AUCUN_VERSEMENT = "Aucun versement"
    TERMINE = "Terminé"
    
class StatutPaiemmentFraisFormationEnum(str, Enum):
    PLANIFIEE = "Planifiée"      # Une date de début est prévue mais elle n’a pas encore commencé.
    EN_COURS = "En cours"        # La formation est actuellement en cours.
    TERMINEE = "Terminée"        # La formation est terminée avec succès.    
    
class StatutEnum(str, Enum):
    PLANIFIEE = "Planifiée"      # Une date de début est prévue mais elle n’a pas encore commencé.
    EN_COURS = "En cours"        # La formation est actuellement en cours.
    TERMINEE = "Terminée"        # La formation est terminée avec succès.
    
class GenotypeTypeEnum(str, Enum):
    """Type de profil lié au génotype."""
    DETENU = "detenu"
    PROCHE = "proche"

class SexeEnum(str, Enum):
    """Genre biologique d'une personne."""
    HOMME = "homme"
    FEMME = "femme"
    AUTRE = "autre"  # Facultatif : utile pour inclure plus d'identités


class RoleEnum(str, Enum):
    """Rôle d’un utilisateur dans le système."""
    ADMIN = "admin"  # Administrateur du système
    COORDONNATEUR = "coordonnateur"  # Responsable de programme
    FORMATEUR = "formateur"  # Formateur/enseignant
    REFERENT = "referent"  # Formateur référent
    APPRENANT = "apprenant"  # Étudiant/apprenant


class EvaluationTypeEnum(str, Enum):
    """Types de questions utilisées dans les évaluations."""
    QCM = "qcm"  # Question à choix multiples
    OUVERTE = "ouverte"  # Réponse rédigée libre
    PRATIQUE = "pratique"  # Exercice ou manipulation


class FileTypeEnum(str, Enum):
    """Types de ressources pédagogiques disponibles."""
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
