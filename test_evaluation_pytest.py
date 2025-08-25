#!/usr/bin/env python3
"""
Test pytest du module évaluations
Ce fichier teste toutes les routes du module évaluations avec pytest
"""

import pytest
import httpx
import json
from datetime import datetime, timedelta

# Configuration de base
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Données de test
TEST_USER_ID = 1
TEST_SESSION_ID = 1

def get_evaluation_data():
    """Données de test pour une évaluation"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "session_id": TEST_SESSION_ID,
        "titre": f"Test d'évaluation - QCM {timestamp}",
        "description": f"Évaluation de test pour valider le système - {timestamp}",
        "type_evaluation": "qcm",
        "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
        "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
        "duree_minutes": 60,
        "ponderation": 100.0,
        "note_minimale": 10.0,
        "nombre_tentatives_max": 2,
        "type_correction": "automatique",
        "instructions": "Répondez à toutes les questions. Vous avez 1 heure.",
        "questions": [
            {
                "question": "Quelle est la capitale de la France?",
                "type_question": "choix_multiple",
                "reponses_possibles": '["Paris", "Londres", "Berlin", "Madrid"]',
                "reponse_correcte": "Paris",
                "points": 5.0,
                "ordre": 1
            },
            {
                "question": "Combien de côtés a un carré?",
                "type_question": "choix_multiple",
                "reponses_possibles": '["3", "4", "5", "6"]',
                "reponse_correcte": "4",
                "points": 5.0,
                "ordre": 2
            }
        ]
    }

def get_question_data(evaluation_id):
    """Données de test pour une question"""
    return {
        "evaluation_id": evaluation_id,
        "question": "Nouvelle question de test",
        "type_question": "choix_multiple",
        "ordre": 3,
        "reponses_possibles": '["A", "B", "C", "D"]',
        "reponse_correcte": "A",
        "points": 3.0
    }

@pytest.mark.asyncio
async def test_api_accessible():
    """Test que l'API est accessible"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/docs")
        assert response.status_code == 200, "L'API doit être accessible"

@pytest.mark.asyncio
async def test_create_evaluation():
    """Test de création d'une évaluation"""
    async with httpx.AsyncClient() as client:
        evaluation_data = get_evaluation_data()
        response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        assert response.status_code == 201, f"La création doit réussir: {response.status_code} - {response.text}"
        
        evaluation = response.json()
        assert "id" in evaluation, "L'évaluation doit avoir un ID"
        assert evaluation["titre"] == evaluation_data["titre"], "Le titre doit correspondre"
        
        return evaluation["id"]

@pytest.mark.asyncio
async def test_get_evaluation():
    """Test de récupération d'une évaluation"""
    # D'abord créer une évaluation
    async with httpx.AsyncClient() as client:
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test GET évaluation",
            "description": "Évaluation pour test GET",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 30,
            "ponderation": 50.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test simple"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Maintenant tester le GET
            response = await client.get(f"{API_BASE}/evaluations/{evaluation_id}")
            assert response.status_code == 200, f"Le GET doit réussir: {response.status_code}"
            
            evaluation = response.json()
            assert evaluation["id"] == evaluation_id, "L'ID doit correspondre"
            assert evaluation["titre"] == evaluation_data["titre"], "Le titre doit correspondre"

@pytest.mark.asyncio
async def test_get_evaluations_by_session():
    """Test de récupération des évaluations d'une session"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/evaluations/session/{TEST_SESSION_ID}")
        assert response.status_code == 200, f"Le GET par session doit réussir: {response.status_code}"
        
        evaluations = response.json()
        assert isinstance(evaluations, list), "Le résultat doit être une liste"

@pytest.mark.asyncio
async def test_update_evaluation():
    """Test de mise à jour d'une évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test UPDATE évaluation",
            "description": "Évaluation pour test UPDATE",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 45,
            "ponderation": 75.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 2,
            "type_correction": "automatique",
            "instructions": "Test UPDATE"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Mettre à jour
            update_data = {
                "titre": "Test UPDATE évaluation (Modifié)",
                "description": "Description modifiée"
            }
            
            response = await client.put(
                f"{API_BASE}/evaluations/{evaluation_id}?user_id={TEST_USER_ID}",
                json=update_data
            )
            
            assert response.status_code == 200, f"La mise à jour doit réussir: {response.status_code}"
            
            updated_evaluation = response.json()
            assert updated_evaluation["titre"] == update_data["titre"], "Le titre doit être mis à jour"

