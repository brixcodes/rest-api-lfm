from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum
from src.util.helper.enum import (
    EvaluationTypeEnum, GenotypeTypeEnum, PermissionEnum, FileTypeEnum,
    RoleEnum, SexeEnum, StatutCompteEnum, StatutEnum, StatutFormationEnum,
    StatutInscriptionEnum, StatutProjetCollectifEnum, StatutProjetIndividuelEnum,
    MethodePaiementEnum, StatutPaiementEnum
)

# ==================================================================
# ========================= SCHÉMAS LIGHT =========================
# ==================================================================


class RoleMinLight(BaseModel):
    id: int
    nom: RoleEnum
    class Config:
        from_attributes = True

class PermissionLight(BaseModel):
    id: int
    nom: PermissionEnum
    roles: List[RoleMinLight] = []
    class Config:
        from_attributes = True

# Minimal permission shape for embedding in Role/RoleLight
class PermissionMinLight(BaseModel):
    id: int
    nom: PermissionEnum
    class Config:
        from_attributes = True

class RoleLight(BaseModel):
    id: int
    nom: RoleEnum
    permissions: List[PermissionMinLight] = []  # Permissions as objects
    user_count: int = 0  # Count of associated users
    class Config:
        from_attributes = True

# Resolve forward references for circular types (Pydantic v2/v1)
try:
    PermissionLight.model_rebuild()
    RoleLight.model_rebuild()
    RoleMinLight.model_rebuild()
except Exception:
    try:
        PermissionLight.update_forward_refs()
        RoleLight.update_forward_refs()
        RoleMinLight.update_forward_refs()
    except Exception:
        pass

class UtilisateurLight(BaseModel):
    id: int
    nom: str
    prenom: Optional[str]
    sexe: SexeEnum
    email: str
    statut: StatutCompteEnum
    est_actif: bool
    date_naissance: Optional[date]
    telephone: Optional[str] = None
    nationalite: Optional[str] = None
    pays: Optional[str] = None
    region: Optional[str] = None
    ville: Optional[str] = None
    adresse: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleLight]
    permissions: List[PermissionMinLight] = []
    class Config:
        from_attributes = True
class UtilisateurMinLight(BaseModel):
    id: int
    nom: str
    prenom: Optional[str]
    sexe: SexeEnum
    email: str
    class Config:
        from_attributes = True

class PaiementLight(BaseModel):
    id: int
    inscription_id: int
    montant: float = Field(ge=0.0)
    date_paiement: datetime
    methode_paiement: MethodePaiementEnum
    reference_transaction: Optional[str] = None
    class Config:
        from_attributes = True

class FormationLight(BaseModel):
    id: int
    titre: str
    specialite: str
    statut: StatutFormationEnum
    photo_couverture: Optional[str] = None
    description: Optional[str] = None
    frais: float = Field(ge=0.0)
    class Config:
        from_attributes = True

class InscriptionFormationLight(BaseModel):
    id: int
    statut: StatutInscriptionEnum
    progression: float
    montant_verse: float
    statut_paiement: StatutPaiementEnum
    date_inscription: datetime  # Champ requis
    utilisateur: UtilisateurLight  # Champ requis
    formation: FormationLight      # Champ requis
    paiements: List[PaiementLight] = []

    class Config:
        from_attributes = True

class ModuleLight(BaseModel):
    id: int
    titre: str
    ordre: int
    photo_couverture: str
    class Config:
        from_attributes = True

class RessourceLight(BaseModel):
    id: int
    titre: str
    type: FileTypeEnum
    class Config:
        from_attributes = True

class ChefDOeuvreLight(BaseModel):
    id: int
    titre: str
    statut: StatutProjetIndividuelEnum
    class Config:
        from_attributes = True

class ProjetCollectifLight(BaseModel):
    id: int
    titre: str
    statut: StatutProjetCollectifEnum
    class Config:
        from_attributes = True

