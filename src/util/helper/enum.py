from enum import Enum
from sqlalchemy import Column, DateTime, func

# ──────────────────────────────────────────────────────────────────────────────
# Mixins utilitaires
# ──────────────────────────────────────────────────────────────────────────────

class TimestampMixin(object):
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class CiviliteEnum(str, Enum):
    MONSIEUR = "MONSIEUR"
    MADAME = "MADAME"
    MADEMOISELLE = "MADEMOISELLE"
    AUTRE = "AUTRE"  
    
class RoleEnum(str, Enum):
    CANDIDAT = "CANDIDAT"
    ADMIN = "ADMIN"
    FORMATEUR = "FORMATEUR"  # Nouveau rôle pour les formateurs

class SpecialiteEnum(str, Enum):
    ACCUEIL = "accueil écoute familles"
    PENITENTIAIRE = "appui pénitentiaire"
    ASSISTANCE = "technicien assistance"

class ModaliteEnum(str, Enum):
    PRESENTIEL = "PRESENTIEL"
    EN_LIGNE = "EN_LIGNE"


class StatutSessionEnum(str, Enum):
    OUVERTE = "ouverte"
    FERMEE = "fermée"
    ANNULEE = "annulée"


class TypeFormationEnum(str, Enum):
    COURTE = "courte"
    LONGUE = "longue"


class StatutCandidatureEnum(str, Enum):
    RECUE = "candidature reçue"
    EN_ETUDE = "en étude"
    ACCEPTÉE = "acceptée"
    REFUSÉE = "refusée"
    ANNULEE = "annulée"


class StatutReclamationEnum(str, Enum):
    NOUVEAU = "nouveau"
    EN_COURS = "en cours"
    CLOTURE = "clôturé"


class TypeRessourceEnum(str, Enum):
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    LIEN = "lien"
    AUTRE = "autre"


class DeviseEnum(str, Enum):
    EUR = "EUR"
    XAF = "XAF"
    XOF = "XOF"
    USD = "USD"


class TypePaiementEnum(str, Enum):
    INSCRIPTION = "inscription"
    FORMATION = "formation"


class StatutPaiementEnum(str, Enum):
    PENDING = "pending"  
    ACCEPTED = "accepted"  
    REFUSED = "refused"  
    CANCELLED = "cancelled"  
    ERROR = "error"  
    REPAY = "rembourse"


class MethodePaiementEnum(str, Enum):
    MOBILE_MONEY = "mobile_money"
    ALL = "ALL"
    CARTE = "carte_bancaire"
    VIREMENT = "virement"
    ESPECES = "especes"

# ──────────────────────────────────────────────────────────────────────────────
# Enums pour les évaluations
# ──────────────────────────────────────────────────────────────────────────────

class TypeEvaluationEnum(str, Enum):
    QCM = "qcm"                    # Quiz à choix multiples (auto-corrigé)
    DEVOIR = "devoir"              # Devoir à rendre (correction manuelle)
    PROJET = "projet"              # Projet pratique
    EXAMEN = "examen"              # Examen surveillé
    SOUTENANCE = "soutenance"      # Soutenance orale
    QUIZ = "quiz"                  # Quiz intermédiaire
    CAS_PRATIQUE = "cas_pratique"  # Étude de cas

class TypeCorrectionEnum(str, Enum):
    AUTO = "automatique"           # Correction automatique (QCM)
    MANUELLE = "manuelle"          # Correction manuelle par formateur
    MIXTE = "mixte"                # Partie auto + partie manuelle

class StatutEvaluationEnum(str, Enum):
    DRAFT = "brouillon"            # En cours de création
    ACTIVE = "active"              # Ouverte aux candidats
    FERMEE = "fermée"              # Fermée aux candidats
    ARCHIVEE = "archivée"          # Archivée

class StatutResultatEnum(str, Enum):
    EN_ATTENTE = "en_attente"      # En attente de correction
    EN_COURS = "en_cours"          # En cours de passage
    SUCCES = "succès"              # Réussi
    ECHEC = "échec"                # Échoué
    ABANDONNE = "abandonné"        # Abandonné

class TypeQuestionEnum(str, Enum):
    QCM = "qcm"
    TEXTE_LIBRE = "texte_libre"
    PRATIQUE = "pratique"
    FICHIER = "fichier"