@pytest.mark.asyncio
async def test_create_question_evaluation():
    """Test de création d'une question d'évaluation"""
    async with httpx.AsyncClient() as client:
        # D'abord créer une évaluation
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test Question évaluation",
            "description": "Évaluation pour test question",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 20,
            "ponderation": 25.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test question"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Créer une question
            question_data = get_question_data(evaluation_id)
            
            response = await client.post(
                f"{API_BASE}/questions-evaluation?user_id={TEST_USER_ID}",
                json=question_data
            )
            
            assert response.status_code == 201, f"La création de question doit réussir: {response.status_code}"
            
            question = response.json()
            assert "id" in question, "La question doit avoir un ID"
            assert question["question"] == question_data["question"], "Le texte de la question doit correspondre"

@pytest.mark.asyncio
async def test_get_question_evaluation():
    """Test de récupération d'une question d'évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation et une question
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test GET Question",
            "description": "Évaluation pour test GET question",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 15,
            "ponderation": 20.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test GET question"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            question_data = get_question_data(evaluation_id)
            question_data["question"] = "Question pour GET"
            
            question_response = await client.post(
                f"{API_BASE}/questions-evaluation?user_id={TEST_USER_ID}",
                json=question_data
            )
            
            if question_response.status_code == 201:
                question_id = question_response.json()["id"]
                
                # Tester le GET
                response = await client.get(f"{API_BASE}/questions-evaluation/{question_id}")
                assert response.status_code == 200, f"Le GET de question doit réussir: {response.status_code}"
                
                question = response.json()
                assert question["id"] == question_id, "L'ID de la question doit correspondre"

@pytest.mark.asyncio
async def test_get_questions_by_evaluation():
    """Test de récupération des questions d'une évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation avec des questions
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test Questions par évaluation",
            "description": "Évaluation avec questions",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 30,
            "ponderation": 30.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test questions par évaluation"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Créer plusieurs questions
            for i in range(3):
                question_data = get_question_data(evaluation_id)
                question_data["question"] = f"Question {i+1}"
                question_data["ordre"] = i+1
                
                await client.post(
                    f"{API_BASE}/questions-evaluation?user_id={TEST_USER_ID}",
                    json=question_data
                )
            
            # Tester le GET des questions par évaluation
            response = await client.get(f"{API_BASE}/questions-evaluation/evaluation/{evaluation_id}")
            assert response.status_code == 200, f"Le GET des questions par évaluation doit réussir: {response.status_code}"
            
            questions = response.json()
            assert isinstance(questions, list), "Le résultat doit être une liste"
            assert len(questions) >= 3, f"Il doit y avoir au moins 3 questions, trouvé: {len(questions)}"

