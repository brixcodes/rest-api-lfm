from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from src.util.helper.enum import (
    CiviliteEnum, DeviseEnum, MethodePaiementEnum, ModaliteEnum,
    RoleEnum, SpecialiteEnum, StatutCandidatureEnum, StatutPaiementEnum, StatutReclamationEnum,
    TypeFormationEnum, TypePaiementEnum, TypeRessourceEnum, StatutSessionEnum,
    TypeEvaluationEnum, StatutEvaluationEnum, StatutResultatEnum, TypeCorrectionEnum
)

# Adresse Schemas
class AdresseCreate(BaseModel):
    type_adresse: str = Field(..., max_length=50)
    pays: Optional[str] = Field(None, max_length=100)
    ville: Optional[str] = Field(None, max_length=120)
    rue: Optional[str] = Field(None, max_length=255)
    code_postal: Optional[str] = Field(None, max_length=50)
    province: Optional[str] = Field(None, max_length=120)
    
    # Champs de facturation
    pays_facturation: Optional[str] = Field(None, max_length=100)
    ville_facturation: Optional[str] = Field(None, max_length=120)
    rue_facturation: Optional[str] = Field(None, max_length=255)
    code_postal_facturation: Optional[str] = Field(None, max_length=50)
    province_facturation: Optional[str] = Field(None, max_length=120)

class AdresseUpdate(BaseModel):
    type_adresse: Optional[str] = Field(None, max_length=50)
    pays: Optional[str] = Field(None, max_length=100)
    ville: Optional[str] = Field(None, max_length=120)
    rue: Optional[str] = Field(None, max_length=255)
    code_postal: Optional[str] = Field(None, max_length=50)
    province: Optional[str] = Field(None, max_length=120)
    
    # Champs de facturation
    pays_facturation: Optional[str] = Field(None, max_length=100)
    ville_facturation: Optional[str] = Field(None, max_length=120)
    rue_facturation: Optional[str] = Field(None, max_length=255)
    code_postal_facturation: Optional[str] = Field(None, max_length=50)
    province_facturation: Optional[str] = Field(None, max_length=120)

class AdresseLight(BaseModel):
    id: int
    type_adresse: str
    pays: Optional[str]
    ville: Optional[str]
    
    # Champs de facturation de base
    pays_facturation: Optional[str]
    ville_facturation: Optional[str]

class AdresseResponse(BaseModel):
    id: int
    type_adresse: str
    utilisateur_id: int
    
    # Adresse principale
    pays: Optional[str]
    ville: Optional[str]
    rue: Optional[str]
    code_postal: Optional[str]
    province: Optional[str]
    
    # Champs de facturation
    pays_facturation: Optional[str]
    ville_facturation: Optional[str]
    rue_facturation: Optional[str]
    code_postal_facturation: Optional[str]
    province_facturation: Optional[str]
    
    created_at: datetime
    updated_at: datetime

# Utilisateur Schemas
class UtilisateurCreate(BaseModel):
    civilite: Optional[CiviliteEnum] = None
    nom: str = Field(..., max_length=100)
    prenom: str = Field(..., max_length=100)
    email: str = Field(..., max_length=120)
    telephone: Optional[str] = Field(None, max_length=30)
    nationalite: Optional[str] = Field(None, max_length=100)
    role: RoleEnum = RoleEnum.CANDIDAT
    actif: bool = True

class UtilisateurUpdate(BaseModel):
    civilite: Optional[CiviliteEnum] = None
    nom: Optional[str] = Field(None, max_length=100)
    prenom: Optional[str] = Field(None, max_length=100)
    date_naissance: Optional[date] = None
    email: Optional[str] = Field(None, max_length=120)
    telephone_mobile: Optional[str] = Field(None, max_length=30)
    telephone: Optional[str] = Field(None, max_length=30)
    nationalite: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    role: Optional[RoleEnum] = None
    actif: Optional[bool] = None
    email_verified: Optional[bool] = None
    last_login: Optional[datetime] = None
    situation_professionnelle: Optional[str] = Field(None, max_length=120)
    experience_professionnelle_en_mois: Optional[int] = None
    employeur: Optional[str] = Field(None, max_length=120)
    categorie_socio_professionnelle: Optional[str] = Field(None, max_length=120)
    fonction: Optional[str] = Field(None, max_length=120)
    dernier_diplome_obtenu: Optional[str] = Field(None, max_length=120)
    date_obtention_dernier_diplome: Optional[date] = None
    adresses: Optional[List[AdresseCreate]] = None

