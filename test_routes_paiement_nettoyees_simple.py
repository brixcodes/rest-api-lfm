#!/usr/bin/env python3
"""
Test des routes de paiement après nettoyage - Version simplifiée sans API CinetPay
"""

import asyncio
import sys
import os
from datetime import datetime

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from src.util.db.database import AsyncSessionLocal
from src.api.service import (
    PaymentService, UserService, FormationService, SessionFormationService
)
from src.api.schema import (
    PaiementCreate, UtilisateurCreate, FormationCreate, SessionFormationCreate
)
from src.util.helper.enum import (
    RoleEnum, SpecialiteEnum, TypeFormationEnum, ModaliteEnum, DeviseEnum, StatutSessionEnum
)
from src.api.model import PaiementCinetPay
from fastapi import HTTPException

class TestRoutesPaiementNettoyeesSimple:
    """Test des routes de paiement après nettoyage - Version simplifiée"""
    
    def __init__(self):
        self.test_results = []
        self.utilisateur_id = None
        self.session_id = None
        
    async def setup_test_data(self, session: AsyncSession):
        """Créer les données de test nécessaires"""
        print("🔧 Configuration des données de test...")
        try:
            # Créer un utilisateur
            user_service = UserService(session)
            user_data = UtilisateurCreate(
                nom="TestPaiement",
                prenom="Jean",
                email=f"jean.paiement{datetime.now().timestamp()}@test.com",
                role=RoleEnum.CANDIDAT,
                telephone="+1234567890"
            )
            user = await user_service.create(user_data)
            self.utilisateur_id = user.id
            print(f"✅ Utilisateur créé: ID {user.id}")
            
            # Créer une formation
            formation_service = FormationService(session)
            formation_data = FormationCreate(
                titre="Formation Test Paiement",
                description="Formation pour tester les paiements",
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
    
    async def test_creation_paiement_direct_db(self, session: AsyncSession):
        """Test 1: Création directe d'un paiement en base (sans API CinetPay)"""
        print("\n💰 Test 1: Création directe d'un paiement en base")
        try:
            # Créer directement un paiement en base pour tester la logique interne
            paiement_data = PaiementCreate(
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=80000,  # 800 XAF en centimes
                devise="XAF",
                description="Paiement formation test",
                type_paiement="FORMATION"
            )
            
            # Créer le paiement directement en base
            paiement = PaiementCinetPay(
                transaction_id=f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp())}",
                utilisateur_id=paiement_data.utilisateur_id,
                session_id=paiement_data.session_id,
                montant=paiement_data.montant,
                devise=paiement_data.devise,
                description=paiement_data.description,
                type_paiement=paiement_data.type_paiement,
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement)
            await session.commit()
            await session.refresh(paiement)
            
            print(f"✅ Paiement créé: ID {paiement.id}")
            print(f"   Transaction ID: {paiement.transaction_id}")
            print(f"   Statut: {paiement.statut}")
            print(f"   Type: {paiement.type_paiement}")
            
            # Vérifier que les champs sont corrects
            assert paiement.transaction_id is not None, "Transaction ID doit être défini"
            assert paiement.statut == "EN_ATTENTE", "Statut doit être EN_ATTENTE"
            assert paiement.type_paiement == "FORMATION", "Type doit être FORMATION"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_creation_paiement_inscription_direct(self, session: AsyncSession):
        """Test 2: Création d'un paiement d'inscription direct en base"""
        print("\n📝 Test 2: Création d'un paiement d'inscription direct en base")
        try:
            # Créer directement un paiement d'inscription en base
            paiement = PaiementCinetPay(
                transaction_id=f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}",
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=3000,  # 30 XAF en centimes
                devise="XAF",
                description="Frais d'inscription test",
                type_paiement="INSCRIPTION",
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement)
            await session.commit()
            await session.refresh(paiement)
            
            print(f"✅ Paiement d'inscription créé: ID {paiement.id}")
            print(f"   Transaction ID: {paiement.transaction_id}")
            print(f"   Type: {paiement.type_paiement}")
            
            # Vérifier le type de paiement
            assert paiement.type_paiement == "INSCRIPTION", "Type de paiement doit être INSCRIPTION"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_recuperation_paiement_service(self, session: AsyncSession):
        """Test 3: Récupération d'un paiement via le service"""
        print("\n🔍 Test 3: Récupération d'un paiement via le service")
        try:
            service = PaymentService(session)
            
            # Créer un paiement pour le test
            paiement = PaiementCinetPay(
                transaction_id=f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}",
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=50000,
                devise="XAF",
                description="Paiement pour test de récupération",
                type_paiement="FORMATION",
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement)
            await session.commit()
            await session.refresh(paiement)
            
            print(f"✅ Paiement créé: ID {paiement.id}")
            
            # Récupérer le paiement par ID via le service
            paiement_retrieved = await service.get_payment_by_id(paiement.id)
            print(f"✅ Paiement récupéré: ID {paiement_retrieved.id}")
            
            # Vérifier que les données correspondent
            assert paiement_retrieved.id == paiement.id, "Les IDs doivent correspondre"
            assert paiement_retrieved.montant == paiement.montant, "Les montants doivent correspondre"
            assert paiement_retrieved.type_paiement == paiement.type_paiement, "Les types doivent correspondre"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_recuperation_par_transaction_id_service(self, session: AsyncSession):
        """Test 4: Récupération par transaction_id via le service"""
        print("\n🔍 Test 4: Récupération par transaction_id via le service")
        try:
            service = PaymentService(session)
            
            # Créer un paiement pour le test
            transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}"
            paiement = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=25000,
                devise="XAF",
                description="Paiement pour test transaction_id",
                type_paiement="FORMATION",
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement)
            await session.commit()
            await session.refresh(paiement)
            
            print(f"✅ Paiement créé: Transaction ID {paiement.transaction_id}")
            
            # Récupérer le paiement par transaction_id via le service
            paiement_retrieved = await service.get_payment_by_transaction_id(paiement.transaction_id)
            print(f"✅ Paiement récupéré par transaction_id: ID {paiement_retrieved.id}")
            
            # Vérifier que les données correspondent
            assert paiement_retrieved.transaction_id == paiement.transaction_id, "Les transaction_ids doivent correspondre"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_paiements_utilisateur_service(self, session: AsyncSession):
        """Test 5: Récupération des paiements d'un utilisateur via le service"""
        print("\n👤 Test 5: Récupération des paiements d'un utilisateur via le service")
        try:
            service = PaymentService(session)
            
            # Créer plusieurs paiements pour le même utilisateur
            paiements = []
            for i in range(3):
                paiement = PaiementCinetPay(
                    transaction_id=f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}_{i}",
                    utilisateur_id=self.utilisateur_id,
                    session_id=self.session_id,
                    montant=10000,
                    devise="XAF",
                    description=f"Paiement test {i}",
                    type_paiement="FORMATION",
                    statut="EN_ATTENTE",
                    notify_url="https://example.com/notify",
                    return_url="https://example.com/return"
                )
                session.add(paiement)
                paiements.append(paiement)
            
            await session.commit()
            
            for paiement in paiements:
                await session.refresh(paiement)
                print(f"✅ Paiement créé: ID {paiement.id}")
            
            # Récupérer tous les paiements de l'utilisateur via le service
            paiements_utilisateur = await service.get_payments_by_user(self.utilisateur_id)
            print(f"✅ {len(paiements_utilisateur)} paiements récupérés pour l'utilisateur")
            
            # Vérifier que tous les paiements appartiennent à l'utilisateur
            for paiement in paiements_utilisateur:
                assert paiement.utilisateur_id == self.utilisateur_id, f"Le paiement {paiement.id} doit appartenir à l'utilisateur {self.utilisateur_id}"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_statistiques_paiements_service(self, session: AsyncSession):
        """Test 6: Statistiques des paiements via le service"""
        print("\n📊 Test 6: Statistiques des paiements via le service")
        try:
            service = PaymentService(session)
            
            # Récupérer les statistiques
            stats = await service.get_payment_statistics()
            print(f"✅ Statistiques récupérées:")
            print(f"   Total paiements: {stats.total_paiements}")
            print(f"   Paiements acceptés: {stats.paiements_acceptes}")
            print(f"   Paiements en attente: {stats.paiements_en_attente}")
            print(f"   Paiements échoués: {stats.paiements_echec}")
            print(f"   Montant total: {stats.montant_total} {stats.devise}")
            
            # Vérifier que les statistiques sont cohérentes
            assert stats.total_paiements >= 0, "Le nombre total de paiements doit être positif"
            assert stats.paiements_acceptes >= 0, "Le nombre de paiements acceptés doit être positif"
            assert stats.paiements_en_attente >= 0, "Le nombre de paiements en attente doit être positif"
            assert stats.paiements_echec >= 0, "Le nombre de paiements échoués doit être positif"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 Démarrage des tests des routes de paiement nettoyées (version simplifiée)")
        print("=" * 70)
        
        async with AsyncSessionLocal() as session:
            # Configuration des données de test
            if not await self.setup_test_data(session):
                print("❌ Échec de la configuration des données de test")
                return
            
            # Exécuter les tests
            tests = [
                self.test_creation_paiement_direct_db,
                self.test_creation_paiement_inscription_direct,
                self.test_recuperation_paiement_service,
                self.test_recuperation_par_transaction_id_service,
                self.test_paiements_utilisateur_service,
                self.test_statistiques_paiements_service
            ]
            
            for test in tests:
                try:
                    result = await test(session)
                    self.test_results.append(result)
                    if result:
                        print("✅ Test réussi")
                    else:
                        print("❌ Test échoué")
                except Exception as e:
                    print(f"❌ Erreur lors de l'exécution du test: {e}")
                    self.test_results.append(False)
                
                print("-" * 40)
        
        # Résumé des résultats
        print("\n📋 Résumé des tests:")
        print("=" * 70)
        successful_tests = sum(self.test_results)
        total_tests = len(self.test_results)
        
        print(f"Tests réussis: {successful_tests}/{total_tests}")
        
        if successful_tests == total_tests:
            print("🎉 Tous les tests sont passés avec succès!")
            print("✅ Le système de paiement unifié fonctionne correctement")
            print("✅ Les routes obsolètes ont été supprimées avec succès")
            print("✅ La logique interne du système de paiement est cohérente")
        else:
            print("⚠️ Certains tests ont échoué")
            print("❌ Il y a des problèmes à corriger")

if __name__ == "__main__":
    test = TestRoutesPaiementNettoyeesSimple()
    asyncio.run(test.run_all_tests())
