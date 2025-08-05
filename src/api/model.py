from sqlalchemy import (
    Column, Index, Integer, String, DateTime, Enum, ForeignKey, Text, Table, Boolean, Float, Date, TIMESTAMP
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from src.util.helper.enum import (
    EvaluationTypeEnum, GenotypeTypeEnum, PermissionEnum, RessourceTypeEnum, 
    RoleEnum, SexeEnum, StatutCompteEnum, StatutEnum, StatutFormationEnum, 
    StatutInscriptionEnum, StatutProjetCollectifEnum, StatutProjetIndividuelEnum
)
from src.util.database.database import Base

# ========================================================================    
# ========================= TABLES D’ASSOCIATION =========================
# ======================================================================== 

association_roles_permissions = Table(
    "association_roles_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    comment="Associe rôles et permissions pour la gestion des droits."
)

association_utilisateurs_permissions = Table(
    "association_utilisateurs_permissions", Base.metadata,
    Column("utilisateur_id", Integer, ForeignKey("utilisateurs.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    comment="Associe permissions directes aux utilisateurs."
)

association_projets_collectifs_membres = Table(
    "association_projets_collectifs_membres", Base.metadata,
    Column("projet_collectif_id", Integer, ForeignKey("projets_collectifs.id"), primary_key=True),
    Column("utilisateur_id", Integer, ForeignKey("utilisateurs.id"), primary_key=True),
    comment="Associe membres aux projets collectifs."
)

# ============================================================================
# ========================= GESTION DES UTILISATEURS =========================
# ============================================================================

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    nom = Column(Enum(PermissionEnum), unique=True, nullable=False)
    __table_args__ = {'comment': "Permissions pour contrôle d'accès."}

    roles = relationship("Role", secondary=association_roles_permissions, backref="permissions", lazy='select')
    utilisateurs = relationship("Utilisateur", secondary=association_utilisateurs_permissions, backref="permissions", lazy='select')

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    nom = Column(Enum(RoleEnum), unique=True, nullable=False)
    __table_args__ = {'comment': "Rôles des utilisateurs avec permissions associées."}

    utilisateurs = relationship("Utilisateur", backref=backref("role", lazy='select'), lazy='select')

class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True)
    nom = Column(String(255), nullable=False)
    prenom = Column(String(255), nullable=True)
    sexe = Column(Enum(SexeEnum), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    statut = Column(Enum(StatutCompteEnum), nullable=False, default=StatutCompteEnum.INACTIF)
    est_actif = Column(Boolean, default=True)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    date_naissance = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"))
    __table_args__ = {'comment': "Informations des utilisateurs (apprenants, formateurs, admins)."}

    inscriptions = relationship("InscriptionFormation", backref=backref("utilisateur", lazy='select'), lazy='select')
    genotypes = relationship("GenotypeIndividuel", backref=backref("utilisateur", lazy='joined'), lazy='select')
    plans_intervention = relationship("PlanInterventionIndividualise", backref=backref("utilisateur", lazy='joined'), lazy='select')
    actualites = relationship("Actualite", backref=backref("utilisateur", lazy='select'), lazy='select')
    accreditations = relationship("Accreditation", backref=backref("utilisateur", lazy='select'), lazy='select')

# =======================================================================================
# ========================= FORMATIONS ET CONTENUS PÉDAGOGIQUES =========================
# =======================================================================================

class InscriptionFormation(Base):
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
    __table_args__ = (
        Index('idx_inscription_user_formation', 'utilisateur_id', 'formation_id'),
        {'comment': "Suivi des inscriptions et progression des apprenants."}
    )

    formation = relationship("Formation", backref=backref("inscriptions", lazy='select'), lazy='select')

class Formation(Base):
    __tablename__ = "formations"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    photo_couverture = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    specialite = Column(String(255), nullable=False, index=True)
    duree_mois = Column(Integer, nullable=False, default=12)
    statut = Column(Enum(StatutFormationEnum), nullable=False, default=StatutFormationEnum.EN_ATTENTE, index=True)
    date_debut = Column(Date, nullable=False, index=True)
    date_fin = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        Index('idx_formation_dates', 'date_debut', 'date_fin'),
        Index('idx_formation_status_dates', 'statut', 'date_debut', 'date_fin'),
        {'comment': "Formations avec spécialités et calendrier."}
    )

    modules = relationship("Module", backref=backref("formation", lazy='select'), lazy='select')
    projets_collectifs = relationship("ProjetCollectif", backref=backref("formation", lazy='select'), lazy='select')

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    photo_couverture = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)
    formation_id = Column(Integer, ForeignKey("formations.id"))
    __table_args__ = {'comment': "Unités pédagogiques d’une formation."}

    ressources = relationship("Ressource", backref=backref("module", lazy='select'), lazy='select')
    evaluations = relationship("Evaluation", backref=backref("module", lazy='select'), lazy='select')
    chefs_d_oeuvre = relationship("ChefDOeuvre", backref=backref("module", lazy='select'), lazy='select')

class Ressource(Base):
    __tablename__ = "ressources"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False, index=True)
    type = Column(Enum(RessourceTypeEnum), nullable=False)
    contenu = Column(Text, nullable=True)
    lien = Column(String(255), nullable=True)
    description_du_lien = Column(Text, nullable=True)
    ordre = Column(Integer, nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"))
    __table_args__ = {'comment': "Ressources pédagogiques pour l’apprentissage."}

# ============================================================================
# ========================= PROJETS PÉDAGOGIQUES =============================
# ============================================================================

class ChefDOeuvre(Base):
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
    __table_args__ = (
        Index('idx_chef_oeuvre_user_module', 'utilisateur_id', 'module_id'),
        {'comment': "Projets individuels des apprenants (pédagogie Mao)."}
    )

    utilisateur = relationship("Utilisateur", backref=backref("chefs_d_oeuvre", lazy='select'), lazy='select')

class ProjetCollectif(Base):
    __tablename__ = "projets_collectifs"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    piece_jointe = Column(String(255), nullable=True)
    formation_id = Column(Integer, ForeignKey("formations.id"))
    statut = Column(Enum(StatutProjetCollectifEnum), nullable=False, default=StatutProjetCollectifEnum.EN_COURS)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        Index('idx_projet_collectif_formation_statut', 'formation_id', 'statut'),
        {'comment': "Projets collaboratifs des apprenants."}
    )

    membres = relationship("Utilisateur", secondary=association_projets_collectifs_membres, backref=backref("projets_collectifs", lazy='select'), lazy='select')

