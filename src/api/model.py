from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text,
    Enum, ForeignKey, UniqueConstraint, Index,
    Numeric, Boolean
)
from sqlalchemy.orm import relationship

from src.util.helper.enum import (
    CiviliteEnum, DeviseEnum, MethodePaiementEnum, ModaliteEnum,
    RoleEnum, SpecialiteEnum, StatutCandidatureEnum, StatutPaiementEnum, StatutReclamationEnum,
    TimestampMixin, TypeFormationEnum, TypePaiementEnum, TypeRessourceEnum, StatutSessionEnum,
    TypeEvaluationEnum, StatutEvaluationEnum, StatutResultatEnum, TypeCorrectionEnum
)
from src.util.db.database import Base


# ──────────────────────────────────────────────────────────────
# ADRESSE (Nouvelle table pour normaliser les adresses et éviter la duplication)
# ──────────────────────────────────────────────────────────────
class Adresse(Base, TimestampMixin):
    __tablename__ = "adresses"

    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    type_adresse = Column(String(50), nullable=False)  # ex: 'principale', 'facturation'

    pays = Column(String(100), nullable=True)
    ville = Column(String(120), nullable=True)
    rue = Column(String(255), nullable=True)
    code_postal = Column(String(50), nullable=True)
    province = Column(String(120), nullable=True)

    # Champs de facturation
    pays_facturation = Column(String(100), nullable=True)
    ville_facturation = Column(String(120), nullable=True)
    rue_facturation = Column(String(255), nullable=True)
    code_postal_facturation = Column(String(50), nullable=True)
    province_facturation = Column(String(120), nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="adresses")

    __table_args__ = (
        UniqueConstraint("utilisateur_id", "type_adresse", name="uq_adresse_user_type"),
        Index("ix_adresse_user", "utilisateur_id"),
    )


