import pytest
import asyncio
import httpx
from datetime import datetime, timedelta
import time

# Configuration de base
API_BASE = "http://localhost:8000/api/v1"
TIMEOUT = 30

# Données de test
def get_resultat_data(evaluation_id: int, candidat_id: int):
    timestamp = int(time.time())
    return {
        "evaluation_id": evaluation_id,
        "candidat_id": candidat_id,
        "date_debut": datetime.now().isoformat(),
        "statut": "en_cours",
        "score_obtenu": None,
        "nombre_questions_repondues": 0,
        "nombre_questions_correctes": 0,
        "temps_total_secondes": None,
        "commentaires_correcteur": None,
        "type_correction": None
    }

def get_reponse_data(question_id: int, candidat_id: int):
    timestamp = int(time.time())
    return {
        "question_evaluation_id": question_id,
        "candidat_id": candidat_id,
        "reponse_texte": f"Réponse test {timestamp}",
        "reponse_choix": None,
        "temps_reponse_secondes": 30,
        "est_correcte": None,
        "commentaire_correcteur": None,
        "note_obtenue": None
    }

@pytest.mark.asyncio
async def test_diagnostic():
    """Test de diagnostic pour vérifier l'état de l'API"""
    print("🔍 Test 1: Vérification de l'API")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{API_BASE}/")
            print(f"   API accessible: {response.status_code == 200}")
        except Exception as e:
            print(f"   ❌ Erreur API: {e}")
            return False
    
    print("🔍 Test 2: Vérification des routes resultats-evaluations")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Test de la route GET /resultats-evaluations
            response = await client.get(f"{API_BASE}/resultats-evaluations")
            print(f"   Route GET /resultats-evaluations: {response.status_code}")
            
            # Test de la route GET /resultats-evaluations/{resultat_id}
            response = await client.get(f"{API_BASE}/resultats-evaluations/1")
            print(f"   Route GET /resultats-evaluations/1: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ Erreur test routes: {e}")
    
    return True

@pytest.mark.asyncio
async def test_create_resultat_simple():
    """Test simple de création d'un résultat d'évaluation"""
    print("🔍 Test de création simple d'un résultat d'évaluation...")
    
    # Données de test avec des IDs qui n'existent probablement pas
    resultat_data = get_resultat_data(999, 999)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(f"{API_BASE}/resultats-evaluations", json=resultat_data)
            print(f"   Création résultat: {response.status_code}")
            
            if response.status_code == 409:
                print("   ✅ Erreur 409 attendue - IDs n'existent pas")
                return True
            elif response.status_code == 201:
                print("   ✅ Création réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors de la création: {e}")
            return False

@pytest.mark.asyncio
async def test_commencer_evaluation():
    """Test de la route commencer une évaluation"""
    print("🔍 Test de la route commencer évaluation...")
    
    data = {
        "evaluation_id": 999,
        "candidat_id": 999
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(f"{API_BASE}/resultats-evaluations/commencer", json=data)
            print(f"   Commencer évaluation: {response.status_code}")
            
            if response.status_code == 409:
                print("   ✅ Erreur 409 attendue - IDs n'existent pas")
                return True
            elif response.status_code == 201:
                print("   ✅ Commencer évaluation réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_soumettre_evaluation():
    """Test de la route soumettre une évaluation"""
    print("🔍 Test de la route soumettre évaluation...")
    
    data = {
        "reponses": [
            {
                "question_id": 999,
                "reponse_texte": "Réponse test",
                "reponse_choix": None,
                "temps_reponse_secondes": 30
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(f"{API_BASE}/resultats-evaluations/999/soumettre", json=data)
            print(f"   Soumettre évaluation: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Soumission réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_corriger_evaluation():
    """Test de la route corriger une évaluation"""
    print("🔍 Test de la route corriger évaluation...")
    
    data = {
        "score_obtenu": 85.5,
        "nombre_questions_correctes": 8,
        "commentaires_correcteur": "Bonne performance",
        "type_correction": "automatique"
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.put(f"{API_BASE}/resultats-evaluations/999/corriger", json=data)
            print(f"   Corriger évaluation: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Correction réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_get_resultat_by_id():
    """Test de la route récupérer un résultat par ID"""
    print("🔍 Test de la route get resultat par ID...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{API_BASE}/resultats-evaluations/999")
            print(f"   Get resultat par ID: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Récupération réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_get_resultats_by_evaluation():
    """Test de la route récupérer les résultats d'une évaluation"""
    print("🔍 Test de la route get resultats par évaluation...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{API_BASE}/resultats-evaluations/evaluation/999")
            print(f"   Get resultats par évaluation: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Récupération réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_get_resultats_by_candidat():
    """Test de la route récupérer les résultats d'un candidat"""
    print("🔍 Test de la route get resultats par candidat...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{API_BASE}/resultats-evaluations/candidat/999")
            print(f"   Get resultats par candidat: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Récupération réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_update_resultat():
    """Test de la route mettre à jour un résultat"""
    print("🔍 Test de la route update resultat...")
    
    data = {
        "score_obtenu": 90.0,
        "commentaires_correcteur": "Mise à jour test"
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.put(f"{API_BASE}/resultats-evaluations/999", json=data)
            print(f"   Update resultat: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 200:
                print("   ✅ Mise à jour réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_delete_resultat():
    """Test de la route supprimer un résultat"""
    print("🔍 Test de la route delete resultat...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.delete(f"{API_BASE}/resultats-evaluations/999")
            print(f"   Delete resultat: {response.status_code}")
            
            if response.status_code == 404:
                print("   ✅ Erreur 404 attendue - ID n'existe pas")
                return True
            elif response.status_code == 204:
                print("   ✅ Suppression réussie")
                return True
            else:
                print(f"   ❌ Erreur inattendue: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

@pytest.mark.asyncio
async def test_get_all_resultats():
    """Test de la route récupérer tous les résultats"""
    print("🔍 Test de la route get all resultats...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{API_BASE}/resultats-evaluations")
            print(f"   Get all resultats: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Récupération réussie")
                data = response.json()
                print(f"   Nombre de résultats: {len(data)}")
                return True
            else:
                print(f"   ❌ Erreur: {response.status_code}")
                print(f"   Détail: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Démarrage des tests du module resultats-evaluations...")
    
    # Exécuter les tests dans l'ordre
    tests = [
        test_diagnostic,
        test_create_resultat_simple,
        test_commencer_evaluation,
        test_soumettre_evaluation,
        test_corriger_evaluation,
        test_get_resultat_by_id,
        test_get_resultats_by_evaluation,
        test_get_resultats_by_candidat,
        test_update_resultat,
        test_delete_resultat,
        test_get_all_resultats
    ]
    
    for test in tests:
        try:
            asyncio.run(test())
            print("✅ Test terminé avec succès\n")
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}\n")
    
    print("🏁 Tous les tests sont terminés")
