# Tests de l'API de Formation

Ce répertoire contient une suite complète de tests pour toutes les routes de l'API de formation, organisée par module avec des données réalistes et cohérentes.

## 📁 Structure des Tests

### Fichiers de Test par Module

- **`test_files.py`** - Tests du module de gestion des fichiers
- **`test_utilisateurs.py`** - Tests du module de gestion des utilisateurs
- **`test_formations.py`** - Tests du module de gestion des formations
- **`test_sessions_formations.py`** - Tests du module de gestion des sessions
- **`test_dossiers_candidatures.py`** - Tests du module de gestion des dossiers
- **`test_paiements.py`** - Tests du module de gestion des paiements
- **`test_reclamations.py`** - Tests du module de gestion des réclamations
- **`conftest.py`** - Configuration pytest et fixtures communes

## 🚀 Installation et Configuration

### Prérequis

```bash
pip install pytest
pip install pytest-asyncio
pip install httpx
```

### Structure des Données de Test

Chaque module utilise des données de test réalistes et cohérentes :

#### Utilisateurs
- **Candidats français** : Jean-Pierre Dupont, Sophie Martin
- **Candidats étrangers** : Moussa Koné (Côte d'Ivoire), Fatou Traoré (Burkina Faso)
- **Administrateurs** : Sophie Martin

#### Formations
- **Accueil et Écoute des Familles** : Formation longue, présentiel, 120h, 1200€
- **Appui Pénitentiaire** : Formation courte, en ligne, 80h, 800€
- **Technicien Assistance Sociale** : Formation longue, présentiel, 200h, 1800€

#### Sessions
- **Dates réalistes** : 2024-2025
- **Centres** : Paris, Lyon
- **Modalités** : Présentiel, En ligne
- **Statuts** : Ouverte, Fermée, Annulée

#### Paiements
- **Méthodes** : Carte bancaire, Virement, Mobile Money, ALL, Espèces
- **Devises** : EUR, XAF (FCFA), USD
- **Statuts** : Pending, Accepted, Refused

#### Réclamations
- **Types** : Dossier, Paiement, Session, Formation, Technique
- **Priorités** : Haute, Moyenne, Basse
- **Statuts** : Nouveau, En cours, Clôturé

## 🧪 Exécution des Tests

### Tous les Tests
```bash
pytest
```

### Tests d'un Module Spécifique
```bash
pytest test_utilisateurs.py
pytest test_formations.py
pytest test_paiements.py
```

### Tests avec Détails
```bash
pytest -v
pytest -s
```

### Tests avec Couverture
```bash
pytest --cov=src
pytest --cov=html
```

## 📊 Types de Tests Inclus

### Tests de Création (POST)
- ✅ Création avec données valides
- ✅ Création avec différents types de données
- ✅ Création avec données internationales (devises XAF, USD)
- ✅ Validation des champs requis

### Tests de Lecture (GET)
- ✅ Récupération par ID
- ✅ Récupération de toutes les entités
- ✅ Gestion des erreurs (404, 500)
- ✅ Pagination (skip/limit)

### Tests de Mise à Jour (PUT/PATCH)
- ✅ Mise à jour complète
- ✅ Mise à jour partielle
- ✅ Changement de statuts
- ✅ Changement de modalités

### Tests de Suppression (DELETE)
- ✅ Suppression avec succès
- ✅ Gestion des erreurs

### Tests de Validation
- ✅ Champs requis manquants
- ✅ Types de données invalides
- ✅ Valeurs hors limites
- ✅ Formats invalides

## 🔧 Configuration des Tests

### Fixtures Disponibles

- **`client`** : Client FastAPI de test
- **`mock_db`** : Mock de la base de données
- **`sample_*_data`** : Données d'exemple pour chaque module

### Mock des Services

Tous les tests utilisent des mocks pour les services, permettant de tester les routes sans dépendre de la base de données réelle.

## 📝 Exemples d'Utilisation

### Test de Création d'Utilisateur
```python
def test_create_utilisateur_candidat_success(self, client: TestClient):
    user_data = TEST_UTILISATEURS["candidat"]
    
    with patch('src.api.service.UserService.create') as mock_create:
        mock_create.return_value = {...}
        
        response = client.post("/utilisateurs", json=user_data)
        
        assert response.status_code == 201
        assert response.json()["nom"] == "Dupont"
```

### Test de Validation
```python
def test_create_utilisateur_missing_required_fields(self, client: TestClient):
    user_data = {"nom": "Dupont"}  # prenom et email manquants
    
    response = client.post("/utilisateurs", json=user_data)
    
    assert response.status_code == 422  # Validation error
```

## 🌍 Données Internationales

Les tests incluent des scénarios internationaux :

- **Devises** : EUR, XAF (FCFA), XOF, USD
- **Nationalités** : Française, Ivoirienne, Burkinabé
- **Téléphones** : Formats français (+33) et africains (+225, +226)
- **Montants** : Euros et FCFA (100000 FCFA = ~150€)

## 🔍 Points d'Attention

### Validation des Données
- Tous les tests vérifient la validation des schémas Pydantic
- Tests des contraintes métier (dates, montants, statuts)
- Gestion des erreurs de validation (422)

### Cohérence des Données
- Les données de test sont cohérentes entre les modules
- Les relations entre entités sont respectées
- Les statuts et transitions sont logiques

### Couverture des Cas d'Usage
- Tests des cas nominaux (succès)
- Tests des cas d'erreur (validation, 404, 500)
- Tests des cas limites (données vides, valeurs extrêmes)

## 📈 Améliorations Possibles

- Ajout de tests d'intégration avec base de données réelle
- Tests de performance et charge
- Tests de sécurité (authentification, autorisation)
- Tests de migration de base de données
- Tests de l'API avec différents clients (mobile, web)

## 🚨 Dépannage

### Erreurs Communes
- **ImportError** : Vérifier que tous les modules sont installés
- **ModuleNotFoundError** : Vérifier la structure des dossiers
- **AssertionError** : Vérifier que les mocks retournent les bonnes données

### Logs et Debug
```bash
pytest -v -s --tb=long
pytest --pdb  # Arrêt sur erreur
```

## 📚 Documentation Complémentaire

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation Pytest](https://docs.pytest.org/)
- [Documentation Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