# ============================================================================
# ========================= ÉVALUATIONS ======================================
# ============================================================================

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True)
    titre = Column(String(255), nullable=False)
    type = Column(Enum(EvaluationTypeEnum), nullable=False)
    consigne = Column(Text, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    __table_args__ = {'comment': "Évaluations pour tester les compétences."}

    questions = relationship("Question", backref=backref("evaluation", lazy='select'), lazy='select')
    resultats = relationship("ResultatEvaluation", backref=backref("evaluation", lazy='select'), lazy='select')

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    type = Column(Enum(EvaluationTypeEnum), nullable=False)
    contenu = Column(Text, nullable=False)
    piece_jointe = Column(String(255), nullable=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True)
    __table_args__ = (
        Index('idx_question_type_eval', 'type', 'evaluation_id'),
        {'comment': "Questions des évaluations."}
    )

    propositions = relationship("Proposition", backref=backref("question", lazy='select'), lazy='select')

class Proposition(Base):
    __tablename__ = "propositions"
    id = Column(Integer, primary_key=True)
    texte = Column(Text, nullable=False)
    est_correcte = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    __table_args__ = {'comment': "Options de réponse pour QCM."}

class ResultatEvaluation(Base):
    __tablename__ = "resultats_evaluations"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), index=True)
    note = Column(Float, nullable=True)
    date_soumission = Column(DateTime(timezone=True), nullable=True)
    commentaires = Column(Text, nullable=True)
    __table_args__ = (
        Index('idx_resultat_user_eval', 'utilisateur_id', 'evaluation_id'),
        Index('idx_resultat_date_note', 'date_soumission', 'note'),
        {'comment': "Performances des apprenants aux évaluations."}
    )

    utilisateur = relationship("Utilisateur", backref=backref("resultats_evaluations", lazy='select'), lazy='select')

