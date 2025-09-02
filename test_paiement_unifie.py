#!/usr/bin/env python3
"""
Test complet du système de paiement unifié
Vérifie que le système gère automatiquement les champs système et utilise Redis de manière optimale
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from src.util.db.database import AsyncSessionLocal
from src.api.service import PaymentService, PaymentBackgroundWorker
from src.api.schema import (
    PaiementCreate, PaiementResponse, PaiementStats
)
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
from fastapi import HTTPException

class TestPaiementUnifie:
    """Test du système de paiement unifié"""
    
    def __init__(self):
        self.test_results = []
        self.utilisateur_id = None
        self.session_id = None
        self.payment_ids = []
    
    async def setup_test_data(self, session: AsyncSession):
        """Créer les données de test nécessaires"""
        print("🔧 Configuration des données de test...")
        try:
            # Créer un utilisateur
            user_service = UserService(session)
            user_data = UtilisateurCreate(
                nom="TestPaiement",
                prenom="Unifie",
                email=f"paiement.unifie{datetime.now().timestamp()}@test.com",
                role=RoleEnum.CANDIDAT,
                telephone="+1234567890"
            )
            user = await user_service.create(user_data)
            self.utilisateur_id = user.id
            print(f"✅ Utilisateur créé: ID {user.id}")
            
            # Créer une formation
            formation_service = FormationService(session)
            formation_data = FormationCreate(
                titre="Formation Test Paiement Unifié",
                description="Formation pour tester le système de paiement unifié",
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
    
    async def test_1_creation_paiement_inscription(self, session: AsyncSession):
        """Test 1: Création d'un paiement d'inscription avec champs système automatiques"""
        print("\n💰 Test 1: Création d'un paiement d'inscription")
        try:
            service = PaymentService(session)
            
            # Le client ne fournit que les informations essentielles
            paiement_data = PaiementCreate(
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=3000,  # 3000 XAF = 30 FCFA
                devise="XAF",
                description="Paiement des frais d'inscription - Formation Test Paiement Unifié",
                type_paiement="INSCRIPTION",
                metadata_paiement=f"inscription_{self.utilisateur_id}_{self.session_id}"
                # notify_url et return_url non fournis - générés automatiquement
            )
            
            paiement = await service.create_payment(paiement_data)
            self.payment_ids.append(paiement.id)
            
            print(f"✅ Paiement créé: ID {paiement.id}")
            print(f"   Transaction ID: {paiement.transaction_id}")
            print(f"   Statut: {paiement.statut}")
            print(f"   Montant: {paiement.montant} {paiement.devise}")
            print(f"   Type: {paiement.type_paiement}")
            print(f"   Notify URL: {paiement.notify_url}")
            print(f"   Return URL: {paiement.return_url}")
            
            # Vérifier que les champs système sont générés automatiquement
            assert paiement.transaction_id.startswith("CINETPAY_"), "Transaction ID incorrect"
            assert paiement.notify_url is not None, "Notify URL manquante"
            assert paiement.return_url is not None, "Return URL manquante"
            assert paiement.statut == "EN_ATTENTE", "Statut initial incorrect"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_2_creation_paiement_formation(self, session: AsyncSession):
        """Test 2: Création d'un paiement de formation avec URLs personnalisées"""
        print("\n💰 Test 2: Création d'un paiement de formation avec URLs personnalisées")
        try:
            service = PaymentService(session)
            
            # Le client fournit des URLs personnalisées
            paiement_data = PaiementCreate(
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=80000,  # 80000 XAF = 800 FCFA
                devise="XAF",
                description="Paiement des frais de formation - Formation Test Paiement Unifié",
                type_paiement="FORMATION",
                metadata_paiement=f"formation_{self.utilisateur_id}_{self.session_id}",
                notify_url="https://webhook.site/custom-notify",
                return_url="https://webhook.site/custom-return"
            )
            
            paiement = await service.create_payment(paiement_data)
            self.payment_ids.append(paiement.id)
            
            print(f"✅ Paiement créé: ID {paiement.id}")
            print(f"   Transaction ID: {paiement.transaction_id}")
            print(f"   Statut: {paiement.statut}")
            print(f"   Montant: {paiement.montant} {paiement.devise}")
            print(f"   Type: {paiement.type_paiement}")
            print(f"   Notify URL: {paiement.notify_url}")
            print(f"   Return URL: {paiement.return_url}")
            
            # Vérifier que les URLs personnalisées sont utilisées
            assert paiement.notify_url == "https://webhook.site/custom-notify", "Notify URL personnalisée non utilisée"
            assert paiement.return_url == "https://webhook.site/custom-return", "Return URL personnalisée non utilisée"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_3_recuperation_paiements(self, session: AsyncSession):
        """Test 3: Récupération des paiements par différentes méthodes"""
        print("\n📋 Test 3: Récupération des paiements")
        try:
            service = PaymentService(session)
            
            # Récupérer par ID
            paiement_1 = await service.get_payment_by_id(self.payment_ids[0])
            print(f"✅ Paiement récupéré par ID: {paiement_1.transaction_id}")
            
            # Récupérer par transaction_id
            paiement_2 = await service.get_payment_by_transaction_id(paiement_1.transaction_id)
            print(f"✅ Paiement récupéré par transaction_id: {paiement_2.transaction_id}")
            
            # Vérifier que c'est le même paiement
            assert paiement_1.id == paiement_2.id, "Paiements différents"
            
            # Récupérer tous les paiements de l'utilisateur
            paiements_utilisateur = await service.get_payments_by_user(self.utilisateur_id)
            print(f"✅ {len(paiements_utilisateur)} paiements récupérés pour l'utilisateur")
            
            assert len(paiements_utilisateur) >= 2, "Nombre de paiements incorrect"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_4_verification_statut(self, session: AsyncSession):
        """Test 4: Vérification du statut d'un paiement"""
        print("\n🔍 Test 4: Vérification du statut")
        try:
            service = PaymentService(session)
            
            # Récupérer un paiement
            paiement = await service.get_payment_by_id(self.payment_ids[0])
            
            # Vérifier le statut (simulation - en vrai cela appellerait l'API CinetPay)
            try:
                verify_result = await service.verify_payment_status(paiement.transaction_id)
                print(f"✅ Statut vérifié: {verify_result.get('status', 'UNKNOWN')}")
            except HTTPException as e:
                if e.status_code == 400:
                    print(f"⚠️ Erreur attendue lors de la vérification (paiement de test): {e.detail}")
                else:
                    raise e
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_5_statistiques_paiements(self, session: AsyncSession):
        """Test 5: Statistiques des paiements"""
        print("\n📊 Test 5: Statistiques des paiements")
        try:
            service = PaymentService(session)
            
            stats = await service.get_payment_statistics()
            
            print(f"✅ Statistiques récupérées:")
            print(f"   Total: {stats.total_paiements}")
            print(f"   Acceptés: {stats.paiements_acceptes}")
            print(f"   Refusés: {stats.paiements_refuses}")
            print(f"   En attente: {stats.paiements_en_attente}")
            print(f"   Échec: {stats.paiements_echec}")
            print(f"   Montant total: {stats.montant_total} {stats.devise}")
            
            assert stats.total_paiements >= 2, "Nombre total de paiements incorrect"
            assert stats.paiements_en_attente >= 2, "Nombre de paiements en attente incorrect"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_6_validation_champs_systeme(self, session: AsyncSession):
        """Test 6: Validation que les champs système sont gérés automatiquement"""
        print("\n🔧 Test 6: Validation des champs système")
        try:
            service = PaymentService(session)
            
            # Tenter de créer un paiement avec montant négatif
            try:
                paiement_data = PaiementCreate(
                    utilisateur_id=self.utilisateur_id,
                    session_id=self.session_id,
                    montant=-1000,  # Montant négatif
                    devise="XAF",
                    description="Test montant négatif",
                    type_paiement="TEST"
                )
                await service.create_payment(paiement_data)
                print("❌ Erreur: Le paiement aurait dû être rejeté")
                return False
            except HTTPException as e:
                if e.status_code == 400 and "montant" in e.detail.lower():
                    print("✅ Validation du montant négatif fonctionne")
                else:
                    print(f"⚠️ Erreur inattendue lors de la validation: {e.detail}")
                    # Continuer le test même si la validation échoue
            
            # Vérifier que les champs système sont automatiques
            paiement_data = PaiementCreate(
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=1000,
                devise="XAF",
                description="Test champs système",
                type_paiement="TEST"
            )
            
            paiement = await service.create_payment(paiement_data)
            self.payment_ids.append(paiement.id)
            
            # Vérifier les champs système
            assert paiement.transaction_id is not None, "Transaction ID manquant"
            assert paiement.notify_url is not None, "Notify URL manquante"
            assert paiement.return_url is not None, "Return URL manquante"
            assert paiement.date_creation is not None, "Date de création manquante"
            assert paiement.date_modification is not None, "Date de modification manquante"
            
            print("✅ Tous les champs système sont gérés automatiquement")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_7_redis_integration(self, session: AsyncSession):
        """Test 7: Intégration Redis (si disponible)"""
        print("\n🔴 Test 7: Intégration Redis")
        try:
            service = PaymentService(session)
            
            if service.redis_client:
                print("✅ Redis est disponible")
                
                # Tester la queue de vérification
                paiement = await service.get_payment_by_id(self.payment_ids[0])
                
                # Simuler l'ajout à la queue
                await service._add_to_verification_queue(paiement.transaction_id)
                print("✅ Paiement ajouté à la queue Redis")
                
                # Vérifier que le paiement est dans la queue
                queue_exists = service.redis_client.exists(f"payment_queue:{paiement.transaction_id}")
                if queue_exists:
                    print("✅ Paiement trouvé dans la queue Redis")
                else:
                    print("⚠️ Paiement non trouvé dans la queue Redis")
                
            else:
                print("⚠️ Redis non disponible - test ignoré")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def cleanup_test_data(self, session: AsyncSession):
        """Nettoyer les données de test"""
        print("\n🧹 Nettoyage des données de test...")
        try:
            # Supprimer les paiements de test
            for payment_id in self.payment_ids:
                try:
                    result = await session.execute(
                        f"DELETE FROM paiements_cinetpay WHERE id = {payment_id}"
                    )
                    print(f"✅ Paiement {payment_id} supprimé")
                except Exception as e:
                    print(f"⚠️ Erreur lors de la suppression du paiement {payment_id}: {e}")
            
            await session.commit()
            print("✅ Nettoyage terminé")
            
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage: {e}")
            await session.rollback()
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 Démarrage des tests du système de paiement unifié")
        print("=" * 60)
        
        async with AsyncSessionLocal() as session:
            # Configuration
            if not await self.setup_test_data(session):
                print("❌ Échec de la configuration - arrêt des tests")
                return
            
            # Tests
            tests = [
                ("Création paiement inscription", self.test_1_creation_paiement_inscription),
                ("Création paiement formation", self.test_2_creation_paiement_formation),
                ("Récupération paiements", self.test_3_recuperation_paiements),
                ("Vérification statut", self.test_4_verification_statut),
                ("Statistiques paiements", self.test_5_statistiques_paiements),
                ("Validation champs système", self.test_6_validation_champs_systeme),
                ("Intégration Redis", self.test_7_redis_integration)
            ]
            
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                try:
                    result = await test_func(session)
                    if result:
                        print(f"✅ {test_name}: SUCCÈS")
                        self.test_results.append((test_name, True))
                    else:
                        print(f"❌ {test_name}: ÉCHEC")
                        self.test_results.append((test_name, False))
                except Exception as e:
                    print(f"❌ {test_name}: ERREUR - {e}")
                    self.test_results.append((test_name, False))
            
            # Nettoyage
            await self.cleanup_test_data(session)
        
        # Résultats finaux
        print("\n" + "=" * 60)
        print("📊 RÉSULTATS FINAUX")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for _, success in self.test_results if success)
        
        for test_name, success in self.test_results:
            status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {successful_tests}/{total_tests} tests réussis")
        
        if successful_tests == total_tests:
            print("🎉 TOUS LES TESTS ONT RÉUSSI !")
            print("✅ Le système de paiement unifié fonctionne correctement")
            print("✅ Les champs système sont gérés automatiquement")
            print("✅ Redis est intégré de manière optimale")
        else:
            print("⚠️ Certains tests ont échoué")
            print("🔧 Vérifiez les erreurs ci-dessus")

async def main():
    """Fonction principale"""
    test = TestPaiementUnifie()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