class UtilisateurLight(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    nationalite: str
    role: RoleEnum

class UtilisateurResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: RoleEnum
    civilite: Optional[CiviliteEnum]
    date_naissance: Optional[date]
    telephone_mobile: Optional[str]
    telephone: Optional[str]
    nationalite: Optional[str]
    actif: bool
    email_verified: bool
    last_login: Optional[datetime]
    situation_professionnelle: Optional[str]
    experience_professionnelle_en_mois: Optional[int]
    employeur: Optional[str]
    categorie_socio_professionnelle: Optional[str]
    fonction: Optional[str]
    dernier_diplome_obtenu: Optional[str]
    date_obtention_dernier_diplome: Optional[date]
    created_at: datetime
    updated_at: datetime
    adresses: Optional[List[AdresseResponse]] = None
    dossiers: Optional[List["DossierCandidatureLight"]] = None
    reclamations: Optional[List["ReclamationLight"]] = None

# Schémas pour la gestion des mots de passe
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Mot de passe actuel")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe (min 8 caractères)")

class PasswordResetByEmailRequest(BaseModel):
    email: str = Field(..., description="Email de l'utilisateur pour réinitialisation du mot de passe")

class PasswordResetByEmailResponse(BaseModel):
    message: str
    email: str
    new_password: str  # À supprimer en production

class PasswordChangeResponse(BaseModel):
    message: str
    user_id: int

# Schémas pour l'authentification
class LoginRequest(BaseModel):
    email: str = Field(..., description="Email de l'utilisateur")
    password: str = Field(..., description="Mot de passe de l'utilisateur")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UtilisateurLight
    message: str = "Connexion réussie"

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[RoleEnum] = None

# ──────────────────────────────────────────────────────────────
# Schémas pour le système d'évaluation et de certification
# ──────────────────────────────────────────────────────────────

# Schémas pour les évaluations
class QuestionEvaluationCreate(BaseModel):
    question: str = Field(..., description="Texte de la question")
    type_question: str = Field(..., description="Type de question (choix_multiple, texte_libre, fichier)")
    ordre: int = Field(0, description="Ordre de la question dans l'évaluation")
    reponses_possibles: Optional[str] = Field(None, description="JSON des réponses possibles pour QCM")
    reponse_correcte: Optional[str] = Field(None, description="Réponse correcte attendue")
    points: float = Field(1.0, description="Points attribués à cette question")

class QuestionEvaluationUpdate(BaseModel):
    question: Optional[str] = None
    type_question: Optional[str] = None
    ordre: Optional[int] = None
    reponses_possibles: Optional[str] = None
    reponse_correcte: Optional[str] = None
    points: Optional[float] = None

class QuestionEvaluationResponse(BaseModel):
    id: int
    evaluation_id: int
    question: str
    type_question: str
    ordre: int
    reponses_possibles: Optional[str] = None
    reponse_correcte: Optional[str] = None
    points: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QuestionEvaluationLight(BaseModel):
    id: int
    question: str
    type_question: str
    ordre: int
    points: float

    class Config:
        from_attributes = True

class EvaluationCreate(BaseModel):
    session_id: int = Field(..., description="ID de la session de formation")
    formateur_id: Optional[int] = Field(None, description="ID du formateur créateur")
    titre: str = Field(..., description="Titre de l'évaluation")
    description: Optional[str] = Field(None, description="Description de l'évaluation")
    type_evaluation: TypeEvaluationEnum = Field(..., description="Type d'évaluation")
    date_ouverture: Optional[datetime] = Field(None, description="Date d'ouverture")
    date_fermeture: Optional[datetime] = Field(None, description="Date de fermeture")
    duree_minutes: Optional[int] = Field(None, description="Durée maximale en minutes")
    ponderation: float = Field(100.0, description="Pondération dans la note finale (%)")
    note_minimale: float = Field(10.0, description="Note minimale pour réussir")
    nombre_tentatives_max: int = Field(1, description="Nombre de tentatives autorisées")
    type_correction: TypeCorrectionEnum = Field(..., description="Type de correction")
    instructions: Optional[str] = Field(None, description="Instructions pour les candidats")
    consignes_correction: Optional[str] = Field(None, description="Consignes pour les correcteurs")
    questions: Optional[List[QuestionEvaluationCreate]] = Field([], description="Liste des questions")

class EvaluationUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    type_evaluation: Optional[TypeEvaluationEnum] = None
    statut: Optional[StatutEvaluationEnum] = None
    date_ouverture: Optional[datetime] = None
    date_fermeture: Optional[datetime] = None
    duree_minutes: Optional[int] = None
    ponderation: Optional[float] = None
    note_minimale: Optional[float] = None
    nombre_tentatives_max: Optional[int] = None
    type_correction: Optional[TypeCorrectionEnum] = None
    instructions: Optional[str] = None
    consignes_correction: Optional[str] = None

class EvaluationResponse(BaseModel):
    id: int
    session_id: int
    formateur_id: Optional[int] = None
    titre: str
    description: Optional[str] = None
    type_evaluation: TypeEvaluationEnum
    statut: StatutEvaluationEnum
    date_ouverture: Optional[datetime] = None
    date_fermeture: Optional[datetime] = None
    duree_minutes: Optional[int] = None
    ponderation: float
    note_minimale: float
    nombre_tentatives_max: int
    type_correction: TypeCorrectionEnum
    instructions: Optional[str] = None
    consignes_correction: Optional[str] = None
    questions: List[QuestionEvaluationResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EvaluationLight(BaseModel):
    id: int
    titre: str
    type_evaluation: TypeEvaluationEnum
    statut: StatutEvaluationEnum
    date_ouverture: Optional[datetime] = None
    date_fermeture: Optional[datetime] = None
    ponderation: float
    note_minimale: float

    class Config:
        from_attributes = True

# Schémas pour les réponses des candidats
class ReponseCandidatCreate(BaseModel):
    question_id: int = Field(..., description="ID de la question")
    reponse_texte: Optional[str] = Field(None, description="Réponse textuelle")
    reponse_fichier_url: Optional[str] = Field(None, description="URL du fichier uploadé")
    reponse_json: Optional[str] = Field(None, description="Réponse au format JSON")

class ReponseCandidatUpdate(BaseModel):
    reponse_texte: Optional[str] = None
    reponse_fichier_url: Optional[str] = None
    reponse_json: Optional[str] = None

class ReponseCandidatResponse(BaseModel):
    id: int
    resultat_id: int
    question_id: int
    reponse_texte: Optional[str] = None
    reponse_fichier_url: Optional[str] = None
    reponse_json: Optional[str] = None
    points_obtenus: Optional[float] = None
    points_maximaux: Optional[float] = None
    commentaire_correction: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schémas pour les résultats d'évaluation
class ResultatEvaluationCreate(BaseModel):
    evaluation_id: int = Field(..., description="ID de l'évaluation")
    candidat_id: int = Field(..., description="ID du candidat")
    tentative_numero: int = Field(1, description="Numéro de la tentative")
    reponses: List[ReponseCandidatCreate] = Field([], description="Réponses du candidat")

class ResultatEvaluationUpdate(BaseModel):
    statut: Optional[StatutResultatEnum] = None
    date_fin: Optional[datetime] = None
    note_obtenue: Optional[float] = None
    commentaire_formateur: Optional[str] = None
    commentaire_candidat: Optional[str] = None

class ResultatEvaluationResponse(BaseModel):
    id: int
    evaluation_id: int
    candidat_id: int
    tentative_numero: int
    statut: StatutResultatEnum
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    note_obtenue: Optional[float] = None
    note_maximale: Optional[float] = None
    pourcentage_reussite: Optional[float] = None
    commentaire_formateur: Optional[str] = None
    commentaire_candidat: Optional[str] = None
    reponses: List[ReponseCandidatResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResultatEvaluationLight(BaseModel):
    id: int
    evaluation_id: int
    candidat_id: int
    tentative_numero: int
    statut: StatutResultatEnum
    note_obtenue: Optional[float] = None
    pourcentage_reussite: Optional[float] = None

    class Config:
        from_attributes = True

# Schémas pour les certificats
class CertificatCreate(BaseModel):
    candidat_id: int = Field(..., description="ID du candidat")
    session_id: int = Field(..., description="ID de la session")
    titre_formation: str = Field(..., description="Titre de la formation")
    date_obtention: date = Field(..., description="Date d'obtention")
    note_finale: float = Field(..., description="Note finale obtenue")
    mention: Optional[str] = Field(None, description="Mention obtenue")
    statut_validation: str = Field("Validé", description="Statut de validation")
    commentaires: Optional[str] = Field(None, description="Commentaires")

class CertificatUpdate(BaseModel):
    mention: Optional[str] = None
    statut_validation: Optional[str] = None
    url_certificat: Optional[str] = None
    commentaires: Optional[str] = None

class CertificatResponse(BaseModel):
    id: int
    candidat_id: int
    session_id: int
    numero_certificat: str
    titre_formation: str
    date_obtention: date
    note_finale: float
    mention: Optional[str] = None
    statut_validation: str
    url_certificat: Optional[str] = None
    commentaires: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CertificatLight(BaseModel):
    id: int
    numero_certificat: str
    titre_formation: str
    date_obtention: date
    note_finale: float
    mention: Optional[str] = None
    statut_validation: str

    class Config:
        from_attributes = True

# Schémas pour les statistiques et rapports
class StatistiquesEvaluation(BaseModel):
    evaluation_id: int
    nombre_participants: int
    nombre_termines: int
    note_moyenne: float
    note_minimale: float
    note_maximale: float
    taux_reussite: float

class RapportSession(BaseModel):
    session_id: int
    formation_titre: str
    nombre_candidats: int
    nombre_certificats_delivres: int
    note_moyenne_generale: float
    evaluations: List[StatistiquesEvaluation] = []

# CentreFormation Schemas
class CentreFormationCreate(BaseModel):
    nom: str = Field(..., max_length=255)
    adresse: Optional[str] = Field(None, max_length=255)
    ville: Optional[str] = Field(None, max_length=120)
    code_postal: Optional[str] = Field(None, max_length=50)
    pays: Optional[str] = Field(None, max_length=100)

class CentreFormationUpdate(BaseModel):
    nom: Optional[str] = Field(None, max_length=255)
    adresse: Optional[str] = Field(None, max_length=255)
    ville: Optional[str] = Field(None, max_length=120)
    code_postal: Optional[str] = Field(None, max_length=50)
    pays: Optional[str] = Field(None, max_length=100)

class CentreFormationLight(BaseModel):
    id: int
    nom: str

class CentreFormationResponse(BaseModel):
    id: int
    nom: str
    adresse: Optional[str] = None
    ville: Optional[str] = None
    code_postal: Optional[str] = None
    pays: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sessions: List["SessionFormationLight"]
    
    class Config:
        # S'assurer que tous les champs sont inclus même s'ils sont None
        exclude_none = False

# InformationDescriptive Schemas
class InformationDescriptiveCreate(BaseModel):
    presentation: Optional[str] = Field(None, description="Contexte, enjeux et vision d'ensemble de la formation")
    avantages: Optional[str] = Field(None, description="Avantages et spécificités de la formation")
    points_forts: Optional[str] = Field(None, description="Points forts de la formation (liste)")
    competences_visees: Optional[str] = Field(None, description="Compétences et savoir-faire à acquérir")
    programme: Optional[str] = Field(None, description="Contenu détaillé et structure de la formation")
    profils_cibles: Optional[str] = Field(None, description="Public cible et prérequis")
    inscription: Optional[str] = Field(None, description="Modalités d'inscription, durée, rythme")
    certifications: Optional[str] = Field(None, description="Certifications et attestations disponibles")
    methode_pedagogique: Optional[str] = Field(None, description="Approche pédagogique et outils utilisés")
    evaluation: Optional[str] = Field(None, description="Modalités d'évaluation et validation")

class InformationDescriptiveUpdate(BaseModel):
    presentation: Optional[str] = Field(None, description="Contexte, enjeux et vision d'ensemble de la formation")
    avantages: Optional[str] = Field(None, description="Avantages et spécificités de la formation")
    points_forts: Optional[str] = Field(None, description="Points forts de la formation (liste)")
    competences_visees: Optional[str] = Field(None, description="Compétences et savoir-faire à acquérir")
    programme: Optional[str] = Field(None, description="Contenu détaillé et structure de la formation")
    profils_cibles: Optional[str] = Field(None, description="Public cible et prérequis")
    inscription: Optional[str] = Field(None, description="Modalités d'inscription, durée, rythme")
    certifications: Optional[str] = Field(None, description="Certifications et attestations disponibles")
    methode_pedagogique: Optional[str] = Field(None, description="Approche pédagogique et outils utilisés")
    evaluation: Optional[str] = Field(None, description="Modalités d'évaluation et validation")

class InformationDescriptiveResponse(BaseModel):
    id: int
    formation_id: int
    presentation: Optional[str]
    avantages: Optional[str]
    points_forts: Optional[str]
    competences_visees: Optional[str]
    programme: Optional[str]
    profils_cibles: Optional[str]
    inscription: Optional[str]
    certifications: Optional[str]
    methode_pedagogique: Optional[str]
    evaluation: Optional[str]
    created_at: datetime
    updated_at: datetime

# Formation Schemas
class FormationCreate(BaseModel): 
    specialite: SpecialiteEnum
    titre: str = Field(..., max_length=255)
    fiche_info: Optional[str] = None
    description: Optional[str] = None
    duree_heures: Optional[int] = None
    type_formation: Optional[TypeFormationEnum] = None
    modalite: ModaliteEnum = ModaliteEnum.EN_LIGNE
    pre_requis: Optional[str] = None
    frais_inscription: Optional[float] = None
    frais_formation: Optional[float] = None
    devise: DeviseEnum = DeviseEnum.EUR

class FormationUpdate(BaseModel):
    specialite: Optional[SpecialiteEnum] = None 
    fiche_info: Optional[str] = None
    titre: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    duree_heures: Optional[int] = None
    type_formation: Optional[TypeFormationEnum] = None
    modalite: Optional[ModaliteEnum] = None
    pre_requis: Optional[str] = None
    frais_inscription: Optional[float] = None
    frais_formation: Optional[float] = None
    devise: Optional[DeviseEnum] = None

class FormationLight(BaseModel):
    id: int
    titre: str
    specialite: SpecialiteEnum
    modalite: ModaliteEnum

class FormationResponse(FormationLight):
    description: Optional[str]
    fiche_info: Optional[str] = None
    duree_heures: Optional[int]
    type_formation: Optional[TypeFormationEnum]
    pre_requis: Optional[str]
    frais_inscription: Optional[float]
    frais_formation: Optional[float]
    devise: DeviseEnum
    created_at: datetime
    updated_at: datetime
    sessions: List["SessionFormationLight"]
    modules: List["ModuleResponse"]
    dossiers: List["DossierCandidatureLight"]
    information_descriptive: Optional[InformationDescriptiveResponse] = None

# SessionFormation Schemas
class SessionFormationCreate(BaseModel):
    formation_id: int
    centre_id: Optional[int] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    date_limite_inscription: Optional[date] = None
    places_disponibles: Optional[int] = None
    statut: StatutSessionEnum = StatutSessionEnum.OUVERTE
    modalite: Optional[ModaliteEnum] = None

class SessionFormationUpdate(BaseModel):
    formation_id: Optional[int] = None
    centre_id: Optional[int] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    date_limite_inscription: Optional[date] = None
    places_disponibles: Optional[int] = None
    statut: Optional[StatutSessionEnum] = None
    modalite: Optional[ModaliteEnum] = None

class SessionFormationLight(BaseModel):
    id: int
    formation_id: int
    date_debut: Optional[date]
    statut: StatutSessionEnum

class SessionFormationResponse(SessionFormationLight):
    centre_id: Optional[int]
    date_fin: Optional[date]
    date_limite_inscription: Optional[date]
    places_disponibles: Optional[int]
    modalite: Optional[ModaliteEnum]
    created_at: datetime
    updated_at: datetime
    formation: FormationLight
    centre: Optional[CentreFormationLight]
    dossiers: List["DossierCandidatureLight"]


# Schémas pour les opérations de changement de statut et modalité
class SessionStatutUpdate(BaseModel):
    statut: StatutSessionEnum

class SessionModaliteUpdate(BaseModel):
    modalite: ModaliteEnum

# Module Schemas
class ModuleCreate(BaseModel):
    formation_id: int
    titre: str = Field(..., max_length=255)
    description: Optional[str] = None
    ordre: Optional[int] = None
    ressources: Optional[List["RessourceCreate"]] = None

class ModuleUpdate(BaseModel):
    formation_id: Optional[int] = None
    titre: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    ordre: Optional[int] = None
    ressources: Optional[List["RessourceCreate"]] = None

class ModuleLight(BaseModel):
    id: int
    titre: str
    ordre: Optional[int]

class ModuleResponse(ModuleLight):
    formation_id: int
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    formation: FormationLight
    ressources: List["RessourceResponse"]

# Ressource Schemas
class RessourceCreate(BaseModel):
    module_id: int
    type_ressource: TypeRessourceEnum
    titre: Optional[str] = Field(None, max_length=255)
    url: str = Field(..., max_length=512)
    description: Optional[str] = None

class RessourceUpdate(BaseModel):
    module_id: Optional[int] = None
    type_ressource: Optional[TypeRessourceEnum] = None
    titre: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = None

class RessourceLight(BaseModel):
    id: int
    type_ressource: TypeRessourceEnum
    url: str

class RessourceResponse(RessourceLight):
    module_id: int
    titre: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    module: ModuleLight

# DossierCandidature Schemas
class DossierCandidatureCreate(BaseModel):
    utilisateur_id: int
    formation_id: int
    session_id: Optional[int] = None
    # numero_candidature est généré automatiquement par le système
    statut: StatutCandidatureEnum = StatutCandidatureEnum.RECUE
    date_soumission: Optional[datetime] = None
    motif_refus: Optional[str] = None
    frais_inscription_montant: Optional[float] = None
    frais_formation_montant: Optional[float] = None
    devise: Optional[DeviseEnum] = None
    # pieces_jointes: Optional[List["PieceJointeCreate"]] = None
    # paiements: Optional[List["PaiementCreate"]] = None
    # reclamations: Optional[List["ReclamationCreate"]] = None

class DossierCandidatureUpdate(BaseModel):
    utilisateur_id: Optional[int] = None
    formation_id: Optional[int] = None
    session_id: Optional[int] = None
    # numero_candidature ne peut pas être modifié par l'utilisateur
    statut: Optional[StatutCandidatureEnum] = None
    date_soumission: Optional[datetime] = None
    motif_refus: Optional[str] = None
    frais_inscription_montant: Optional[float] = None
    frais_formation_montant: Optional[float] = None
    devise: Optional[DeviseEnum] = None
    pieces_jointes: Optional[List["PieceJointeCreate"]] = None
    paiements: Optional[List["PaiementCreate"]] = None
    reclamations: Optional[List["ReclamationCreate"]] = None

# Schémas pour le changement de statut
class DossierStatutUpdate(BaseModel):
    statut: StatutCandidatureEnum
    motif_refus: Optional[str] = Field(None, max_length=500, description="Motif du refus si le statut est REFUSÉE")
    date_soumission: Optional[datetime] = Field(None, description="Date de soumission si le statut passe à EN_ETUDE ou ACCEPTÉE")
    commentaire: Optional[str] = Field(None, max_length=1000, description="Commentaire administratif sur le changement de statut")

class DossierStatutResponse(BaseModel):
    id: int
    numero_candidature: str
    ancien_statut: StatutCandidatureEnum
    nouveau_statut: StatutCandidatureEnum
    motif_refus: Optional[str]
    date_soumission: Optional[datetime]
    commentaire: Optional[str]
    date_modification: datetime
    modifie_par: Optional[str] = Field(None, description="Nom de l'utilisateur qui a modifié le statut")

class DossierCandidatureLight(BaseModel):
    id: int
    utilisateur_id: int
    formation_id: int
    statut: StatutCandidatureEnum

class DossierCandidatureResponse(DossierCandidatureLight):
    session_id: Optional[int]
    numero_candidature: Optional[str]
    date_soumission: Optional[datetime]
    motif_refus: Optional[str]
    frais_inscription_montant: Optional[float]
    frais_formation_montant: Optional[float]
    devise: Optional[DeviseEnum]
    created_at: datetime
    updated_at: datetime
    utilisateur: UtilisateurLight
    formation: FormationLight
    session: Optional[SessionFormationLight]
    reclamations: List["ReclamationLight"]
    paiements: List["PaiementLight"]
    pieces_jointes: List["PieceJointeResponse"]
    total_paye: float
    reste_a_payer_inscription: float
    reste_a_payer_formation: float

# PieceJointe Schemas
class PieceJointeCreate(BaseModel):
    dossier_id: int
    type_document: str = Field(..., max_length=100)
    chemin_fichier: str = Field(..., max_length=255)
    description: Optional[str] = None
    date_upload: Optional[datetime] = None

class PieceJointeUpdate(BaseModel):
    dossier_id: Optional[int] = None
    type_document: Optional[str] = Field(None, max_length=100)
    chemin_fichier: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    date_upload: Optional[datetime] = None

class PieceJointeLight(BaseModel):
    id: int
    type_document: str
    chemin_fichier: str

class PieceJointeResponse(PieceJointeLight):
    dossier_id: int
    description: Optional[str]
    date_upload: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    dossier: DossierCandidatureLight

# Reclamation Schemas
class ReclamationCreate(BaseModel):
    dossier_id: int
    auteur_id: int
    numero_reclamation: Optional[str] = Field(None, max_length=50)
    objet: str = Field(..., max_length=255)
    type_reclamation: Optional[str] = Field(None, max_length=100)
    priorite: Optional[str] = Field(None, max_length=50)
    statut: StatutReclamationEnum = StatutReclamationEnum.NOUVEAU
    description: Optional[str] = None
    date_cloture: Optional[datetime] = None

class ReclamationUpdate(BaseModel):
    dossier_id: Optional[int] = None
    auteur_id: Optional[int] = None
    numero_reclamation: Optional[str] = Field(None, max_length=50)
    objet: Optional[str] = Field(None, max_length=255)
    type_reclamation: Optional[str] = Field(None, max_length=100)
    priorite: Optional[str] = Field(None, max_length=50)
    statut: Optional[StatutReclamationEnum] = None
    description: Optional[str] = None
    date_cloture: Optional[datetime] = None

class ReclamationLight(BaseModel):
    id: int
    objet: str
    statut: StatutReclamationEnum

class ReclamationResponse(ReclamationLight):
    dossier_id: int
    auteur_id: int
    numero_reclamation: Optional[str]
    type_reclamation: Optional[str]
    priorite: Optional[str]
    description: Optional[str]
    date_cloture: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    dossier: DossierCandidatureLight
    auteur: UtilisateurLight

# Paiement Schemas
class PaiementCreate(BaseModel):
    dossier_id: int
    type_paiement: TypePaiementEnum
    montant: float
    devise: DeviseEnum
    statut: StatutPaiementEnum = StatutPaiementEnum.PENDING
    methode: Optional[MethodePaiementEnum] = None
    reference_externe: Optional[str] = Field(None, max_length=120)
    message: Optional[str] = Field(None, max_length=255)
    paye_le: Optional[datetime] = None
    date_echeance: Optional[date] = None

class PaiementUpdate(BaseModel):
    dossier_id: Optional[int] = None
    type_paiement: Optional[TypePaiementEnum] = None
    montant: Optional[float] = None
    devise: Optional[DeviseEnum] = None
    statut: Optional[StatutPaiementEnum] = None
    methode: Optional[MethodePaiementEnum] = None
    reference_externe: Optional[str] = Field(None, max_length=120)
    message: Optional[str] = Field(None, max_length=255)
    paye_le: Optional[datetime] = None
    date_echeance: Optional[date] = None

class PaiementLight(BaseModel):
    id: int
    type_paiement: TypePaiementEnum
    montant: float
    statut: StatutPaiementEnum

class PaiementResponse(PaiementLight):
    dossier_id: int
    devise: DeviseEnum
    methode: Optional[MethodePaiementEnum]
    reference_externe: Optional[str]
    message: Optional[str]
    paye_le: Optional[datetime]
    date_echeance: Optional[date]
    created_at: datetime
    updated_at: datetime
    dossier: DossierCandidatureLight