# ============================================================================
# ========================= DONNÉES DU GÉNOTYPE INDIVIDUEL ===================
# ============================================================================

class GenotypeIndividuel(Base):
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
    __table_args__ = (
        Index('idx_genotype_nom_prenom', 'nom', 'prenom'),
        Index('idx_genotype_detention', 'type', 'maison_detention', 'date_debut_detention'),
        {'comment': "Données des détenus ou proches pour le génotype individuel."}
    )

    ascendance = relationship("AscendanceGenotype", backref=backref("genotype", lazy='select'), uselist=False, lazy='select')
    sante = relationship("SanteGenotype", backref=backref("genotype", lazy='select'), uselist=False, lazy='select')
    education = relationship("EducationGenotype", backref=backref("genotype", lazy='select'), uselist=False, lazy='select')
    plans_intervention = relationship("PlanInterventionIndividualise", backref=backref("genotype", lazy='joined'), lazy='select')

class AscendanceGenotype(Base):
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
    __table_args__ = {'comment': "Informations d’ascendance pour le génotype."}

class SanteGenotype(Base):
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
    __table_args__ = {'comment': "Informations sanitaires pour le génotype."}

class EducationGenotype(Base):
    __tablename__ = "education_genotypes"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"), unique=True)
    etablissements_frequentes = Column(Text, nullable=True)
    derniere_classe = Column(String(255), nullable=True)
    date_arret_cours = Column(Date, nullable=True)
    raisons_decrochage = Column(Text, nullable=True)
    __table_args__ = {'comment': "Informations éducatives pour le génotype."}

# ========================================================================
# ========================= PLANS D’INTERVENTION =========================
# ========================================================================

class PlanInterventionIndividualise(Base):
    __tablename__ = "plans_intervention_individualises"
    id = Column(Integer, primary_key=True)
    genotype_id = Column(Integer, ForeignKey("genotypes_individuels.id"), index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), index=True)
    description = Column(Text, nullable=False)
    objectifs = Column(Text, nullable=True)
    statut = Column(Enum(StatutEnum), nullable=False, default=StatutEnum.EN_COURS)
    date_creation = Column(DateTime(timezone=True), server_default=func.now())
    date_mise_a_jour = Column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (
        Index('idx_plan_genotype_statut', 'genotype_id', 'statut'),
        Index('idx_plan_dates', 'date_creation', 'date_mise_a_jour'),
        {'comment': "Plans d’intervention individualisés basés sur le génotype."}
    )
    
# ============================================================================
# ========================= ACCRÉDITATIONS ===================================
# ============================================================================

class Accreditation(Base):
    __tablename__ = "accreditations"
    id = Column(Integer, primary_key=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    etablissement = Column(String(255), nullable=False)
    date_emission = Column(DateTime(timezone=True), nullable=False)
    date_expiration = Column(DateTime(timezone=True), nullable=True)
    statut = Column(Enum(StatutEnum), nullable=False, default=StatutEnum.EN_ATTENTE)
    __table_args__ = {'comment': "Accréditations pour accès aux établissements pénitentiaires."}

# ============================================================================
# ========================= ACTUALITÉS =======================================
# ============================================================================

class Actualite(Base):
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
    __table_args__ = {'comment': "Actualités et articles de blog."}