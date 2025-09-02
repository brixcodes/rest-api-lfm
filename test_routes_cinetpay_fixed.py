#!/usr/bin/env python3
"""
Test complet des routes API CinetPay
Vérifie que tous les endpoints fonctionnent correctement
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.util.db.database import AsyncSessionLocal
from src.main import app
from src.api.service import (
    UserService, FormationService, SessionFormationService
)
from src.api.schema import (
    UtilisateurCreate, FormationCreate, SessionFormationCreate
)
from src.util.helper.enum import (
    RoleEnum, SpecialiteEnum, TypeFormationEnum, ModaliteEnum, 
    DeviseEnum, StatutSessionEnum
)

class TestRoutesCinetPay:
    """Test des routes API CinetPay"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.test_results = []
        self.utilisateur_id = None
        self.session_id = None
        self.payment_id = None
        self.transaction_id = None
        
    async def setup_test_data(self):
        """Créer les données de test nécessaires"""
        print("🔧 Configuration des données de test...")
        
        async with AsyncSessionLocal() as session:
            try:
                # Créer un utilisateur
                user_service = UserService(session)
                user_data = UtilisateurCreate(
                    nom="TestCinetPay",
                    prenom="Jean",
                    email=f"jean.cinetpay{datetime.now().timestamp()}@test.com",
                    role=RoleEnum.CANDIDAT,
                    telephone="+1234567890"
                )
                user = await user_service.create(user_data)
                self.utilisateur_id = user.id
                print(f"✅ Utilisateur créé: ID {user.id}")
                
                # Créer une formation
                formation_service = FormationService(session)
                formation_data = FormationCreate(
                    titre="Formation Test CinetPay",
                    description="Formation pour tester l'intégration CinetPay",
                    type_formation=TypeFormationEnum.COURTE,
                    specialite=SpecialiteEnum.ACCUEIL,
                    duree_formation=40,
                    frais_formation=80000,
                    frais_inscription=3000,
                    devise=DeviseEnum.XAF
                )
                formation = await formation_service.create(formation_data)
                print(f"✅ Formation créée: ID {formation.id}")
                
                # Créer une session
                session_service = SessionFormationService(session)
                session_data = SessionFormationCreate(
                    formation_id=formation.id,
                    date_debut=datetime.now().date(),
                    date_fin=datetime.now().date(),
                    modalite=ModaliteEnum.PRESENTIEL,
                    statut=StatutSessionEnum.OUVERTE,
                    capacite_max=20
                )
                session_formation = await session_service.create(session_data)
                self.session_id = session_formation.id
                print(f"✅ Session créée: ID {session_formation.id}")
                
                return True
                
            except Exception as e:
                print(f"❌ Erreur lors de la configuration: {e}")
                return False
    
    def test_initier_paiement(self):
        """Test 1: POST /api/v1/paiements/initier"""
        print("\n💰 Test 1: POST /api/v1/paiements/initier")
        
        try:
            paiement_data = {
                "utilisateur_id": self.utilisateur_id,
                "session_id": self.session_id,
                "montant": 5000,  # 5000 XAF = 50 FCFA
                "devise": "XAF",
                "description": "Paiement des frais d'inscription - Formation Test CinetPay",
                "metadata_paiement": f"inscription_{self.utilisateur_id}_{self.session_id}",
                "notify_url": "https://webhook.site/d1dbbb89-52c7-49af-a689-b3c412df820d",
                "return_url": "https://webhook.site/d1dbbb89-52c7-49af-a689-b3c412df820d"
            }
            
            response = self.client.post("/api/v1/paiements/initier", json=paiement_data)
            
            if response.status_code == 200:
                data = response.json()
                self.payment_id = data["id"]
                self.transaction_id = data["transaction_id"]
                
                print("✅ Paiement initié avec succès")
                print(f"   ID: {data['id']}")
                print(f"   Transaction ID: {data['transaction_id']}")
                print(f"   Montant: {data['montant']} {data['devise']}")
                print(f"   Statut: {data['statut']}")
                print(f"   URL de paiement: {data['payment_url']}")
                
                self.test_results.append(("POST /api/v1/paiements/initier", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("POST /api/v1/paiements/initier", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("POST /api/v1/paiements/initier", False))
            return False
    
    def test_get_paiement_by_id(self):
        """Test 2: GET /api/v1/paiements/cinetpay/{payment_id}"""
        print("\n📄 Test 2: GET /api/v1/paiements/cinetpay/{payment_id}")
        
        if not self.payment_id:
            print("❌ Aucun payment_id disponible")
            self.test_results.append(("GET /api/v1/paiements/cinetpay/{payment_id}", False))
            return False
        
        try:
            response = self.client.get(f"/api/v1/paiements/cinetpay/{self.payment_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Paiement récupéré avec succès")
                print(f"   ID: {data['id']}")
                print(f"   Transaction ID: {data['transaction_id']}")
                print(f"   Montant: {data['montant']} {data['devise']}")
                print(f"   Statut: {data['statut']}")
                
                self.test_results.append(("GET /api/v1/paiements/cinetpay/{payment_id}", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/v1/paiements/cinetpay/{payment_id}", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("GET /api/v1/paiements/cinetpay/{payment_id}", False))
            return False
    
    def test_get_paiement_by_transaction(self):
        """Test 3: GET /api/v1/paiements/transaction/{transaction_id}"""
        print("\n🔄 Test 3: GET /api/v1/paiements/transaction/{transaction_id}")
        
        if not self.transaction_id:
            print("❌ Aucun transaction_id disponible")
            self.test_results.append(("GET /api/v1/paiements/transaction/{transaction_id}", False))
            return False
        
        try:
            response = self.client.get(f"/api/v1/paiements/transaction/{self.transaction_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Paiement récupéré par transaction_id avec succès")
                print(f"   ID: {data['id']}")
                print(f"   Transaction ID: {data['transaction_id']}")
                print(f"   Montant: {data['montant']} {data['devise']}")
                print(f"   Statut: {data['statut']}")
                
                self.test_results.append(("GET /api/v1/paiements/transaction/{transaction_id}", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/v1/paiements/transaction/{transaction_id}", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("GET /api/v1/paiements/transaction/{transaction_id}", False))
            return False
    
    def test_get_paiements_utilisateur(self):
        """Test 4: GET /api/v1/paiements/utilisateur/{utilisateur_id}"""
        print("\n👤 Test 4: GET /api/v1/paiements/utilisateur/{utilisateur_id}")
        
        if not self.utilisateur_id:
            print("❌ Aucun utilisateur_id disponible")
            self.test_results.append(("GET /api/v1/paiements/utilisateur/{utilisateur_id}", False))
            return False
        
        try:
            response = self.client.get(f"/api/v1/paiements/utilisateur/{self.utilisateur_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Paiements de l'utilisateur récupérés avec succès")
                print(f"   Nombre de paiements: {len(data)}")
                
                if len(data) > 0:
                    paiement = data[0]
                    print(f"   Premier paiement - ID: {paiement['id']}")
                    print(f"   Transaction ID: {paiement['transaction_id']}")
                    print(f"   Montant: {paiement['montant']} {paiement['devise']}")
                    print(f"   Statut: {paiement['statut']}")
                
                self.test_results.append(("GET /api/v1/paiements/utilisateur/{utilisateur_id}", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("GET /api/v1/paiements/utilisateur/{utilisateur_id}", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("GET /api/v1/paiements/utilisateur/{utilisateur_id}", False))
            return False
    
    def test_notification_endpoint(self):
        """Test 5: POST /api/v1/paiements/notification"""
        print("\n🔔 Test 5: POST /api/v1/paiements/notification")
        
        try:
            # Simuler une notification CinetPay
            notification_data = {
                "cpm_trans_id": self.transaction_id or "TEST_TRANSACTION",
                "cpm_amount": "5000",
                "cpm_currency": "XAF",
                "cpm_status": "ACCEPTED",
                "cpm_payid": "TEST_PAYID",
                "cpm_payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cpm_payment_time": datetime.now().strftime("%H:%M:%S"),
                "cpm_error_message": "",
                "cpm_phone_prefixe": "237",
                "cpm_phone_number": "123456789",
                "cpm_ipn_acl_token": "TEST_TOKEN",
                "cpm_language": "fr",
                "cpm_version": "V2",
                "cpm_reference": "TEST_REFERENCE",
                "cpm_designation": "Test payment"
            }
            
            headers = {"x-token": "test_hmac_token"}
            response = self.client.post("/api/v1/paiements/notification", data=notification_data, headers=headers)
            
            if response.status_code in [200, 400]:  # 400 attendu car token HMAC invalide
                print("✅ Endpoint de notification accessible")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
                self.test_results.append(("POST /api/v1/paiements/notification", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("POST /api/v1/paiements/notification", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("POST /api/v1/paiements/notification", False))
            return False
    
    def test_retour_endpoint(self):
        """Test 6: POST /api/v1/paiements/retour"""
        print("\n🔄 Test 6: POST /api/v1/paiements/retour")
        
        try:
            # Simuler un retour après paiement
            retour_data = {
                "transaction_id": self.transaction_id or "TEST_TRANSACTION",
                "status": "ACCEPTED",
                "amount": "5000",
                "currency": "XAF"
            }
            
            response = self.client.post("/api/v1/paiements/retour", data=retour_data)
            
            if response.status_code in [200, 400]:  # 400 attendu si transaction_id invalide
                print("✅ Endpoint de retour accessible")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                
                self.test_results.append(("POST /api/v1/paiements/retour", True))
                return True
            else:
                print(f"❌ Erreur: {response.status_code} - {response.text}")
                self.test_results.append(("POST /api/v1/paiements/retour", False))
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            self.test_results.append(("POST /api/v1/paiements/retour", False))
            return False
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 Démarrage des tests des routes API CinetPay")
        print("=" * 80)
        
        # Configuration des données de test
        if not await self.setup_test_data():
            print("❌ Échec de la configuration des données de test")
            return
        
        # Tests des routes
        self.test_initier_paiement()
        self.test_get_paiement_by_id()
        self.test_get_paiement_by_transaction()
        self.test_get_paiements_utilisateur()
        self.test_notification_endpoint()
        self.test_retour_endpoint()
        
        # Résultats
        print("\n" + "=" * 80)
        print("📊 RÉSULTATS DES TESTS")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        for test_name, success in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 Résumé: {passed_tests}/{total_tests} tests réussis")
        
        if failed_tests == 0:
            print("🎉 Tous les tests ont réussi !")
        else:
            print(f"⚠️  {failed_tests} test(s) ont échoué")

async def main():
    """Fonction principale"""
    tester = TestRoutesCinetPay()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
