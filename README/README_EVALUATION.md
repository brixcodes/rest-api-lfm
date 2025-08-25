# 🎓 Système d'évaluation et de certification

Ce document explique le système d'évaluation et de certification implémenté dans l'API de formation.

## 📋 Vue d'ensemble

Le système permet aux formateurs et administrateurs de créer des évaluations pour les sessions de formation, et aux candidats de les passer pour obtenir des certificats.

## 🏗️ Architecture du système

### Entités principales

1. **Evaluation** - Définit une épreuve pour une session
2. **QuestionEvaluation** - Questions individuelles d'une évaluation
3. **ResultatEvaluation** - Résultats d'un candidat pour une évaluation
4. **ReponseCandidat** - Réponses individuelles d'un candidat
5. **Certificat** - Attestation de réussite

### Relations

```
SessionFormation (1) ←→ (N) Evaluation
Evaluation (1) ←→ (N) QuestionEvaluation
Evaluation (1) ←→ (N) ResultatEvaluation
ResultatEvaluation (1) ←→ (N) ReponseCandidat
Utilisateur (1) ←→ (N) Certificat
```

## 🔐 Rôles et permissions

### Rôles utilisateur
- **CANDIDAT** : Peut passer les évaluations et voir ses résultats
- **FORMATEUR** : Peut créer/modifier des évaluations et corriger les devoirs
- **ADMIN** : Accès complet au système

### Permissions par fonctionnalité

| Fonctionnalité | CANDIDAT | FORMATEUR | ADMIN |
|----------------|----------|-----------|-------|
| Créer évaluation | ❌ | ✅ | ✅ |
| Modifier évaluation | ❌ | ✅ | ✅ |
| Passer évaluation | ✅ | ❌ | ❌ |
| Voir résultats | ✅ (siens) | ✅ (tous) | ✅ |
| Générer certificat | ❌ | ✅ | ✅ |

## 📊 Types d'évaluation supportés

### 1. QCM (Quiz à choix multiples)
- **Correction** : Automatique
- **Format** : Questions avec réponses prédéfinies
- **Exemple** : Quiz de validation des connaissances

### 2. Devoir à rendre
- **Correction** : Manuelle par le formateur
- **Format** : Fichier uploadé ou texte libre
- **Exemple** : Rédaction d'un rapport

### 3. Projet pratique
- **Correction** : Manuelle par le formateur
- **Format** : Fichier, lien GitHub, etc.
- **Exemple** : Développement d'une application

### 4. Examen surveillé
- **Correction** : Manuelle par le formateur
- **Format** : Questions variées
- **Exemple** : Examen final de session

### 5. Soutenance
- **Correction** : Manuelle par le formateur
- **Format** : Présentation orale
- **Exemple** : Défense de projet

## 🚀 Workflow complet

### 1. Création d'une évaluation (Formateur/Admin)

```bash
POST /api/v1/evaluations
{
  "session_id": 1,
  "titre": "Examen final - Module 1",
  "description": "Évaluation des connaissances acquises",
  "type_evaluation": "examen",
  "date_ouverture": "2024-01-15T09:00:00Z",
  "date_fermeture": "2024-01-15T17:00:00Z",
  "duree_minutes": 120,
  "ponderation": 30.0,
  "note_minimale": 10.0,
  "nombre_tentatives_max": 2,
  "type_correction": "manuelle",
  "instructions": "Répondez à toutes les questions...",
  "questions": [
    {
      "question": "Qu'est-ce que...?",
      "type_question": "texte_libre",
      "ordre": 1,
      "points": 5.0
    }
  ]
}
```

### 2. Passage d'une évaluation (Candidat)

#### Commencer l'évaluation
```bash
POST /api/v1/resultats-evaluations/commencer?evaluation_id=1
Authorization: Bearer <token_jwt>
```