class EvaluationLight(BaseModel):
    id: int
    titre: str
    type: EvaluationTypeEnum
    class Config:
        from_attributes = True

class QuestionLight(BaseModel):
    id: int
    type: EvaluationTypeEnum
    contenu: str
    class Config:
        from_attributes = True

class PropositionLight(BaseModel):
    id: int
    texte: str
    est_correcte: bool
    class Config:
        from_attributes = True

class ResultatEvaluationLight(BaseModel):
    id: int
    note: Optional[float] = None
    date_soumission: Optional[datetime] = None
    class Config:
        from_attributes = True

class GenotypeIndividuelLight(BaseModel):
    id: int
    type: GenotypeTypeEnum
    nom: str
    prenom: Optional[str] = None
    class Config:
        from_attributes = True

class AscendanceGenotypeLight(BaseModel):
    id: int
    nom_pere: Optional[str] = None
    nom_mere: Optional[str] = None
    class Config:
        from_attributes = True

class SanteGenotypeLight(BaseModel):
    id: int
    groupe_sanguin: Optional[str] = None
    class Config:
        from_attributes = True

class EducationGenotypeLight(BaseModel):
    id: int
    derniere_classe: Optional[str] = None
    class Config:
        from_attributes = True

class PlanInterventionIndividualiseLight(BaseModel):
    id: int
    statut: StatutEnum
    class Config:
        from_attributes = True

class AccreditationLight(BaseModel):
    id: int
    etablissement: str
    statut: StatutEnum
    class Config:
        from_attributes = True

class ActualiteLight(BaseModel):
    id: int
    titre: str
    slug: str
    date_publication: date
    class Config:
        from_attributes = True

# ==================================================================
# ========================= SCHÉMAS COMPLETS =======================
# ==================================================================

class loginSchema(BaseModel):
    email: str
    password: str

class Permission(BaseModel):
    id: int
    nom: PermissionEnum
    roles: List[RoleLight] = []
    utilisateurs: List[UtilisateurLight] = []
    class Config:
        from_attributes = True

class Role(BaseModel):
    id: int
    nom: RoleEnum
    permissions: List[PermissionMinLight] = []

    class Config:
        from_attributes = True

class Utilisateur(BaseModel):
    id: int
    nom: str = Field(..., max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    sexe: SexeEnum
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)
    statut: StatutCompteEnum = StatutCompteEnum.INACTIF
    est_actif: bool = True
    last_password_change: Optional[datetime] = None
    date_naissance: Optional[date] = None
    telephone: Optional[str] = Field(None, max_length=30)
    nationalite: Optional[str] = Field(None, max_length=100)
    pays: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    ville: Optional[str] = Field(None, max_length=100)
    adresse: Optional[str] = Field(None, max_length=255)
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleLight] = None
    permissions: List[PermissionLight] = []
    inscriptions: List[InscriptionFormationLight] = []
    genotypes: List[GenotypeIndividuelLight] = []
    plans_intervention: List[PlanInterventionIndividualiseLight] = []
    actualites: List[ActualiteLight] = []
    accreditations: List[AccreditationLight] = []
    chefs_d_oeuvre: List[ChefDOeuvreLight] = []
    projets_collectifs: List[ProjetCollectifLight] = []
    resultats_evaluations: List[ResultatEvaluationLight] = []
    class Config:
        from_attributes = True

class Paiement(BaseModel):
    id: int
    inscription: InscriptionFormationLight
    montant: float = Field(ge=0.0)
    date_paiement: datetime
    methode_paiement: MethodePaiementEnum
    reference_transaction: Optional[str] = None
    class Config:
        from_attributes = True

