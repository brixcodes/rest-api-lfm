# 🔐 Guide d'authentification de l'API de formation

Ce document explique comment utiliser le système d'authentification JWT implémenté dans l'API.

## 📋 Fonctionnalités disponibles

### 1. Connexion utilisateur
- **Endpoint**: `POST /api/v1/utilisateurs/login`
- **Description**: Authentifie un utilisateur avec son email et mot de passe
- **Retourne**: Un token JWT d'accès et les informations de l'utilisateur

### 2. Profil utilisateur protégé
- **Endpoint**: `GET /api/v1/utilisateurs/me`
- **Description**: Récupère le profil de l'utilisateur connecté
- **Protection**: Nécessite un token JWT valide

### 3. Profil utilisateur alternatif
- **Endpoint**: `GET /api/v1/utilisateurs/profile`
- **Description**: Récupère le profil de l'utilisateur connecté (route alternative)
- **Protection**: Nécessite un token JWT valide

### 4. Gestion des mots de passe
- **Changement de mot de passe**: `POST /api/v1/utilisateurs/{id}/change-password`
- **Réinitialisation par email**: `POST /api/v1/utilisateurs/reset-password`

## 🚀 Comment utiliser l'authentification

### Étape 1: Connexion
```bash
curl -X POST "http://localhost:8000/api/v1/utilisateurs/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "votre.email@example.com",
    "password": "votre_mot_de_passe"
  }'
```

**Réponse réussie:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "nom": "Dupont",
    "prenom": "Jean",
    "email": "votre.email@example.com",
    "nationalite": "Française",
    "role": "CANDIDAT"
  },
  "message": "Connexion réussie"
}
```

### Étape 2: Utilisation du token
```bash
curl -X GET "http://localhost:8000/api/v1/utilisateurs/me" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## 🏗️ Architecture

### Logique métier dans le service
La logique d'authentification est entièrement gérée dans le service `UserService` :
- **`authenticate_user()`** : Vérifie les credentials et met à jour `last_login`
- **`login_user()`** : Gère l'authentification complète et retourne `LoginResponse`

### Routes simplifiées
Les routes utilisent maintenant directement les méthodes du service :
- **`/login`** : Appelle `service.login_user()` et retourne `LoginResponse`
- **`/me`** et **`/profile`** : Récupèrent le profil via `get_current_active_user`

## 🔒 Sécurité

### Configuration JWT
- **Algorithme**: HS256
- **Durée de vie**: 30 minutes par défaut
- **Clé secrète**: Configurée via la variable d'environnement `SECRET_KEY`

### Protection des routes
Les routes protégées utilisent le décorateur `Depends(get_current_active_user)` qui :
1. Vérifie la présence du token JWT
2. Valide la signature du token
3. Vérifie l'expiration
4. Récupère l'utilisateur depuis la base de données
5. Vérifie que le compte est actif

## 🧪 Tests

### Fichier de test
Exécutez le fichier de test pour vérifier le bon fonctionnement :
```bash
python test_auth.py
```

### Tests inclus
- ✅ Connexion utilisateur
- ✅ Accès aux routes protégées
- ✅ Rejet des tokens invalides
- ✅ Rejet des requêtes sans token
- ✅ Création d'utilisateur et tentative de connexion

## 📝 Variables d'environnement

### SECRET_KEY (Recommandé)
```bash
export SECRET_KEY="votre_cle_secrete_tres_longue_et_complexe_ici"
```

**⚠️ Important**: En production, utilisez une clé secrète forte et unique !

### Configuration par défaut
Si `SECRET_KEY` n'est pas définie, une clé par défaut est utilisée (à changer en production).

## 🔧 Développement

### Ajouter une route protégée
```python
from src.api.security import get_current_active_user

@app.get("/route-protegee")
async def route_protegee(current_user: Utilisateur = Depends(get_current_active_user)):
    return {"message": f"Bonjour {current_user.nom}!"}
```

### Vérifier le rôle utilisateur
```python
from src.util.helper.enum import RoleEnum

@app.get("/admin-only")
async def admin_only(current_user: Utilisateur = Depends(get_current_active_user)):
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return {"message": "Accès administrateur autorisé"}
```

## 🚨 Dépannage

### Erreur 401 - Non autorisé
- Vérifiez que le token est présent dans l'en-tête `Authorization`
- Vérifiez que le token n'est pas expiré
- Vérifiez que l'utilisateur existe et est actif

### Erreur 403 - Accès interdit
- Vérifiez les permissions de l'utilisateur
- Vérifiez que le compte n'est pas désactivé

### Token expiré
- Le token JWT expire après 30 minutes
- Demandez un nouveau token via la route de connexion

## 📚 Ressources

- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [JWT.io](https://jwt.io/) - Décodeur et générateur de tokens JWT
- [Passlib](https://passlib.readthedocs.io/) - Gestion des mots de passe

## 🔐 Bonnes pratiques

1. **Ne stockez jamais** les tokens côté serveur
2. **Utilisez HTTPS** en production
3. **Changez régulièrement** la clé secrète
4. **Limitez la durée de vie** des tokens
5. **Implémentez la révocation** des tokens si nécessaire
6. **Loggez les tentatives** d'authentification échouées

---

**Note**: Ce système d'authentification est conçu pour les applications web et mobiles. Pour les applications plus complexes, considérez l'ajout de refresh tokens et de la révocation de tokens.