# ──────────────────────────────────────────────────────────────
# UTILISATEUR (Optimisé: Adresses externalisées, ajout de champs pour traçabilité et sécurité, suppression de redondances)
# ──────────────────────────────────────────────────────────────
class Utilisateur(Base, TimestampMixin):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True)

    # Informations personnelles
    civilite = Column(Enum(CiviliteEnum), nullable=True)
    nom = Column(String(100), nullable=False, index=True)
    prenom = Column(String(100), nullable=False, index=True)
    date_naissance = Column(Date, nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    telephone_mobile = Column(String(30), nullable=True, index=True)  # Index ajouté pour recherches rapides
    telephone = Column(String(30), nullable=True)
    nationalite = Column(String(100), nullable=True)

    # Compte (Ajout: last_login, email_verified pour sécurité et traçabilité)
    password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.CANDIDAT, nullable=False)
    actif = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Informations professionnelles (Supprimé type_employeur car redondant avec categorie_socio_professionnelle)
    situation_professionnelle = Column(String(120), nullable=True)
    experience_professionnelle_en_mois = Column(Integer, nullable=True)
    employeur = Column(String(120), nullable=True)
    categorie_socio_professionnelle = Column(String(120), nullable=True)
    fonction = Column(String(120), nullable=True)

    # Parcours scolaire (Changé annee_obtention en Date pour plus de précision)
    dernier_diplome_obtenu = Column(String(120), nullable=True)
    date_obtention_dernier_diplome = Column(Date, nullable=True)

    # Relations
    adresses = relationship("Adresse", back_populates="utilisateur", cascade="all, delete-orphan")
    dossiers = relationship("DossierCandidature", back_populates="utilisateur", cascade="all, delete-orphan")
    reclamations = relationship("Reclamation", back_populates="auteur", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Utilisateur {self.id} {self.nom} {self.prenom}>"


# ──────────────────────────────────────────────────────────────
# CENTRE / FORMATION / SESSION (Optimisé: Ajout de champs pour gestion des places, prérequis, durée en Integer)
# ──────────────────────────────────────────────────────────────
class CentreFormation(Base, TimestampMixin):
    __tablename__ = "centres"

    id = Column(Integer, primary_key=True)
    nom = Column(String(255), nullable=False, unique=True, index=True)
    adresse = Column(String(255), nullable=True)
    ville = Column(String(120), nullable=True)
    code_postal = Column(String(50), nullable=True)
    pays = Column(String(100), nullable=True)

    sessions = relationship("SessionFormation", back_populates="centre", cascade="all, delete-orphan")


class Formation(Base, TimestampMixin):
    __tablename__ = "formations"

    id = Column(Integer, primary_key=True)
    specialite = Column(Enum(SpecialiteEnum), nullable=False, index=True)
    titre = Column(String(255), nullable=False, index=True)
    fiche_info = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    duree_heures = Column(Integer, nullable=True)  # Changé en Integer pour précision et calculs
    type_formation = Column(Enum(TypeFormationEnum), nullable=True)
    modalite = Column(Enum(ModaliteEnum), default=ModaliteEnum.EN_LIGNE, nullable=False)
    pre_requis = Column(Text, nullable=True)  # Ajouté: Prérequis pour la formation

    frais_inscription = Column(Numeric(12, 2), nullable=True)
    frais_formation = Column(Numeric(12, 2), nullable=True)
    devise = Column(Enum(DeviseEnum), default=DeviseEnum.EUR, nullable=False)

    sessions = relationship("SessionFormation", back_populates="formation", cascade="all, delete-orphan")
    modules = relationship("Module", back_populates="formation", cascade="all, delete-orphan")
    dossiers = relationship("DossierCandidature", back_populates="formation")
    information_descriptive = relationship("InformationDescriptive", back_populates="formation", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (Index("ix_formation_type_modalite", "type_formation", "modalite"),)  # Index ajouté pour filtres courants



class InformationDescriptive(Base, TimestampMixin):
    __tablename__ = "informations_descriptives"
    
    id = Column(Integer, primary_key=True, index=True)
    formation_id = Column(Integer, ForeignKey("formations.id", ondelete="CASCADE"), unique=True, nullable=False)
    presentation = Column(Text, nullable=True, comment="Contexte, enjeux et vision d'ensemble de la formation")
    avantages = Column(Text, nullable=True, comment="Avantages et spécificités de la formation")
    points_forts = Column(Text, nullable=True, comment="Points forts de la formation (liste)")
    competences_visees = Column(Text, nullable=True, comment="Compétences et savoir-faire à acquérir")
    programme = Column(Text, nullable=True, comment="Contenu détaillé et structure de la formation")
    profils_cibles = Column(Text, nullable=True, comment="Public cible et prérequis")
    inscription = Column(Text, nullable=True, comment="Modalités d'inscription, durée, rythme")
    certifications = Column(Text, nullable=True, comment="Certifications et attestations disponibles")
    methode_pedagogique = Column(Text, nullable=True, comment="Approche pédagogique et outils utilisés")
    evaluation = Column(Text, nullable=True, comment="Modalités d'évaluation et validation")
    
    # Relation one-to-one avec Formation
    formation = relationship("Formation", back_populates="information_descriptive", uselist=False)


class SessionFormation(Base, TimestampMixin):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey("formations.id", ondelete="CASCADE"), nullable=False)
    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="SET NULL"), nullable=True)

    date_debut = Column(Date, nullable=True)
    date_fin = Column(Date, nullable=True)
    date_limite_inscription = Column(Date, nullable=True)
    places_disponibles = Column(Integer, nullable=True)  # Ajouté: Gestion des places
    statut = Column(Enum(StatutSessionEnum), default=StatutSessionEnum.OUVERTE, nullable=False)  # Enum pour le statut

    modalite = Column(Enum(ModaliteEnum), nullable=True)

    formation = relationship("Formation", back_populates="sessions")
    centre = relationship("CentreFormation", back_populates="sessions")
    dossiers = relationship("DossierCandidature", back_populates="session")

    __table_args__ = (
        Index("ix_session_dates", "date_debut", "date_fin"),
        Index("ix_session_formation", "formation_id"),  # Index ajouté pour jointures fréquentes
    )


# ──────────────────────────────────────────────────────────────
# MODULE / RESSOURCE (Optimisé: Ajout d'index sur ordre, suppression de titre redondant si URL suffit)
# ──────────────────────────────────────────────────────────────
class Module(Base, TimestampMixin):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    formation_id = Column(Integer, ForeignKey("formations.id", ondelete="CASCADE"), nullable=False)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=True, index=True)  # Index ajouté pour tri

    formation = relationship("Formation", back_populates="modules")
    ressources = relationship("Ressource", back_populates="module", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("formation_id", "titre", name="uq_module_formation_titre"),)


