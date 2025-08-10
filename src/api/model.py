from sqlalchemy import (
    Column, Index, Integer, String, DateTime, Enum, ForeignKey, Text, Table, Boolean, Float, Date, TIMESTAMP
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.util.helper.enum import (
    EvaluationTypeEnum, GenotypeTypeEnum, PermissionEnum, FileTypeEnum,
    RoleEnum, SexeEnum, StatutCompteEnum, StatutEnum, StatutFormationEnum, TypeFormationEnum,
    StatutInscriptionEnum, StatutPaiementEnum, StatutProjetCollectifEnum,
    StatutProjetIndividuelEnum, MethodePaiementEnum
)
from src.util.database.database import Base

# ============================================================================
# ========================= TABLES D’ASSOCIATION =========================
# ============================================================================

association_roles_permissions = Table(
    "association_roles_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

association_utilisateurs_permissions = Table(
    "association_utilisateurs_permissions", Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("utilisateurs.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

association_projets_collectifs_membres = Table(
    "association_projets_collectifs_membres", Base.metadata,
    Column("projet_collectif_id", Integer, ForeignKey("projets_collectifs.id"), primary_key=True),
    Column("utilisateur_id", Integer, ForeignKey("utilisateurs.id"), primary_key=True),
)

association_utilisateurs_formations = Table(
    "association_utilisateurs_formations", Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("utilisateurs.id"), primary_key=True),
    Column("formation_id", Integer, ForeignKey("formations.id"), primary_key=True),
)

# ============================================================================
# ========================= GESTION DES UTILISATEURS =========================
# ============================================================================

class Permission(Base):
    """
    Modèle pour les permissions des utilisateurs.
    Définit les différents types de permissions que les utilisateurs peuvent avoir.
    """
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    nom = Column(Enum(PermissionEnum), unique=True, nullable=False)

    roles = relationship("Role", secondary=association_roles_permissions, back_populates="permissions")
    utilisateurs = relationship("Utilisateur", secondary=association_utilisateurs_permissions, back_populates="permissions")

class Role(Base):
    """
    Modèle pour les rôles des utilisateurs.
    Définit les rôles que les utilisateurs peuvent avoir, comme apprenant, formateur, ou administrateur.
    """
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    nom = Column(Enum(RoleEnum), unique=True, nullable=False)

    permissions = relationship("Permission", secondary=association_roles_permissions, back_populates="roles")
    utilisateurs = relationship("Utilisateur", back_populates="role")

class Utilisateur(Base):
    """
    Modèle pour les utilisateurs.
    Stocke les informations des utilisateurs, y compris leurs rôles et permissions.
    """
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True)
    nom = Column(String(255), nullable=False)
    prenom = Column(String(255), nullable=True)
    sexe = Column(Enum(SexeEnum), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    statut = Column(Enum(StatutCompteEnum), nullable=False, default=StatutCompteEnum.ACTIF)
    est_actif = Column(Boolean, default=True)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    date_naissance = Column(Date, nullable=True)

    # Coordonnées et adresse
    telephone = Column(String(30), nullable=True)
    nationalite = Column(String(100), nullable=True)
    pays = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    ville = Column(String(100), nullable=True)
    adresse = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"))
    reset_token = Column(String(36), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)

    role = relationship("Role", back_populates="utilisateurs")
    permissions = relationship("Permission", secondary=association_utilisateurs_permissions, back_populates="utilisateurs")
    inscriptions = relationship("InscriptionFormation", back_populates="utilisateur")
    genotypes = relationship("GenotypeIndividuel", back_populates="utilisateur")
    plans_intervention = relationship("PlanInterventionIndividualise", back_populates="utilisateur")
    actualites = relationship("Actualite", back_populates="utilisateur")
    accreditations = relationship("Accreditation", back_populates="utilisateur")
    chefs_d_oeuvre = relationship("ChefDOeuvre", back_populates="utilisateur")
    projets_collectifs = relationship("ProjetCollectif", secondary=association_projets_collectifs_membres, back_populates="membres")
    resultats_evaluations = relationship("ResultatEvaluation", back_populates="utilisateur")
    formations = relationship("Formation", secondary=association_utilisateurs_formations, back_populates="utilisateurs")

# ============================================================================
# ========================= FORMATIONS ET CONTENUS PÉDAGOGIQUES ===============
# ============================================================================

class InscriptionFormation(Base):
    """
    Modèle pour les inscriptions aux formations.
    Gère les inscriptions des utilisateurs aux différentes formations, leur progression, et les paiements associés.
    """
    __tablename__ = "inscriptions_formations"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    formation_id = Column(Integer, ForeignKey("formations.id"))
    statut = Column(Enum(StatutInscriptionEnum), nullable=False, default=StatutInscriptionEnum.EN_COURS)
    progression = Column(Float, default=0.0)
    date_inscription = Column(DateTime(timezone=True), server_default=func.now())
    date_dernier_acces = Column(DateTime(timezone=True), onupdate=func.now())
    note_finale = Column(Float, nullable=True)
    heures_formation = Column(Float, default=0.0)
    montant_verse = Column(Float, default=0.0, nullable=False)
    statut_paiement = Column(Enum(StatutPaiementEnum), nullable=False, default=StatutPaiementEnum.AUCUN_VERSEMENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="inscriptions")
    formation = relationship("Formation", back_populates="inscriptions")
    paiements = relationship("Paiement", back_populates="inscription")

class Formation(Base):
    """
    Modèle pour les formations.
    Définit les formations disponibles, leurs spécialités, durée, statut, et autres détails.
    """
    __tablename__ = "formations"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    photo_couverture = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    specialite = Column(String(255), nullable=False, index=True)
    duree_mois = Column(Integer, nullable=False, default=12)
    statut = Column(Enum(StatutFormationEnum), nullable=False, default=StatutFormationEnum.EN_ATTENTE, index=True)
    frais = Column(Float, default=0.0, nullable=False)
    date_debut = Column(Date, nullable=False, index=True)
    date_fin = Column(Date, nullable=False, index=True)
    type_formation = Column(Enum(TypeFormationEnum), nullable=False, default=TypeFormationEnum.PRESENTIEL)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    modules = relationship("Module", back_populates="formation")
    inscriptions = relationship("InscriptionFormation", back_populates="formation")
    projets_collectifs = relationship("ProjetCollectif", back_populates="formation")
    accreditations = relationship("Accreditation", back_populates="formation")
    utilisateurs = relationship("Utilisateur", secondary=association_utilisateurs_formations, back_populates="formations")

class Module(Base):
    """
    Modèle pour les modules de formation.
    Représente les unités pédagogiques d'une formation, contenant des ressources et des évaluations.
    """
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    photo_couverture = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)
    formation_id = Column(Integer, ForeignKey("formations.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    formation = relationship("Formation", back_populates="modules")
    ressources = relationship("Ressource", back_populates="module")
    evaluations = relationship("Evaluation", back_populates="module")
    chefs_d_oeuvre = relationship("ChefDOeuvre", back_populates="module")

class Ressource(Base):
    """
    Modèle pour les ressources pédagogiques.
    Stocke les ressources associées aux modules de formation, comme des fichiers, des liens, etc.
    """
    __tablename__ = "ressources"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    type = Column(Enum(FileTypeEnum), nullable=False)
    contenu = Column(Text, nullable=True)
    lien = Column(String(255), nullable=True)
    description_du_lien = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    module = relationship("Module", back_populates="ressources")

class Paiement(Base):
    """
    Modèle pour les paiements.
    Enregistre les paiements effectués par les utilisateurs pour les inscriptions aux formations.
    """
    __tablename__ = "paiements"
    id = Column(Integer, primary_key=True)
    inscription_id = Column(Integer, ForeignKey("inscriptions_formations.id"), nullable=False)
    montant = Column(Float, nullable=False)
    date_paiement = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    methode_paiement = Column(Enum(MethodePaiementEnum), nullable=False)
    reference_transaction = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    inscription = relationship("InscriptionFormation", back_populates="paiements")

# ============================================================================
# ========================= PROJETS PÉDAGOGIQUES ==============================
# ============================================================================

class ChefDOeuvre(Base):
    """
    Modèle pour les chefs-d'œuvre.
    Représente les projets individuels réalisés par les apprenants dans le cadre de leur formation.
    """
    __tablename__ = "chefs_d_oeuvre"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    piece_jointe = Column(String(255), nullable=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    module_id = Column(Integer, ForeignKey("modules.id"))
    statut = Column(Enum(StatutProjetIndividuelEnum), nullable=False, default=StatutProjetIndividuelEnum.EN_COURS)
    date_soumission = Column(DateTime(timezone=True), nullable=True)
    note = Column(Float, nullable=True)
    commentaires = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="chefs_d_oeuvre")
    module = relationship("Module", back_populates="chefs_d_oeuvre")

class ProjetCollectif(Base):
    """
    Modèle pour les projets collectifs.
    Représente les projets collaboratifs réalisés par les apprenants dans le cadre de leur formation.
    """
    __tablename__ = "projets_collectifs"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    piece_jointe = Column(String(255), nullable=True)
    formation_id = Column(Integer, ForeignKey("formations.id"))
    statut = Column(Enum(StatutProjetCollectifEnum), nullable=False, default=StatutProjetCollectifEnum.EN_COURS)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    formation = relationship("Formation", back_populates="projets_collectifs")
    membres = relationship("Utilisateur", secondary=association_projets_collectifs_membres, back_populates="projets_collectifs")

# ============================================================================
# ========================= ÉVALUATIONS ======================================
# ============================================================================

class Evaluation(Base):
    """
    Modèle pour les évaluations.
    Définit les évaluations associées aux modules de formation pour tester les compétences des apprenants.
    """
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False)
    type = Column(Enum(EvaluationTypeEnum), nullable=False)
    consigne = Column(Text, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    module = relationship("Module", back_populates="evaluations")
    questions = relationship("Question", back_populates="evaluation")
    resultats = relationship("ResultatEvaluation", back_populates="evaluation")

class Question(Base):
    """
    Modèle pour les questions d'évaluation.
    Stocke les questions associées aux évaluations, avec leurs types et contenus.
    """
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    type = Column(Enum(EvaluationTypeEnum), nullable=False)
    contenu = Column(Text, nullable=False)
    piece_jointe = Column(String(255), nullable=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("Evaluation", back_populates="questions")
    propositions = relationship("Proposition", back_populates="question")

class Proposition(Base):
    """
    Modèle pour les propositions de réponse aux questions d'évaluation.
    Stocke les options de réponse pour les questions de type QCM.
    """
    __tablename__ = "propositions"
    id = Column(Integer, primary_key=True)
    texte = Column(Text, nullable=False)
    est_correcte = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    question = relationship("Question", back_populates="propositions")

class ResultatEvaluation(Base):
    """
    Modèle pour les résultats des évaluations.
    Enregistre les performances des apprenants aux évaluations, avec leurs notes et commentaires.
    """
    __tablename__ = "resultats_evaluations"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True)
    note = Column(Float, nullable=True)
    date_soumission = Column(DateTime(timezone=True), nullable=True)
    commentaires = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="resultats_evaluations")
    evaluation = relationship("Evaluation", back_populates="resultats")

# ============================================================================
# ========================= DONNÉES DU GÉNOTYPE INDIVIDUEL ===================
# ============================================================================

class GenotypeIndividuel(Base):
    """
    Modèle pour les données du génotype individuel.
    Stocke les informations individuelles des détenus ou de leurs proches pour le génotype individuel.
    """
    __tablename__ = "genotypes_individuels"
    id = Column(Integer, primary_key=True)
    type = Column(Enum(GenotypeTypeEnum), nullable=False, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), index=True)
    nom = Column(String(255), nullable=False, index=True)
    prenom = Column(String(255), nullable=True, index=True)
    age = Column(Integer, nullable=True)
    sexe = Column(Enum(SexeEnum), nullable=True)
    motif_detention = Column(Text, nullable=True)
    date_debut_detention = Column(Date, nullable=True, index=True)
    duree_detention = Column(String(50), nullable=True)
    pays_detention = Column(String(255), nullable=True, index=True)
    maison_detention = Column(String(255), nullable=True, index=True)
    profession = Column(String(255), nullable=True)
    activite_avant_detention = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="genotypes")
    ascendance = relationship("AscendanceGenotype", back_populates="genotype", uselist=False)
    sante = relationship("SanteGenotype", back_populates="genotype", uselist=False)
    education = relationship("EducationGenotype", back_populates="genotype", uselist=False)
    plans_intervention = relationship("PlanInterventionIndividualise", back_populates="genotype")

class AscendanceGenotype(Base):
    """
    Modèle pour les informations d'ascendance du génotype.
    Stocke les informations sur les parents et grands-parents des individus.
    """
    __tablename__ = "ascendance_genotypes"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"))
    nom_pere = Column(String(255), nullable=True)
    age_pere = Column(Integer, nullable=True)
    tribu_pere = Column(String(255), nullable=True)
    ethnie_pere = Column(String(255), nullable=True)
    religion_pere = Column(String(255), nullable=True)
    situation_matrimoniale_pere = Column(String(255), nullable=True)
    profession_pere = Column(String(255), nullable=True)
    domicile_pere = Column(String(255), nullable=True)
    proprietaire_domicile_pere = Column(String(255), nullable=True)
    nom_mere = Column(String(255), nullable=True)
    age_mere = Column(Integer, nullable=True)
    tribu_mere = Column(String(255), nullable=True)
    ethnie_mere = Column(String(255), nullable=True)
    religion_mere = Column(String(255), nullable=True)
    situation_matrimoniale_mere = Column(String(255), nullable=True)
    profession_mere = Column(String(255), nullable=True)
    domicile_mere = Column(String(255), nullable=True)
    proprietaire_domicile_mere = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    genotype = relationship("GenotypeIndividuel", back_populates="ascendance")

class SanteGenotype(Base):
    """
    Modèle pour les informations sanitaires du génotype.
    Stocke les informations sur la santé des individus, comme les maladies chroniques, les allergies, etc.
    """
    __tablename__ = "sante_genotypes"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"), unique=True)
    maladie_chronique = Column(Text, nullable=True)
    maladie_frequente = Column(Text, nullable=True)
    maladie_haut_risque = Column(Text, nullable=True)
    situation_vaccinale = Column(Text, nullable=True)
    antecedents_medicaux = Column(Text, nullable=True)
    maladie_hereditaire = Column(Text, nullable=True)
    handicap = Column(Text, nullable=True)
    allergie = Column(Text, nullable=True)
    groupe_sanguin = Column(String(10), nullable=True)
    rhesus = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    genotype = relationship("GenotypeIndividuel", back_populates="sante")

class EducationGenotype(Base):
    """
    Modèle pour les informations éducatives du génotype.
    Stocke les informations sur l'éducation des individus, comme les établissements fréquentés, les classes suivies, etc.
    """
    __tablename__ = "education_genotypes"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"), unique=True)
    etablissements_frequentes = Column(Text, nullable=True)
    derniere_classe = Column(String(255), nullable=True)
    date_arret_cours = Column(Date, nullable=True)
    raisons_decrochage = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    genotype = relationship("GenotypeIndividuel", back_populates="education")

# ============================================================================
# ========================= PLANS D’INTERVENTION =============================
# ============================================================================

class PlanInterventionIndividualise(Base):
    """
    Modèle pour les plans d'intervention individualisés.
    Définit les plans d'intervention basés sur le génotype individuel pour aider les détenus ou leurs proches.
    """
    __tablename__ = "plans_intervention_individualises"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"), index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), index=True)
    description = Column(Text, nullable=False)
    objectifs = Column(Text, nullable=True)
    statut = Column(Enum(StatutEnum), nullable=False, default=StatutEnum.EN_COURS)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    date_mise_a_jour = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    genotype = relationship("GenotypeIndividuel", back_populates="plans_intervention")
    utilisateur = relationship("Utilisateur", back_populates="plans_intervention")

# ============================================================================
# ========================= ACCRÉDITATIONS ===================================
# ============================================================================

class Accreditation(Base):
    """
    Modèle pour les accréditations.
    Gère les accréditations nécessaires pour l'accès aux établissements pénitentiaires.
    """
    __tablename__ = "accreditations"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    formation_id = Column(Integer, ForeignKey("formations.id"))
    etablissement = Column(String(255), nullable=False)
    date_emission = Column(DateTime(timezone=True), nullable=False)
    date_expiration = Column(DateTime(timezone=True), nullable=True)
    statut = Column(Enum(StatutEnum), nullable=False, default=StatutEnum.PLANIFIEE)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    utilisateur = relationship("Utilisateur", back_populates="accreditations")
    formation = relationship("Formation", back_populates="accreditations")

# ============================================================================
# ========================= ACTUALITÉS =======================================
# ============================================================================

class Actualite(Base):
    """
    Modèle pour les actualités.
    Stocke les articles et actualités publiés sur le site, avec des informations comme le titre, l'auteur, la date de publication, etc.
    """
    __tablename__ = "actualites"
    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    categorie = Column(String(100), nullable=False)
    chapeau = Column(Text, nullable=False)
    contenu_html = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    date_publication = Column(Date, nullable=False)
    date_debut_formation = Column(Date, nullable=True)
    date_fin_formation = Column(Date, nullable=True)
    document_url = Column(String(255), nullable=True)
    auteur = Column(String(150), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))

    utilisateur = relationship("Utilisateur", back_populates="actualites")