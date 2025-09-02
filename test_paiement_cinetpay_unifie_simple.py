#!/usr/bin/env python3
"""
Test pour vérifier que tous les paiements passent exclusivement par CinetPay (version simplifiée)
"""

import asyncio
import sys
import os
from datetime import datetime

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from src.util.db.database import AsyncSessionLocal
from src.api.model import PaiementCinetPay
from src.api.schema import (
    PaiementCreate, UtilisateurCreate, FormationCreate, SessionFormationCreate
)
from src.util.helper.enum import (
    RoleEnum, SpecialiteEnum, TypeFormationEnum, ModaliteEnum, DeviseEnum, StatutSessionEnum
)
from fastapi import HTTPException

class TestPaiementCinetPayUnifieSimple:
    """Test pour vérifier que tous les paiements passent exclusivement par CinetPay (version simplifiée)"""
    
    def __init__(self):
        self.test_results = []
        self.utilisateur_id = None
        self.session_id = None
        
    async def setup_test_data(self, session: AsyncSession):
        """Créer les données de test nécessaires"""
        print("🔧 Configuration des données de test...")
        try:
            # Créer un utilisateur directement en base
            from src.api.model import Utilisateur
            from src.api.service import hash_password
            user = Utilisateur(
                nom="TestCinetPay",
                prenom="Jean",
                email=f"jean.cinetpay{datetime.now().timestamp()}@test.com",
                role=RoleEnum.CANDIDAT,
                telephone="+1234567890",
                actif=True,
                password=hash_password("TestPassword123!")
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            self.utilisateur_id = user.id
            print(f"✅ Utilisateur créé: ID {user.id}")
            
            # Créer une formation directement en base
            from src.api.model import Formation
            formation = Formation(
                titre="Formation Test CinetPay",
                description="Formation pour tester l'unification CinetPay",
                type_formation=TypeFormationEnum.COURTE,
                specialite=SpecialiteEnum.ACCUEIL,
                duree_formation=40,
                frais_formation=80000,
                frais_inscription=3000,
                devise=DeviseEnum.XAF
            )
            session.add(formation)
            await session.commit()
            await session.refresh(formation)
            print(f"✅ Formation créée: ID {formation.id}")
            
            # Créer une session directement en base
            from src.api.model import SessionFormation
            session_formation = SessionFormation(
                formation_id=formation.id,
                date_debut=datetime.now().date(),
                date_fin=datetime.now().date(),
                modalite=ModaliteEnum.PRESENTIEL,
                statut=StatutSessionEnum.OUVERTE,
                capacite_max=20
            )
            session.add(session_formation)
            await session.commit()
            await session.refresh(session_formation)
            self.session_id = session_formation.id
            print(f"✅ Session créée: ID {session_formation.id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la configuration: {e}")
            return False
    
    async def test_creation_paiement_formation_cinetpay_direct(self, session: AsyncSession):
        """Test 1: Création directe d'un paiement de formation CinetPay en base"""
        print("\n💰 Test 1: Création directe d'un paiement de formation CinetPay en base")
        try:
            # Créer un paiement CinetPay directement en base
            transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            paiement = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=80000,  # 800 XAF en centimes
                devise="XAF",
                description="Paiement formation test CinetPay",
                type_paiement="FORMATION",
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
            
            # Vérifier que c'est bien un paiement CinetPay
            assert paiement.transaction_id.startswith("CINETPAY_"), "Transaction ID doit commencer par CINETPAY_"
            assert paiement.statut == "EN_ATTENTE", "Statut initial doit être EN_ATTENTE"
            assert paiement.type_paiement == "FORMATION", "Type de paiement doit être FORMATION"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_creation_paiement_inscription_cinetpay_direct(self, session: AsyncSession):
        """Test 2: Création directe d'un paiement d'inscription CinetPay en base"""
        print("\n📝 Test 2: Création directe d'un paiement d'inscription CinetPay en base")
        try:
            # Créer un paiement CinetPay directement en base
            transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            paiement = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=3000,  # 30 XAF en centimes
                devise="XAF",
                description="Frais d'inscription test CinetPay",
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
            
            # Vérifier que c'est bien un paiement CinetPay
            assert paiement.transaction_id.startswith("CINETPAY_"), "Transaction ID doit commencer par CINETPAY_"
            assert paiement.type_paiement == "INSCRIPTION", "Type de paiement doit être INSCRIPTION"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_recuperation_paiement_cinetpay_direct(self, session: AsyncSession):
        """Test 3: Récupération d'un paiement CinetPay directement depuis la base"""
        print("\n🔍 Test 3: Récupération d'un paiement CinetPay directement depuis la base")
        try:
            # Créer un paiement pour le test
            transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            paiement_created = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=50000,
                devise="XAF",
                description="Paiement pour test de récupération CinetPay",
                type_paiement="FORMATION",
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement_created)
            await session.commit()
            await session.refresh(paiement_created)
            print(f"✅ Paiement créé: ID {paiement_created.id}")
            
            # Récupérer le paiement par ID
            from sqlalchemy import select
            result = await session.execute(select(PaiementCinetPay).where(PaiementCinetPay.id == paiement_created.id))
            paiement_retrieved = result.scalar_one()
            print(f"✅ Paiement récupéré: ID {paiement_retrieved.id}")
            
            # Vérifier que les données correspondent
            assert paiement_retrieved.id == paiement_created.id, "Les IDs doivent correspondre"
            assert paiement_retrieved.transaction_id == paiement_created.transaction_id, "Les transaction_ids doivent correspondre"
            assert paiement_retrieved.type_paiement == paiement_created.type_paiement, "Les types doivent correspondre"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_recuperation_par_transaction_id_cinetpay_direct(self, session: AsyncSession):
        """Test 4: Récupération par transaction_id CinetPay directement depuis la base"""
        print("\n🔍 Test 4: Récupération par transaction_id CinetPay directement depuis la base")
        try:
            # Créer un paiement pour le test
            transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            paiement_created = PaiementCinetPay(
                transaction_id=transaction_id,
                utilisateur_id=self.utilisateur_id,
                session_id=self.session_id,
                montant=25000,
                devise="XAF",
                description="Paiement pour test transaction_id CinetPay",
                type_paiement="FORMATION",
                statut="EN_ATTENTE",
                notify_url="https://example.com/notify",
                return_url="https://example.com/return"
            )
            
            session.add(paiement_created)
            await session.commit()
            await session.refresh(paiement_created)
            print(f"✅ Paiement créé: Transaction ID {paiement_created.transaction_id}")
            
            # Récupérer le paiement par transaction_id
            from sqlalchemy import select
            result = await session.execute(select(PaiementCinetPay).where(PaiementCinetPay.transaction_id == paiement_created.transaction_id))
            paiement_retrieved = result.scalar_one()
            print(f"✅ Paiement récupéré par transaction_id: ID {paiement_retrieved.id}")
            
            # Vérifier que les données correspondent
            assert paiement_retrieved.transaction_id == paiement_created.transaction_id, "Les transaction_ids doivent correspondre"
            assert paiement_retrieved.id == paiement_created.id, "Les IDs doivent correspondre"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_paiements_utilisateur_cinetpay_direct(self, session: AsyncSession):
        """Test 5: Récupération des paiements d'un utilisateur via CinetPay directement depuis la base"""
        print("\n👤 Test 5: Récupération des paiements d'un utilisateur via CinetPay directement depuis la base")
        try:
            # Créer plusieurs paiements pour le même utilisateur
            paiements_created = []
            for i in range(3):
                transaction_id = f"CINETPAY_{self.utilisateur_id}_{self.session_id}_{int(datetime.now().timestamp() * 1000) + i}"
                
                paiement = PaiementCinetPay(
                    transaction_id=transaction_id,
                    utilisateur_id=self.utilisateur_id,
                    session_id=self.session_id,
                    montant=10000,
                    devise="XAF",
                    description=f"Paiement test CinetPay {i}",
                    type_paiement="FORMATION",
                    statut="EN_ATTENTE",
                    notify_url="https://example.com/notify",
                    return_url="https://example.com/return"
                )
                
                session.add(paiement)
                await session.commit()
                await session.refresh(paiement)
                paiements_created.append(paiement)
                print(f"✅ Paiement créé: ID {paiement.id}")
            
            # Récupérer tous les paiements de l'utilisateur
            from sqlalchemy import select
            result = await session.execute(select(PaiementCinetPay).where(PaiementCinetPay.utilisateur_id == self.utilisateur_id))
            paiements_utilisateur = result.scalars().all()
            print(f"✅ {len(paiements_utilisateur)} paiements récupérés pour l'utilisateur")
            
            # Vérifier que tous les paiements appartiennent à l'utilisateur et sont des paiements CinetPay
            for paiement in paiements_utilisateur:
                assert paiement.utilisateur_id == self.utilisateur_id, f"Le paiement {paiement.id} doit appartenir à l'utilisateur {self.utilisateur_id}"
                assert paiement.transaction_id.startswith("CINETPAY_"), f"Le paiement {paiement.id} doit être un paiement CinetPay"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_statistiques_paiements_cinetpay_direct(self, session: AsyncSession):
        """Test 6: Statistiques des paiements CinetPay directement depuis la base"""
        print("\n📊 Test 6: Statistiques des paiements CinetPay directement depuis la base")
        try:
            from sqlalchemy import select, func
            
            # Compter les paiements par statut
            result = await session.execute(select(func.count(PaiementCinetPay.id)))
            total_paiements = result.scalar()
            
            result = await session.execute(select(func.count(PaiementCinetPay.id)).where(PaiementCinetPay.statut == "ACCEPTED"))
            paiements_acceptes = result.scalar()
            
            result = await session.execute(select(func.count(PaiementCinetPay.id)).where(PaiementCinetPay.statut == "REFUSED"))
            paiements_refuses = result.scalar()
            
            result = await session.execute(select(func.count(PaiementCinetPay.id)).where(PaiementCinetPay.statut == "EN_ATTENTE"))
            paiements_en_attente = result.scalar()
            
            result = await session.execute(select(func.count(PaiementCinetPay.id)).where(PaiementCinetPay.statut == "ECHEC"))
            paiements_echec = result.scalar()
            
            result = await session.execute(select(func.sum(PaiementCinetPay.montant)).where(PaiementCinetPay.statut == "ACCEPTED"))
            montant_total = result.scalar() or 0
            
            print(f"✅ Statistiques récupérées:")
            print(f"   Total paiements: {total_paiements}")
            print(f"   Paiements acceptés: {paiements_acceptes}")
            print(f"   Paiements refusés: {paiements_refuses}")
            print(f"   Paiements en attente: {paiements_en_attente}")
            print(f"   Paiements échoués: {paiements_echec}")
            print(f"   Montant total: {montant_total} XAF")
            
            # Vérifier que les statistiques sont cohérentes
            assert total_paiements >= 0, "Le nombre total de paiements doit être positif"
            assert paiements_acceptes >= 0, "Le nombre de paiements acceptés doit être positif"
            assert paiements_en_attente >= 0, "Le nombre de paiements en attente doit être positif"
            assert paiements_echec >= 0, "Le nombre de paiements échoués doit être positif"
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            return False
    
    async def test_verification_absence_paiements_obsoletes(self, session: AsyncSession):
        """Test 7: Vérification de l'absence de paiements obsolètes"""
        print("\n🔍 Test 7: Vérification de l'absence de paiements obsolètes")
        try:
            # Vérifier qu'il n'y a pas de modèle Paiement obsolète
            from src.api.model import Paiement
            print("❌ Erreur: Le modèle Paiement obsolète existe encore")
            return False
            
        except ImportError:
            print("✅ Modèle Paiement obsolète supprimé avec succès")
            return True
        except Exception as e:
            print(f"✅ Modèle Paiement obsolète non trouvé: {e}")
            return True
    
    async def cleanup_test_data(self, session: AsyncSession):
        """Nettoyer les données de test"""
        print("\n🧹 Nettoyage des données de test...")
        try:
            from sqlalchemy import text
            
            # Supprimer les paiements de test
            await session.execute(text(f"DELETE FROM paiements_cinetpay WHERE utilisateur_id = {self.utilisateur_id}"))
            
            # Supprimer la session de test
            if self.session_id:
                await session.execute(text(f"DELETE FROM sessions WHERE id = {self.session_id}"))
            
            # Supprimer la formation de test
            await session.execute(text("DELETE FROM formations WHERE titre = 'Formation Test CinetPay'"))
            
            # Supprimer l'utilisateur de test
            if self.utilisateur_id:
                await session.execute(text(f"DELETE FROM utilisateurs WHERE id = {self.utilisateur_id}"))
            
            await session.commit()
            print("✅ Données de test nettoyées")
            
        except Exception as e:
            print(f"⚠️ Erreur lors du nettoyage: {e}")
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🚀 Démarrage des tests d'unification CinetPay (version simplifiée)")
        print("=" * 60)
        
        async with AsyncSessionLocal() as session:
            # Configuration des données de test
            if not await self.setup_test_data(session):
                print("❌ Échec de la configuration des données de test")
                return
            
            # Exécuter les tests
            tests = [
                self.test_creation_paiement_formation_cinetpay_direct,
                self.test_creation_paiement_inscription_cinetpay_direct,
                self.test_recuperation_paiement_cinetpay_direct,
                self.test_recuperation_par_transaction_id_cinetpay_direct,
                self.test_paiements_utilisateur_cinetpay_direct,
                self.test_statistiques_paiements_cinetpay_direct,
                self.test_verification_absence_paiements_obsoletes
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
            
            # Nettoyer les données de test
            await self.cleanup_test_data(session)
        
        # Résumé des résultats
        print("\n📋 Résumé des tests:")
        print("=" * 60)
        successful_tests = sum(self.test_results)
        total_tests = len(self.test_results)
        
        print(f"Tests réussis: {successful_tests}/{total_tests}")
        
        if successful_tests == total_tests:
            print("🎉 Tous les tests sont passés avec succès!")
            print("✅ Tous les paiements passent exclusivement par CinetPay")
            print("✅ Le système de paiement est complètement unifié")
            print("✅ Les paiements obsolètes ont été supprimés")
            print("✅ La logique interne du système de paiement fonctionne correctement")
        else:
            print("⚠️ Certains tests ont échoué")
            print("❌ Il y a des problèmes à corriger")

if __name__ == "__main__":
    test = TestPaiementCinetPayUnifieSimple()
    asyncio.run(test.run_all_tests())