class Ressource(Base, TimestampMixin):
    __tablename__ = "ressources"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    type_ressource = Column(Enum(TypeRessourceEnum), nullable=False)
    titre = Column(String(255), nullable=True)  # Optionnel si URL descriptive
    url = Column(String(512), nullable=False)  # Rendu obligatoire pour cohérence
    description = Column(Text, nullable=True)

    module = relationship("Module", back_populates="ressources")

    __table_args__ = (Index("ix_ressource_type", "type_ressource"),)  # Index ajouté pour filtres par type


# ──────────────────────────────────────────────────────────────
# DOSSIER CANDIDATURE / PIECES JOINTES (Optimisé: Ajout de date_soumission, motif_refus; frais hérités mais surchargables)
# ──────────────────────────────────────────────────────────────
class DossierCandidature(Base, TimestampMixin):
    __tablename__ = "dossiers"

    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    formation_id = Column(Integer, ForeignKey("formations.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)

    numero_candidature = Column(String(50), unique=True, index=True, nullable=True)
    statut = Column(Enum(StatutCandidatureEnum), default=StatutCandidatureEnum.RECUE, nullable=False)
    date_soumission = Column(DateTime(timezone=True), nullable=True)  # Ajouté: Traçabilité
    motif_refus = Column(Text, nullable=True)  # Ajouté: Pour statut REFUSE

    frais_inscription_montant = Column(Numeric(12, 2), nullable=True)  # Surchargable par rapport à Formation
    frais_formation_montant = Column(Numeric(12, 2), nullable=True)
    devise = Column(Enum(DeviseEnum), nullable=True)

    utilisateur = relationship("Utilisateur", back_populates="dossiers")
    formation = relationship("Formation", back_populates="dossiers")
    session = relationship("SessionFormation", back_populates="dossiers")

    reclamations = relationship("Reclamation", back_populates="dossier", cascade="all, delete-orphan")
    paiements = relationship("Paiement", back_populates="dossier", cascade="all, delete-orphan")
    pieces_jointes = relationship("PieceJointe", back_populates="dossier", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("utilisateur_id", "session_id", name="uq_dossier_user_session"),
        Index("ix_dossier_user", "utilisateur_id"),
        Index("ix_dossier_statut", "statut"),  # Index ajouté pour filtres par statut
    )

    # Propriétés métiers (Optimisé: Utilise sum() avec filter pour performance)
    @property
    def total_paye(self) -> float:
        return sum(float(p.montant) for p in self.paiements if p.statut == StatutPaiementEnum.SUCCES)

    @property
    def reste_a_payer_inscription(self) -> float:
        attendu = float(self.frais_inscription_montant or 0)
        paye = sum(float(p.montant) for p in self.paiements if p.type_paiement == TypePaiementEnum.INSCRIPTION and p.statut == StatutPaiementEnum.SUCCES)
        return max(attendu - paye, 0.0)

    @property
    def reste_a_payer_formation(self) -> float:
        attendu = float(self.frais_formation_montant or 0)
        paye = sum(float(p.montant) for p in self.paiements if p.type_paiement == TypePaiementEnum.FORMATION and p.statut == StatutPaiementEnum.SUCCES)
        return max(attendu - paye, 0.0)


class PieceJointe(Base, TimestampMixin):
    __tablename__ = "pieces_jointes"

    id = Column(Integer, primary_key=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)

    type_document = Column(String(100), nullable=False)
    chemin_fichier = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    date_upload = Column(DateTime(timezone=True), nullable=True)  # Ajouté: Traçabilité

    dossier = relationship("DossierCandidature", back_populates="pieces_jointes")

    __table_args__ = (Index("ix_piece_type", "type_document"),)  # Index ajouté pour filtres par type


# ──────────────────────────────────────────────────────────────
# RECLAMATIONS (Optimisé: Ajout de date_cloture, index sur statut)
# ──────────────────────────────────────────────────────────────
class Reclamation(Base, TimestampMixin):
    __tablename__ = "reclamations"

    id = Column(Integer, primary_key=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)
    auteur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)

    numero_reclamation = Column(String(50), unique=True, index=True, nullable=True)
    objet = Column(String(255), nullable=False)
    type_reclamation = Column(String(100), nullable=True)
    priorite = Column(String(50), nullable=True)
    statut = Column(Enum(StatutReclamationEnum), default=StatutReclamationEnum.NOUVEAU, nullable=False)
    description = Column(Text, nullable=True)
    date_cloture = Column(DateTime(timezone=True), nullable=True)  # Ajouté: Pour traçabilité de résolution

    dossier = relationship("DossierCandidature", back_populates="reclamations")
    auteur = relationship("Utilisateur", back_populates="reclamations")

    __table_args__ = (Index("ix_reclamation_statut", "statut"),)  # Index ajouté pour dashboards


# ──────────────────────────────────────────────────────────────
# PAIEMENTS (Optimisé: Ajout de date_echeance, index sur reference_externe)
# ──────────────────────────────────────────────────────────────
class Paiement(Base, TimestampMixin):
    __tablename__ = "paiements"

    id = Column(Integer, primary_key=True)
    dossier_id = Column(Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False)

    type_paiement = Column(Enum(TypePaiementEnum), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
    devise = Column(Enum(DeviseEnum), nullable=False)

    statut = Column(Enum(StatutPaiementEnum), default=StatutPaiementEnum.PENDING, nullable=False)
    methode = Column(Enum(MethodePaiementEnum), nullable=True)
    reference_externe = Column(String(120), index=True, nullable=True)
    message = Column(String(255), nullable=True)
    paye_le = Column(DateTime(timezone=True), nullable=True)
    date_echeance = Column(Date, nullable=True)  # Ajouté: Pour rappels

    dossier = relationship("DossierCandidature", back_populates="paiements")

    __table_args__ = (
        Index("ix_paiement_type_statut", "type_paiement", "statut"),
    )


# ──────────────────────────────────────────────────────────────
# SYSTÈME D'ÉVALUATION ET DE CERTIFICATION
# ──────────────────────────────────────────────────────────────

class Evaluation(Base, TimestampMixin):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    formateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True)
    
    # Informations de base
    titre = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    type_evaluation = Column(Enum(TypeEvaluationEnum), nullable=False, index=True)
    statut = Column(Enum(StatutEvaluationEnum), default=StatutEvaluationEnum.DRAFT, nullable=False)
    
    # Configuration temporelle
    date_ouverture = Column(DateTime(timezone=True), nullable=True)
    date_fermeture = Column(DateTime(timezone=True), nullable=True)
    duree_minutes = Column(Integer, nullable=True)  # Durée maximale pour passer l'évaluation
    
    # Configuration pédagogique
    ponderation = Column(Numeric(5, 2), default=100.0, nullable=False)  # Pourcentage dans la note finale
    note_minimale = Column(Numeric(5, 2), default=10.0, nullable=False)  # Note minimale pour réussir
    nombre_tentatives_max = Column(Integer, default=1, nullable=False)  # Nombre de tentatives autorisées
    
    # Configuration technique
    type_correction = Column(Enum(TypeCorrectionEnum), nullable=False)
    instructions = Column(Text, nullable=True)  # Instructions pour les candidats
    consignes_correction = Column(Text, nullable=True)  # Consignes pour les correcteurs
    
    # Relations
    session = relationship("SessionFormation", back_populates="evaluations")
    formateur = relationship("Utilisateur", foreign_keys=[formateur_id])
    resultats = relationship("ResultatEvaluation", back_populates="evaluation", cascade="all, delete-orphan")
    questions = relationship("QuestionEvaluation", back_populates="evaluation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_evaluation_session", "session_id"),
        Index("ix_evaluation_type", "type_evaluation"),
        Index("ix_evaluation_statut", "statut"),
        Index("ix_evaluation_dates", "date_ouverture", "date_fermeture"),
    )