class InscriptionFormation(BaseModel):
    id: int
    utilisateur: UtilisateurLight
    formation: FormationLight
    statut: StatutInscriptionEnum = StatutInscriptionEnum.EN_COURS
    progression: float = Field(0.0, ge=0.0, le=100.0)
    date_inscription: datetime
    date_dernier_acces: Optional[datetime] = None
    note_finale: Optional[float] = None
    heures_formation: float = Field(0.0, ge=0.0)
    montant_verse: float = Field(0.0, ge=0.0)
    statut_paiement: StatutPaiementEnum = StatutPaiementEnum.AUCUN_VERSEMENT
    paiements: List[PaiementLight] = []
    class Config:
        from_attributes = True

class Formation(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    photo_couverture: str = Field(..., max_length=255)
    description: Optional[str] = None
    specialite: str = Field(..., max_length=255)
    duree_mois: int = Field(12, ge=1)
    statut: StatutFormationEnum = StatutFormationEnum.EN_ATTENTE
    frais: float = Field(0.0, ge=0.0)
    date_debut: date
    date_fin: date
    created_at: datetime
    updated_at: datetime
    modules: List[ModuleLight] = []
    inscriptions: List[InscriptionFormationLight] = []
    projets_collectifs: List[ProjetCollectifLight] = []
    accreditations: List[AccreditationLight] = []
    class Config:
        from_attributes = True

class Module(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    photo_couverture: str = Field(..., max_length=255)
    description: Optional[str] = None
    ordre: int = Field(..., ge=1)
    formation: FormationLight
    ressources: List[RessourceLight] = []
    evaluations: List[EvaluationLight] = []
    chefs_d_oeuvre: List[ChefDOeuvreLight] = []
    class Config:
        from_attributes = True

class Ressource(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    type: FileTypeEnum
    contenu: Optional[str] = None
    lien: Optional[str] = Field(None, max_length=255)
    ordre: int = Field(..., ge=1)
    module: ModuleLight
    class Config:
        from_attributes = True

class ChefDOeuvre(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    utilisateur: UtilisateurLight
    module: ModuleLight
    statut: StatutProjetIndividuelEnum = StatutProjetIndividuelEnum.EN_COURS
    date_soumission: Optional[datetime] = None
    note: Optional[float] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class ProjetCollectif(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    formation: FormationLight
    statut: StatutProjetCollectifEnum = StatutProjetCollectifEnum.EN_COURS
    date_debut: datetime
    date_fin: datetime
    membres: List[UtilisateurLight] = []
    class Config:
        from_attributes = True

class Evaluation(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    type: EvaluationTypeEnum
    consigne: Optional[str] = None
    module: ModuleLight
    questions: List[QuestionLight] = []
    resultats: List[ResultatEvaluationLight] = []
    class Config:
        from_attributes = True

class Question(BaseModel):
    id: int
    type: EvaluationTypeEnum
    contenu: str
    piece_jointe: Optional[str] = Field(None, max_length=255)
    evaluation: EvaluationLight
    propositions: List[PropositionLight] = []
    class Config:
        from_attributes = True

class Proposition(BaseModel):
    id: int
    texte: str
    est_correcte: bool = False
    question: QuestionLight
    class Config:
        from_attributes = True

class ResultatEvaluation(BaseModel):
    id: int
    utilisateur: UtilisateurLight
    evaluation: EvaluationLight
    note: Optional[float] = None
    date_soumission: Optional[datetime] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class GenotypeIndividuel(BaseModel):
    id: int
    type: GenotypeTypeEnum
    utilisateur: UtilisateurLight
    nom: str = Field(..., max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, ge=0)
    sexe: Optional[SexeEnum] = None
    motif_detention: Optional[str] = None
    date_debut_detention: Optional[date] = None
    duree_detention: Optional[str] = Field(None, max_length=50)
    pays_detention: Optional[str] = Field(None, max_length=255)
    maison_detention: Optional[str] = Field(None, max_length=255)
    profession: Optional[str] = Field(None, max_length=255)
    activite_avant_detention: Optional[str] = None
    ascendance: Optional[AscendanceGenotypeLight] = None
    sante: Optional[SanteGenotypeLight] = None
    education: Optional[EducationGenotypeLight] = None
    plans_intervention: List[PlanInterventionIndividualiseLight] = []
    class Config:
        from_attributes = True

class AscendanceGenotype(BaseModel):
    id: int
    genotype: GenotypeIndividuelLight
    nom_pere: Optional[str] = Field(None, max_length=255)
    age_pere: Optional[int] = Field(None, ge=0)
    tribu_pere: Optional[str] = Field(None, max_length=255)
    ethnie_pere: Optional[str] = Field(None, max_length=255)
    religion_pere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_pere: Optional[str] = Field(None, max_length=255)
    profession_pere: Optional[str] = Field(None, max_length=255)
    domicile_pere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_pere: Optional[str] = Field(None, max_length=255)
    nom_mere: Optional[str] = Field(None, max_length=255)
    age_mere: Optional[int] = Field(None, ge=0)
    tribu_mere: Optional[str] = Field(None, max_length=255)
    ethnie_mere: Optional[str] = Field(None, max_length=255)
    religion_mere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_mere: Optional[str] = Field(None, max_length=255)
    profession_mere: Optional[str] = Field(None, max_length=255)
    domicile_mere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_mere: Optional[str] = Field(None, max_length=255)
    class Config:
        from_attributes = True

class SanteGenotype(BaseModel):
    id: int
    genotype: GenotypeIndividuelLight
    maladie_chronique: Optional[str] = None
    maladie_frequente: Optional[str] = None
    maladie_haut_risque: Optional[str] = None
    situation_vaccinale: Optional[str] = None
    antecedents_medicaux: Optional[str] = None
    maladie_hereditaire: Optional[str] = None
    handicap: Optional[str] = None
    allergie: Optional[str] = None
    groupe_sanguin: Optional[str] = Field(None, max_length=10)
    rhesus: Optional[str] = Field(None, max_length=10)
    class Config:
        from_attributes = True

class EducationGenotype(BaseModel):
    id: int
    genotype: GenotypeIndividuelLight
    etablissements_frequentes: Optional[str] = None
    derniere_classe: Optional[str] = Field(None, max_length=255)
    date_arret_cours: Optional[date] = None
    raisons_decrochage: Optional[str] = None
    class Config:
        from_attributes = True

class PlanInterventionIndividualise(BaseModel):
    id: int
    genotype: GenotypeIndividuelLight
    utilisateur: UtilisateurLight
    description: str
    objectifs: Optional[str] = None
    statut: StatutEnum = StatutEnum.EN_COURS
    date_creation: datetime
    date_mise_a_jour: datetime
    class Config:
        from_attributes = True

class Accreditation(BaseModel):
    id: int
    utilisateur: UtilisateurLight
    formation: FormationLight
    etablissement: str = Field(..., max_length=255)
    date_emission: datetime
    date_expiration: Optional[datetime] = None
    statut: StatutEnum = StatutEnum.PLANIFIEE
    class Config:
        from_attributes = True

class Actualite(BaseModel):
    id: int
    titre: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    categorie: str = Field(..., max_length=100)
    chapeau: str
    contenu_html: str
    image_url: Optional[str] = Field(None, max_length=255)
    date_publication: date
    date_debut_formation: Optional[date] = None
    date_fin_formation: Optional[date] = None
    document_url: Optional[str] = Field(None, max_length=255)
    auteur: str = Field(..., max_length=150)
    created_at: datetime
    updated_at: datetime
    utilisateur: UtilisateurLight
    class Config:
        from_attributes = True

# ==================================================================
# ========================= SCHÉMAS CREATE =========================
# ==================================================================

class PermissionCreate(BaseModel):
    nom: PermissionEnum
    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    nom: RoleEnum
    permission_ids: List[int] = []
    class Config:
        from_attributes = True

class UtilisateurCreate(BaseModel):
    nom: str = Field(..., max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    sexe: SexeEnum
    email: str = Field(..., max_length=255)
    role_name: RoleEnum
    date_naissance: Optional[date] = None
    telephone: Optional[str] = Field(None, max_length=30)
    nationalite: Optional[str] = Field(None, max_length=100)
    pays: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    ville: Optional[str] = Field(None, max_length=100)
    adresse: Optional[str] = Field(None, max_length=255)
    class Config:
        from_attributes = True

class PaiementCreate(BaseModel):
    inscription_id: int
    montant: float = Field(ge=0.0)
    methode_paiement: MethodePaiementEnum
    reference_transaction: Optional[str] = None
    class Config:
        from_attributes = True

class InscriptionFormationCreate(BaseModel):
    utilisateur_id: int
    formation_id: int
    statut: StatutInscriptionEnum = StatutInscriptionEnum.EN_COURS
    progression: float = Field(0.0, ge=0.0, le=100.0)
    date_inscription: datetime
    date_dernier_acces: Optional[datetime] = None
    note_finale: Optional[float] = None
    heures_formation: float = Field(0.0, ge=0.0)
    montant_verse: float = Field(0.0, ge=0.0)
    statut_paiement: StatutPaiementEnum = StatutPaiementEnum.AUCUN_VERSEMENT
    class Config:
        from_attributes = True

class FormationCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    photo_couverture: str = Field(..., max_length=255)
    description: Optional[str] = None
    specialite: str = Field(..., max_length=255)
    duree_mois: int = Field(12, ge=1)
    statut: StatutFormationEnum = StatutFormationEnum.EN_ATTENTE
    frais: float = Field(0.0, ge=0.0)
    date_debut: date
    date_fin: date
    class Config:
        from_attributes = True

class ModuleCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    photo_couverture: str = Field(..., max_length=255)
    description: Optional[str] = None
    formation_id: int
    class Config:
        from_attributes = True

class RessourceCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    type: FileTypeEnum
    contenu: Optional[str] = None
    lien: Optional[str] = Field(None, max_length=255)
    ordre: int = Field(..., ge=1)
    module_id: int
    class Config:
        from_attributes = True

class ChefDOeuvreCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    utilisateur_id: int
    module_id: int
    statut: StatutProjetIndividuelEnum = StatutProjetIndividuelEnum.EN_COURS
    date_soumission: Optional[datetime] = None
    note: Optional[float] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class ProjetCollectifCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    formation_id: int
    statut: StatutProjetCollectifEnum = StatutProjetCollectifEnum.EN_COURS
    date_debut: datetime
    date_fin: datetime
    membre_ids: List[int] = []
    class Config:
        from_attributes = True

class EvaluationCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    type: EvaluationTypeEnum
    consigne: Optional[str] = None
    module_id: int
    class Config:
        from_attributes = True

class PropositionCreate(BaseModel):
    texte: str
    est_correcte: bool = False
    question_id: int
    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    type: EvaluationTypeEnum
    contenu: str
    piece_jointe: Optional[str] = Field(None, max_length=255)
    evaluation_id: int
    propositions: List[PropositionCreate] = []
    class Config:
        from_attributes = True

class ResultatEvaluationCreate(BaseModel):
    utilisateur_id: int
    evaluation_id: int
    note: Optional[float] = None
    date_soumission: Optional[datetime] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class GenotypeIndividuelCreate(BaseModel):
    type: GenotypeTypeEnum
    utilisateur_id: int
    nom: str = Field(..., max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, ge=0)
    sexe: Optional[SexeEnum] = None
    motif_detention: Optional[str] = None
    date_debut_detention: Optional[date] = None
    duree_detention: Optional[str] = Field(None, max_length=50)
    pays_detention: Optional[str] = Field(None, max_length=255)
    maison_detention: Optional[str] = Field(None, max_length=255)
    profession: Optional[str] = Field(None, max_length=255)
    activite_avant_detention: Optional[str] = None
    class Config:
        from_attributes = True

class AscendanceGenotypeCreate(BaseModel):
    genotype_id: int
    nom_pere: Optional[str] = Field(None, max_length=255)
    age_pere: Optional[int] = Field(None, ge=0)
    tribu_pere: Optional[str] = Field(None, max_length=255)
    ethnie_pere: Optional[str] = Field(None, max_length=255)
    religion_pere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_pere: Optional[str] = Field(None, max_length=255)
    profession_pere: Optional[str] = Field(None, max_length=255)
    domicile_pere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_pere: Optional[str] = Field(None, max_length=255)
    nom_mere: Optional[str] = Field(None, max_length=255)
    age_mere: Optional[int] = Field(None, ge=0)
    tribu_mere: Optional[str] = Field(None, max_length=255)
    ethnie_mere: Optional[str] = Field(None, max_length=255)
    religion_mere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_mere: Optional[str] = Field(None, max_length=255)
    profession_mere: Optional[str] = Field(None, max_length=255)
    domicile_mere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_mere: Optional[str] = Field(None, max_length=255)
    class Config:
        from_attributes = True

class SanteGenotypeCreate(BaseModel):
    genotype_id: int
    maladie_chronique: Optional[str] = None
    maladie_frequente: Optional[str] = None
    maladie_haut_risque: Optional[str] = None
    situation_vaccinale: Optional[str] = None
    antecedents_medicaux: Optional[str] = None
    maladie_hereditaire: Optional[str] = None
    handicap: Optional[str] = None
    allergie: Optional[str] = None
    groupe_sanguin: Optional[str] = Field(None, max_length=10)
    rhesus: Optional[str] = Field(None, max_length=10)
    class Config:
        from_attributes = True

class EducationGenotypeCreate(BaseModel):
    genotype_id: int
    etablissements_frequentes: Optional[str] = None
    derniere_classe: Optional[str] = Field(None, max_length=255)
    date_arret_cours: Optional[date] = None
    raisons_decrochage: Optional[str] = None
    class Config:
        from_attributes = True

class PlanInterventionIndividualiseCreate(BaseModel):
    genotype_id: int
    utilisateur_id: int
    description: str
    objectifs: Optional[str] = None
    statut: StatutEnum = StatutEnum.EN_COURS
    date_creation: datetime
    class Config:
        from_attributes = True

class AccreditationCreate(BaseModel):
    utilisateur_id: int
    formation_id: int
    etablissement: str = Field(..., max_length=255)
    date_emission: datetime
    date_expiration: Optional[datetime] = None
    statut: StatutEnum = StatutEnum.PLANIFIEE
    class Config:
        from_attributes = True

class ActualiteCreate(BaseModel):
    titre: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    categorie: str = Field(..., max_length=100)
    chapeau: str
    contenu_html: str
    image_url: Optional[str] = Field(None, max_length=255)
    date_publication: date
    date_debut_formation: Optional[date] = None
    date_fin_formation: Optional[date] = None
    document_url: Optional[str] = None
    auteur: str = Field(..., max_length=150)
    utilisateur_id: int
    class Config:
        from_attributes = True

# ==================================================================
# ========================= SCHÉMAS UPDATE =========================
# ==================================================================

class PermissionUpdate(BaseModel):
    nom: Optional[PermissionEnum] = None
    class Config:
        from_attributes = True

class RoleUpdate(BaseModel):
    nom: Optional[RoleEnum] = None
    permission_ids: Optional[List[int]] = None
    class Config:
        from_attributes = True

class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = Field(None, max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    sexe: Optional[SexeEnum] = None
    email: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=128)
    statut: Optional[StatutCompteEnum] = None
    est_actif: Optional[bool] = None
    date_naissance: Optional[date] = None
    telephone: Optional[str] = Field(None, max_length=30)
    nationalite: Optional[str] = Field(None, max_length=100)
    pays: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    ville: Optional[str] = Field(None, max_length=100)
    adresse: Optional[str] = Field(None, max_length=255)
    role_id: Optional[int] = None
    permission_ids: Optional[List[int]] = None
    class Config:
        from_attributes = True

class PaiementUpdate(BaseModel):
    inscription_id: Optional[int] = None
    montant: Optional[float] = Field(None, ge=0.0)
    methode_paiement: Optional[MethodePaiementEnum] = None
    reference_transaction: Optional[str] = None
    class Config:
        from_attributes = True

class InscriptionFormationUpdate(BaseModel):
    utilisateur_id: Optional[int] = None
    formation_id: Optional[int] = None
    statut: Optional[StatutInscriptionEnum] = None
    progression: Optional[float] = Field(None, ge=0.0, le=100.0)
    date_dernier_acces: Optional[datetime] = None
    note_finale: Optional[float] = None
    heures_formation: Optional[float] = Field(None, ge=0.0)
    montant_verse: Optional[float] = Field(None, ge=0.0)
    statut_paiement: Optional[StatutPaiementEnum] = None
    class Config:
        from_attributes = True

class FormationUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    photo_couverture: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    specialite: Optional[str] = Field(None, max_length=255)
    duree_mois: Optional[int] = Field(None, ge=1)
    statut: Optional[StatutFormationEnum] = None
    frais: Optional[float] = Field(None, ge=0.0)
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    class Config:
        from_attributes = True

class ModuleUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    photo_couverture: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    formation_id: Optional[int] = None
    class Config:
        from_attributes = True

class RessourceUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    type: Optional[FileTypeEnum] = None
    contenu: Optional[str] = None
    lien: Optional[str] = Field(None, max_length=255)
    ordre: Optional[int] = Field(None, ge=1)
    module_id: Optional[int] = None
    class Config:
        from_attributes = True

class ChefDOeuvreUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    utilisateur_id: Optional[int] = None
    module_id: Optional[int] = None
    statut: Optional[StatutProjetIndividuelEnum] = None
    date_soumission: Optional[datetime] = None
    note: Optional[float] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class ProjetCollectifUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    formation_id: Optional[int] = None
    statut: Optional[StatutProjetCollectifEnum] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    membre_ids: Optional[List[int]] = None
    class Config:
        from_attributes = True

class EvaluationUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    type: Optional[EvaluationTypeEnum] = None
    consigne: Optional[str] = None
    module_id: Optional[int] = None
    class Config:
        from_attributes = True

class PropositionUpdate(BaseModel):
    texte: Optional[str] = None
    est_correcte: Optional[bool] = None
    question_id: Optional[int] = None
    class Config:
        from_attributes = True

class QuestionUpdate(BaseModel):
    type: Optional[EvaluationTypeEnum] = None
    contenu: Optional[str] = None
    piece_jointe: Optional[str] = Field(None, max_length=255)
    evaluation_id: Optional[int] = None
    propositions: Optional[List[PropositionUpdate]] = None
    class Config:
        from_attributes = True

class ResultatEvaluationUpdate(BaseModel):
    utilisateur_id: Optional[int] = None
    evaluation_id: Optional[int] = None
    note: Optional[float] = None
    date_soumission: Optional[datetime] = None
    commentaires: Optional[str] = None
    class Config:
        from_attributes = True

class GenotypeIndividuelUpdate(BaseModel):
    type: Optional[GenotypeTypeEnum] = None
    utilisateur_id: Optional[int] = None
    nom: Optional[str] = Field(None, max_length=255)
    prenom: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, ge=0)
    sexe: Optional[SexeEnum] = None
    motif_detention: Optional[str] = None
    date_debut_detention: Optional[date] = None
    duree_detention: Optional[str] = Field(None, max_length=50)
    pays_detention: Optional[str] = Field(None, max_length=255)
    maison_detention: Optional[str] = Field(None, max_length=255)
    profession: Optional[str] = Field(None, max_length=255)
    activite_avant_detention: Optional[str] = None
    class Config:
        from_attributes = True

class AscendanceGenotypeUpdate(BaseModel):
    genotype_id: Optional[int] = None
    nom_pere: Optional[str] = Field(None, max_length=255)
    age_pere: Optional[int] = Field(None, ge=0)
    tribu_pere: Optional[str] = Field(None, max_length=255)
    ethnie_pere: Optional[str] = Field(None, max_length=255)
    religion_pere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_pere: Optional[str] = Field(None, max_length=255)
    profession_pere: Optional[str] = Field(None, max_length=255)
    domicile_pere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_pere: Optional[str] = Field(None, max_length=255)
    nom_mere: Optional[str] = Field(None, max_length=255)
    age_mere: Optional[int] = Field(None, ge=0)
    tribu_mere: Optional[str] = Field(None, max_length=255)
    ethnie_mere: Optional[str] = Field(None, max_length=255)
    religion_mere: Optional[str] = Field(None, max_length=255)
    situation_matrimoniale_mere: Optional[str] = Field(None, max_length=255)
    profession_mere: Optional[str] = Field(None, max_length=255)
    domicile_mere: Optional[str] = Field(None, max_length=255)
    proprietaire_domicile_mere: Optional[str] = Field(None, max_length=255)
    class Config:
        from_attributes = True

class SanteGenotypeUpdate(BaseModel):
    genotype_id: Optional[int] = None
    maladie_chronique: Optional[str] = None
    maladie_frequente: Optional[str] = None
    maladie_haut_risque: Optional[str] = None
    situation_vaccinale: Optional[str] = None
    antecedents_medicaux: Optional[str] = None
    maladie_hereditaire: Optional[str] = None
    handicap: Optional[str] = None
    allergie: Optional[str] = None
    groupe_sanguin: Optional[str] = Field(None, max_length=10)
    rhesus: Optional[str] = Field(None, max_length=10)
    class Config:
        from_attributes = True

class EducationGenotypeUpdate(BaseModel):
    genotype_id: Optional[int] = None
    etablissements_frequentes: Optional[str] = None
    derniere_classe: Optional[str] = Field(None, max_length=255)
    date_arret_cours: Optional[date] = None
    raisons_decrochage: Optional[str] = None
    class Config:
        from_attributes = True

class PlanInterventionIndividualiseUpdate(BaseModel):
    genotype_id: Optional[int] = None
    utilisateur_id: Optional[int] = None
    description: Optional[str] = None
    objectifs: Optional[str] = None
    statut: Optional[StatutEnum] = None
    class Config:
        from_attributes = True

class AccreditationUpdate(BaseModel):
    utilisateur_id: Optional[int] = None
    formation_id: Optional[int] = None
    etablissement: Optional[str] = Field(None, max_length=255)
    date_emission: Optional[datetime] = None
    date_expiration: Optional[datetime] = None
    statut: Optional[StatutEnum] = None
    class Config:
        from_attributes = True

class ActualiteUpdate(BaseModel):
    titre: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    categorie: Optional[str] = Field(None, max_length=100)
    chapeau: Optional[str] = None
    contenu_html: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=255)
    date_publication: Optional[date] = None
    date_debut_formation: Optional[date] = None
    date_fin_formation: Optional[date] = None
    document_url: Optional[str] = Field(None, max_length=255)
    auteur: Optional[str] = Field(None, max_length=150)
    utilisateur_id: Optional[int] = None
    class Config:
        from_attributes = True

class ResetPasswordRequestSchema(BaseModel):
    email: str

class ChangePasswordSchema(BaseModel):
    utilisateur_id: int
    current_password: str
    new_password: str