#### Soumettre les réponses
```bash
POST /api/v1/resultats-evaluations/{resultat_id}/soumettre
Authorization: Bearer <token_jwt>
{
  "reponses": [
    {
      "question_id": 1,
      "reponse_texte": "Ma réponse à la question..."
    },
    {
      "question_id": 2,
      "reponse_fichier_url": "/upload/projet_final.pdf"
    }
  ]
}
```

### 3. Génération du certificat (Formateur/Admin)

```bash
POST /api/v1/certificats/generer?candidat_id=1&session_id=1
Authorization: Bearer <token_jwt>
```

## 📈 Calcul des notes

### Pondération des évaluations
- Chaque évaluation a un pourcentage de pondération
- La note finale est calculée selon la formule :
  ```
  Note_finale = Σ(Note_évaluation × Pondération_évaluation) / Σ(Pondération_évaluation)
  ```

### Exemple de calcul
- **Évaluation 1** : 15/20 (pondération 40%)
- **Évaluation 2** : 18/20 (pondération 60%)
- **Note finale** : (15×0.4 + 18×0.6) = 16.8/20

### Mentions
- **Très bien** : ≥ 16.0
- **Bien** : ≥ 14.0
- **Assez bien** : ≥ 12.0
- **Passable** : ≥ 10.0
- **Insuffisant** : < 10.0

## 🔧 API Endpoints

### Évaluations
- `POST /evaluations` - Créer une évaluation
- `GET /evaluations/{id}` - Récupérer une évaluation
- `GET /evaluations/session/{session_id}` - Lister les évaluations d'une session
- `PUT /evaluations/{id}` - Modifier une évaluation
- `DELETE /evaluations/{id}` - Supprimer une évaluation

### Résultats
- `POST /resultats-evaluations/commencer` - Commencer une évaluation
- `POST /resultats-evaluations/{id}/soumettre` - Soumettre les réponses

### Certificats
- `POST /certificats/generer` - Générer un certificat
- `GET /certificats/candidat/{id}` - Lister les certificats d'un candidat

## 📝 Exemples d'utilisation

### Créer un QCM automatique
```python
evaluation_data = {
    "session_id": 1,
    "titre": "Quiz de validation",
    "type_evaluation": "qcm",
    "type_correction": "automatique",
    "questions": [
        {
            "question": "Quelle est la capitale de la France?",
            "type_question": "choix_multiple",
            "reponses_possibles": '["Paris", "Londres", "Berlin", "Madrid"]',
            "reponse_correcte": "Paris",
            "points": 2.0
        }
    ]
}
```

### Créer un devoir à rendre
```python
evaluation_data = {
    "session_id": 1,
    "titre": "Rapport de stage",
    "type_evaluation": "devoir",
    "type_correction": "manuelle",
    "instructions": "Rédigez un rapport de 5 pages sur votre expérience...",
    "duree_minutes": 1440  # 24h
}
```

## 🚨 Gestion des erreurs

### Erreurs courantes
- **403 Forbidden** : Permissions insuffisantes
- **400 Bad Request** : Évaluation fermée ou trop de tentatives
- **404 Not Found** : Évaluation ou session inexistante

### Validation des données
- Vérification des dates d'ouverture/fermeture
- Contrôle du nombre de tentatives
- Validation des types de questions et réponses

## 🔮 Évolutions futures

### Fonctionnalités prévues
- [ ] Support des évaluations en temps réel
- [ ] Système de plagiat
- [ ] Évaluations par pairs
- [ ] Templates d'évaluation
- [ ] Export des résultats (PDF, Excel)
- [ ] Notifications automatiques
- [ ] Dashboard de suivi

### Améliorations techniques
- [ ] Cache Redis pour les performances
- [ ] WebSockets pour les évaluations en temps réel
- [ ] Système de backup automatique
- [ ] API GraphQL pour les requêtes complexes

## 📚 Ressources

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic Validation](https://pydantic-docs.helpmanual.io/)
- [JWT Authentication](https://jwt.io/)

---

**Note** : Ce système est conçu pour être extensible et peut être adapté selon les besoins spécifiques de votre organisation.
