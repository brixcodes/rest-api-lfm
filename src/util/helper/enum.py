from enum import Enum



class PermissionEnum(str, Enum):
    """Permissions pour contrôler l'accès aux fonctionnalités."""
    LIRE_FORMATION = "lire_formation"  # Accès en lecture aux formations
    MODIFIER_FORMATION = "modifier_formation"  # Modifier les formations
    
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


class RessourceTypeEnum(str, Enum):
    """Types de ressources pédagogiques disponibles."""
    VIDEO = "video"
    PDF = "pdf"
    TEXTE = "texte"
    IMAGE = "image"
    AUDIO = "audio"
    LIEN = "lien"  # Lien externe ou ressource en ligne
    ARCHIVE = "archive"  # Zip, tar, etc.