class QuestionEvaluation(Base, TimestampMixin):
    __tablename__ = "questions_evaluation"

    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    
    # Contenu de la question
    question = Column(Text, nullable=False)
    type_question = Column(String(50), nullable=False)  # 'choix_multiple', 'texte_libre', 'fichier', etc.
    ordre = Column(Integer, nullable=False, default=0)
    
    # Configuration de la réponse
    reponses_possibles = Column(Text, nullable=True)  # JSON pour QCM
    reponse_correcte = Column(Text, nullable=True)  # Réponse attendue
    points = Column(Numeric(5, 2), default=1.0, nullable=False)  # Points pour cette question
    
    # Relations
    evaluation = relationship("Evaluation", back_populates="questions")
    reponses_candidats = relationship("ReponseCandidat", back_populates="question", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_question_evaluation", "evaluation_id"),
        Index("ix_question_ordre", "evaluation_id", "ordre"),
    )


class ResultatEvaluation(Base, TimestampMixin):
    __tablename__ = "resultats_evaluation"

    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    candidat_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    tentative_numero = Column(Integer, default=1, nullable=False)
    
    # Statut et progression
    statut = Column(Enum(StatutResultatEnum), default=StatutResultatEnum.EN_ATTENTE, nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    
    # Résultats
    note_obtenue = Column(Numeric(5, 2), nullable=True)
    note_maximale = Column(Numeric(5, 2), nullable=True)
    pourcentage_reussite = Column(Numeric(5, 2), nullable=True)
    
    # Feedback et commentaires
    commentaire_formateur = Column(Text, nullable=True)
    commentaire_candidat = Column(Text, nullable=True)
    
    # Relations
    evaluation = relationship("Evaluation", back_populates="resultats")
    candidat = relationship("Utilisateur", foreign_keys=[candidat_id])
    reponses = relationship("ReponseCandidat", back_populates="resultat", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("evaluation_id", "candidat_id", "tentative_numero", name="uq_resultat_eval_candidat_tentative"),
        Index("ix_resultat_evaluation", "evaluation_id"),
        Index("ix_resultat_candidat", "candidat_id"),
        Index("ix_resultat_statut", "statut"),
    )


class ReponseCandidat(Base, TimestampMixin):
    __tablename__ = "reponses_candidats"

    id = Column(Integer, primary_key=True)
    resultat_id = Column(Integer, ForeignKey("resultats_evaluation.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions_evaluation.id", ondelete="CASCADE"), nullable=False)
    
    # Réponse du candidat
    reponse_texte = Column(Text, nullable=True)
    reponse_fichier_url = Column(String(512), nullable=True)  # URL vers le fichier uploadé
    reponse_json = Column(Text, nullable=True)  # Pour les réponses complexes (QCM, etc.)
    
    # Évaluation de la réponse
    points_obtenus = Column(Numeric(5, 2), nullable=True)
    points_maximaux = Column(Numeric(5, 2), nullable=True)
    commentaire_correction = Column(Text, nullable=True)
    
    # Relations
    resultat = relationship("ResultatEvaluation", back_populates="reponses")
    question = relationship("QuestionEvaluation", back_populates="reponses_candidats")
    
    __table_args__ = (
        UniqueConstraint("resultat_id", "question_id", name="uq_reponse_resultat_question"),
        Index("ix_reponse_resultat", "resultat_id"),
        Index("ix_reponse_question", "question_id"),
    )


class Certificat(Base, TimestampMixin):
    __tablename__ = "certificats"

    id = Column(Integer, primary_key=True)
    candidat_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Informations du certificat
    numero_certificat = Column(String(100), unique=True, index=True, nullable=False)
    titre_formation = Column(String(255), nullable=False)
    date_obtention = Column(Date, nullable=False)
    
    # Résultats finaux
    note_finale = Column(Numeric(5, 2), nullable=False)
    mention = Column(String(50), nullable=True)  # 'Passable', 'Bien', 'Très bien', etc.
    statut_validation = Column(String(50), nullable=False)  # 'Validé', 'Non validé'
    
    # Métadonnées
    url_certificat = Column(String(512), nullable=True)  # URL vers le PDF du certificat
    commentaires = Column(Text, nullable=True)
    
    # Relations
    candidat = relationship("Utilisateur", foreign_keys=[candidat_id])
    session = relationship("SessionFormation")
    
    __table_args__ = (
        Index("ix_certificat_candidat", "candidat_id"),
        Index("ix_certificat_session", "session_id"),
        Index("ix_certificat_date", "date_obtention"),
    )


# ──────────────────────────────────────────────────────────────
# Mise à jour des relations existantes
# ──────────────────────────────────────────────────────────────

# Ajouter la relation evaluations à SessionFormation
SessionFormation.evaluations = relationship("Evaluation", back_populates="session", cascade="all, delete-orphan")

# Ajouter la relation evaluations_crees à Utilisateur (pour les formateurs)
Utilisateur.evaluations_crees = relationship("Evaluation", foreign_keys="[Evaluation.formateur_id]", back_populates="formateur")

# Ajouter la relation resultats_evaluations à Utilisateur (pour les candidats)
Utilisateur.resultats_evaluations = relationship("ResultatEvaluation", foreign_keys="[ResultatEvaluation.candidat_id]", back_populates="candidat")

# Ajouter la relation certificats à Utilisateur
Utilisateur.certificats = relationship("Certificat", back_populates="candidat", cascade="all, delete-orphan")