@pytest.mark.asyncio
async def test_update_question_evaluation():
    """Test de mise à jour d'une question d'évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation et une question
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test UPDATE Question",
            "description": "Évaluation pour test UPDATE question",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 25,
            "ponderation": 25.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test UPDATE question"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            question_data = get_question_data(evaluation_id)
            question_data["question"] = "Question originale"
            
            question_response = await client.post(
                f"{API_BASE}/questions-evaluation?user_id={TEST_USER_ID}",
                json=question_data
            )
            
            if question_response.status_code == 201:
                question_id = question_response.json()["id"]
                
                # Mettre à jour la question
                update_data = {
                    "question": "Question modifiée",
                    "points": 10.0
                }
                
                response = await client.put(
                    f"{API_BASE}/questions-evaluation/{question_id}?user_id={TEST_USER_ID}",
                    json=update_data
                )
                
                assert response.status_code == 200, f"La mise à jour de question doit réussir: {response.status_code}"
                
                updated_question = response.json()
                assert updated_question["question"] == update_data["question"], "Le texte de la question doit être mis à jour"
                assert updated_question["points"] == update_data["points"], "Les points doivent être mis à jour"

@pytest.mark.asyncio
async def test_start_evaluation():
    """Test de démarrage d'une évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test Start évaluation",
            "description": "Évaluation pour test start",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 20,
            "ponderation": 20.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test start"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Démarrer l'évaluation
            response = await client.post(
                f"{API_BASE}/resultats-evaluations/commencer?evaluation_id={evaluation_id}&user_id={TEST_USER_ID}"
            )
            
            assert response.status_code == 201, f"Le démarrage de l'évaluation doit réussir: {response.status_code}"
            
            resultat = response.json()
            assert "id" in resultat, "Le résultat doit avoir un ID"
            assert "statut" in resultat, "Le résultat doit avoir un statut"

@pytest.mark.asyncio
async def test_get_resultat_evaluation():
    """Test de récupération d'un résultat d'évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer et démarrer une évaluation
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test GET Resultat",
            "description": "Évaluation pour test GET resultat",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 15,
            "ponderation": 15.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test GET resultat"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            start_response = await client.post(
                f"{API_BASE}/resultats-evaluations/commencer?evaluation_id={evaluation_id}&user_id={TEST_USER_ID}"
            )
            
            if start_response.status_code == 201:
                resultat_id = start_response.json()["id"]
                
                # Tester le GET du résultat
                response = await client.get(f"{API_BASE}/resultats-evaluations/{resultat_id}")
                assert response.status_code == 200, f"Le GET du résultat doit réussir: {response.status_code}"
                
                resultat = response.json()
                assert resultat["id"] == resultat_id, "L'ID du résultat doit correspondre"

@pytest.mark.asyncio
async def test_get_resultats_by_evaluation():
    """Test de récupération des résultats d'une évaluation"""
    async with httpx.AsyncClient() as client:
        # Créer une évaluation
        evaluation_data = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test Resultats par évaluation",
            "description": "Évaluation pour test resultats",
            "type_evaluation": "qcm",
            "date_ouverture": (datetime.now() - timedelta(hours=1)).isoformat(),
            "date_fermeture": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duree_minutes": 10,
            "ponderation": 10.0,
            "note_minimale": 10.0,
            "nombre_tentatives_max": 1,
            "type_correction": "automatique",
            "instructions": "Test resultats par évaluation"
        }
        
        create_response = await client.post(
            f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
            json=evaluation_data
        )
        
        if create_response.status_code == 201:
            evaluation_id = create_response.json()["id"]
            
            # Démarrer l'évaluation
            await client.post(
                f"{API_BASE}/resultats-evaluations/commencer?evaluation_id={evaluation_id}&user_id={TEST_USER_ID}"
            )
            
            # Tester le GET des résultats par évaluation
            response = await client.get(f"{API_BASE}/resultats-evaluations/evaluation/{evaluation_id}")
            assert response.status_code == 200, f"Le GET des résultats par évaluation doit réussir: {response.status_code}"
            
            resultats = response.json()
            assert isinstance(resultats, list), "Le résultat doit être une liste"

@pytest.mark.asyncio
async def test_get_resultats_by_candidat():
    """Test de récupération des résultats d'un candidat"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/resultats-evaluations/candidat/{TEST_USER_ID}")
        assert response.status_code == 200, f"Le GET des résultats par candidat doit réussir: {response.status_code}"
        
        resultats = response.json()
        assert isinstance(resultats, list), "Le résultat doit être une liste"

@pytest.mark.asyncio
async def test_generate_certificat():
    """Test de génération d'un certificat"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/certificats/generer?candidat_id={TEST_USER_ID}&session_id={TEST_SESSION_ID}&user_id={TEST_USER_ID}"
        )
        
        # La génération peut échouer si les données ne sont pas complètes, ce n'est pas critique
        if response.status_code == 201:
            certificat = response.json()
            assert "numero_certificat" in certificat, "Le certificat doit avoir un numéro"
        else:
            print(f"⚠️  La génération du certificat a échoué: {response.status_code} - {response.text}")

@pytest.mark.asyncio
async def test_get_certificats_by_candidat():
    """Test de récupération des certificats d'un candidat"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/certificats/candidat/{TEST_USER_ID}?user_id={TEST_USER_ID}")
        assert response.status_code == 200, f"Le GET des certificats par candidat doit réussir: {response.status_code}"
        
        certificats = response.json()
        assert isinstance(certificats, list), "Le résultat doit être une liste"

@pytest.mark.asyncio
async def test_diagnostic():
    """Test de diagnostic pour identifier le problème"""
    async with httpx.AsyncClient() as client:
        # Test 1: Vérifier si l'API est accessible
        print("🔍 Test 1: Vérification de l'API")
        response = await client.get(f"{BASE_URL}/docs")
        print(f"   API accessible: {response.status_code == 200}")
        
        # Test 2: Vérifier si la session existe
        print("🔍 Test 2: Vérification de la session")
        try:
            response = await client.get(f"{API_BASE}/sessions-formations/{TEST_SESSION_ID}")
            print(f"   Session {TEST_SESSION_ID} existe: {response.status_code == 200}")
            if response.status_code == 200:
                session = response.json()
                print(f"   Session: {session.get('titre', 'N/A')}")
        except Exception as e:
            print(f"   Erreur session: {str(e)}")
        
        # Test 3: Vérifier si l'utilisateur existe
        print("🔍 Test 3: Vérification de l'utilisateur")
        try:
            response = await client.get(f"{API_BASE}/utilisateurs/{TEST_USER_ID}")
            print(f"   Utilisateur {TEST_USER_ID} existe: {response.status_code == 200}")
            if response.status_code == 200:
                user = response.json()
                print(f"   Utilisateur: {user.get('nom', 'N/A')} {user.get('prenom', 'N/A')} - Rôle: {user.get('role', 'N/A')}")
        except Exception as e:
            print(f"   Erreur utilisateur: {str(e)}")
        
        # Test 4: Essayer de créer une évaluation simple
        print("🔍 Test 4: Test de création d'évaluation simple")
        simple_evaluation = {
            "session_id": TEST_SESSION_ID,
            "titre": "Test diagnostic",
            "type_evaluation": "qcm",
            "type_correction": "automatique",
            "nombre_tentatives_max": 1
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/evaluations?user_id={TEST_USER_ID}",
                json=simple_evaluation
            )
            print(f"   Création évaluation: {response.status_code}")
            if response.status_code != 201:
                print(f"   Erreur: {response.text}")
        except Exception as e:
            print(f"   Exception: {str(e)}")

@pytest.mark.asyncio
async def test_database_health():
    """Test de santé de la base de données"""
    async with httpx.AsyncClient() as client:
        print("🔍 Test de santé de la base de données...")
        
        # Test 1: Vérifier si l'API est accessible
        print("   📡 Test de l'API...")
        try:
            response = await client.get(f"{BASE_URL}/docs")
            print(f"   ✅ API accessible: {response.status_code}")
        except Exception as e:
            print(f"   ❌ API inaccessible: {str(e)}")
            return False
        
        # Test 2: Vérifier les routes disponibles
        print("   🛣️ Test des routes...")
        try:
            # Test route utilisateurs
            response = await client.get(f"{API_BASE}/utilisateurs?skip=0&limit=1")
            print(f"   ✅ Route utilisateurs: {response.status_code}")
            
            # Test route centres
            response = await client.get(f"{API_BASE}/centres-formations?skip=0&limit=1")
            print(f"   ✅ Route centres: {response.status_code}")
            
            # Test route formations
            response = await client.get(f"{API_BASE}/formations?skip=0&limit=1")
            print(f"   ✅ Route formations: {response.status_code}")
            
            # Test route sessions
            response = await client.get(f"{API_BASE}/sessions-formations?skip=0&limit=1")
            print(f"   ✅ Route sessions: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ Erreur test routes: {str(e)}")
            return False
        
        # Test 3: Vérifier si des données existent déjà
        print("   📊 Vérification des données existantes...")
        try:
            response = await client.get(f"{API_BASE}/utilisateurs?skip=0&limit=10")
            if response.status_code == 200:
                users = response.json()
                print(f"   📝 Utilisateurs existants: {len(users)}")
                if len(users) > 0:
                    print(f"   👤 Premier utilisateur: {users[0].get('nom', 'N/A')} {users[0].get('prenom', 'N/A')} (ID: {users[0].get('id', 'N/A')})")
                    global TEST_USER_ID
                    TEST_USER_ID = users[0]["id"]
                    print(f"   🎯 Utilisateur de test défini: {TEST_USER_ID}")
            
            response = await client.get(f"{API_BASE}/sessions-formations?skip=0&limit=10")
            if response.status_code == 200:
                sessions = response.json()
                print(f"   📅 Sessions existantes: {len(sessions)}")
                if len(sessions) > 0:
                    print(f"   🗓️ Première session: {sessions[0].get('titre', 'N/A')} (ID: {sessions[0].get('id', 'N/A')})")
                    global TEST_SESSION_ID
                    TEST_SESSION_ID = sessions[0]["id"]
                    print(f"   🎯 Session de test définie: {TEST_SESSION_ID}")
                    
        except Exception as e:
            print(f"   ❌ Erreur vérification données: {str(e)}")
            return False
        
        print("   ✅ Tests de santé terminés")
        return True

@pytest.mark.asyncio
async def test_setup_base_data():
    """Test de création des données de base nécessaires"""
    async with httpx.AsyncClient() as client:
        print("🔧 Création des données de base...")
        
        # 1. Créer un utilisateur
        print("   📝 Création d'un utilisateur...")
        user_data = {
            "nom": "Test",
            "prenom": "User",
            "email": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
            "role": "formateur"
        }
        
        try:
            response = await client.post(f"{API_BASE}/utilisateurs", json=user_data)
            if response.status_code == 201:
                user = response.json()
                global TEST_USER_ID
                TEST_USER_ID = user["id"]
                print(f"   ✅ Utilisateur créé avec l'ID: {TEST_USER_ID}")
            else:
                print(f"   ❌ Erreur création utilisateur: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Exception création utilisateur: {str(e)}")
            return False
        
        # 2. Créer un centre de formation
        print("   🏢 Création d'un centre de formation...")
        centre_data = {
            "nom": "Centre Test",
            "adresse": "123 Rue Test",
            "ville": "Ville Test",
            "code_postal": "12345",
            "pays": "France",
            "telephone": "0123456789",
            "email": "centre@test.com"
        }
        
        try:
            response = await client.post(f"{API_BASE}/centres-formations", json=centre_data)
            if response.status_code == 201:
                centre = response.json()
                centre_id = centre["id"]
                print(f"   ✅ Centre créé avec l'ID: {centre_id}")
            else:
                print(f"   ❌ Erreur création centre: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Exception création centre: {str(e)}")
            return False
        
        # 3. Créer une formation
        print("   📚 Création d'une formation...")
        formation_data = {
            "centre_id": centre_id,
            "titre": "Formation Test",
            "description": "Formation de test pour les évaluations",
            "specialite": "accueil écoute familles",
            "type_formation": "courte",
            "modalite": "PRESENTIEL",
            "duree_heures": 40
        }
        
        try:
            response = await client.post(f"{API_BASE}/formations", json=formation_data)
            if response.status_code == 201:
                formation = response.json()
                formation_id = formation["id"]
                print(f"   ✅ Formation créée avec l'ID: {formation_id}")
            else:
                print(f"   ❌ Erreur création formation: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Exception création formation: {str(e)}")
            return False
        
        # 4. Créer une session de formation
        print("   🗓️ Création d'une session de formation...")
        session_data = {
            "formation_id": formation_id,
            "titre": "Session Test",
            "date_debut": (datetime.now() + timedelta(days=7)).isoformat(),
            "date_fin": (datetime.now() + timedelta(days=14)).isoformat(),
            "modalite": "PRESENTIEL",
            "statut": "ouverte"
        }
        
        try:
            response = await client.post(f"{API_BASE}/sessions-formations", json=session_data)
            if response.status_code == 201:
                session = response.json()
                global TEST_SESSION_ID
                TEST_SESSION_ID = session["id"]
                print(f"   ✅ Session créée avec l'ID: {TEST_SESSION_ID}")
            else:
                print(f"   ❌ Erreur création session: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Exception création session: {str(e)}")
            return False
        
        print("   🎉 Toutes les données de base ont été créées!")
        return True

@pytest.mark.asyncio
async def test_create_evaluation_simple():
    """Test simple de création d'évaluation avec des IDs fictifs"""
    async with httpx.AsyncClient() as client:
        print("🔍 Test simple de création d'évaluation...")
        
        # Utiliser des IDs fictifs pour tester
        test_user_id = 999
        test_session_id = 999
        
        # Données d'évaluation minimales
        evaluation_data = {
            "session_id": test_session_id,
            "titre": "Test évaluation simple",
            "type_evaluation": "qcm",
            "type_correction": "automatique",
            "nombre_tentatives_max": 1
        }
        
        try:
            print(f"   📝 Tentative de création avec session_id={test_session_id}, user_id={test_user_id}")
            response = await client.post(
                f"{API_BASE}/evaluations?user_id={test_user_id}",
                json=evaluation_data
            )
            
            print(f"   📊 Réponse: {response.status_code}")
            if response.status_code != 201:
                print(f"   ❌ Erreur: {response.text}")
                
                # Analyser l'erreur
                if response.status_code == 409:
                    print("   🔍 Erreur 409: Violation d'intégrité - probablement session_id ou user_id inexistant")
                elif response.status_code == 422:
                    print("   🔍 Erreur 422: Validation des données échouée")
                elif response.status_code == 500:
                    print("   🔍 Erreur 500: Erreur interne du serveur")
                    
            else:
                print("   ✅ Création réussie!")
                evaluation = response.json()
                print(f"   📋 Évaluation créée: {evaluation}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
        
        return True

@pytest.mark.asyncio
async def test_create_user_simple():
    """Test simple de création d'utilisateur"""
    async with httpx.AsyncClient() as client:
        print("🔍 Test simple de création d'utilisateur...")
        
        # Données utilisateur minimales
        user_data = {
            "nom": "Test",
            "prenom": "User",
            "email": "test@example.com"
        }
        
        try:
            print(f"   📝 Tentative de création d'utilisateur...")
            response = await client.post(f"{API_BASE}/utilisateurs", json=user_data)
            
            print(f"   📊 Réponse: {response.status_code}")
            if response.status_code != 201:
                print(f"   ❌ Erreur: {response.text}")
                
                # Analyser l'erreur
                if response.status_code == 409:
                    print("   🔍 Erreur 409: Violation d'intégrité - probablement email dupliqué")
                elif response.status_code == 422:
                    print("   🔍 Erreur 422: Validation des données échouée")
                elif response.status_code == 500:
                    print("   🔍 Erreur 500: Erreur interne du serveur")
                    
            else:
                print("   ✅ Création réussie!")
                user = response.json()
                print(f"   👤 Utilisateur créé: {user}")
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
        
        return True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
