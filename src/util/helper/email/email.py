import logging
import re
from email.message import EmailMessage
from typing import List
from fastapi import HTTPException, status
from aiosmtplib import SMTP, SMTPAuthenticationError, SMTPConnectError
from tzlocal import get_localzone
from datetime import datetime
from src.util.database.setting import settings
from src.util.helper.enum import (
    FileTypeEnum, MethodePaiementEnum, StatutFormationEnum,
    StatutInscriptionEnum, StatutPaiementEnum, StatutProjetIndividuelEnum
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EmailService:
    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self):
        self.smtp_host = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.GMAIL_EMAIL
        self.smtp_password = settings.GMAIL_PASSWORD
        self.smtp = None
        logger.info("[INIT] EmailService initialisé")

    async def _validate_smtp_config(self):
        """Valide la configuration SMTP."""
        logger.info("[CHECK] Validation des paramètres SMTP...")
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            logger.error("[ERREUR] Configuration SMTP incomplète")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration SMTP invalide"
            )
        logger.info("[OK] Configuration SMTP validée.")

    async def _connect_smtp(self):
        """Établit une connexion sécurisée TLS au serveur SMTP."""
        await self._validate_smtp_config()
        if self.smtp is None or not self.smtp.is_connected:
            logger.info(f"[CONNECT] Connexion sécurisée TLS à {self.smtp_host}:{self.smtp_port}...")
            self.smtp = SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=True,
                start_tls=False,
                timeout=10
            )
            try:
                await self.smtp.connect()
                logger.info("[CONNECTÉ] Connexion TLS établie")
                await self.smtp.login(self.smtp_user, self.smtp_password)
                logger.info("[LOGIN] Authentification SMTP réussie")
            except SMTPAuthenticationError:
                logger.error("❌ Échec de l'authentification SMTP")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur d'authentification SMTP"
                )
            except SMTPConnectError:
                logger.error(f"❌ Impossible de se connecter à {self.smtp_host}:{self.smtp_port}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur de connexion SMTP"
                )
            except Exception as e:
                logger.exception("❌ Exception lors de la connexion SMTP")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur SMTP: {str(e)}"
                )

    async def _create_message(self, to_email: str, subject: str, text_body: str, html_body: str) -> EmailMessage:
        """Crée un message email avec contenu texte et HTML."""
        logger.info(f"[CREATE] Création du message pour {to_email}")
        if not self.EMAIL_REGEX.match(to_email):
            logger.error(f"[ERREUR] Adresse email invalide: {to_email}")
            raise HTTPException(status_code=400, detail="Adresse email invalide")
        msg = EmailMessage()
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
        msg["From"] = f"{settings.GMAIL_USERNAME} <{self.smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        logger.info("[OK] Message créé avec succès")
        return msg

    async def _send_email(self, to_email: str, subject: str, text_body: str, html_body: str):
        """Envoie un email avec gestion des erreurs."""
        logger.info(f"[ENVOI] Email → {to_email} - Sujet: {subject}")
        await self._connect_smtp()
        msg = await self._create_message(to_email, subject, text_body, html_body)
        try:
            await self.smtp.send_message(msg)
            logger.info(f"✅ Email envoyé avec succès à {to_email}")
        except Exception as e:
            logger.exception(f"❌ Échec de l'envoi de l'email à {to_email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur d'envoi d'email: {str(e)}"
            )

    async def close(self):
        """Ferme la connexion SMTP."""
        if self.smtp and self.smtp.is_connected:
            logger.info("[FERMETURE] Fermeture de la connexion SMTP...")
            await self.smtp.quit()
            self.smtp = None
            logger.info("[FERMÉ] Connexion SMTP fermée")

    @staticmethod
    def _get_greeting(language: str = "fr") -> str:
        """Génère une salutation basée sur l'heure locale et la langue."""
        hour = datetime.now().hour
        if language == "en":
            return "Good evening dear user." if hour >= 18 else "Good morning dear user."
        return "Bonsoir cher utilisateur." if hour >= 18 else "Bonjour cher utilisateur."

    @staticmethod
    def _get_email_template(content: str, title: str, language: str = "fr") -> tuple[str, str]:
        """Génère les corps de texte et HTML pour les emails en fonction de la langue."""
        greeting = EmailService._get_greeting(language)
        team = settings.GMAIL_USERNAME
        if language == "en":
            text_body = f"{greeting}\n\n{content}\n\nBest regards,\nThe {team.capitalize()} team\n\n---\nIf you have any questions, please contact us at {settings.GMAIL_EMAIL}."
            contact_link = f'<a href="mailto:{settings.GMAIL_EMAIL}">{settings.GMAIL_EMAIL}</a>'
            signature = f"Best regards, The {team.capitalize()} team"
        else:
            text_body = f"{greeting}\n\n{content}\n\nCordialement,\nL'équipe {team.capitalize()}\n\n---\nSi vous avez des questions, contactez-nous à {settings.GMAIL_EMAIL}."
            contact_link = f'<a href="mailto:{settings.GMAIL_EMAIL}">{settings.GMAIL_EMAIL}</a>'
            signature = f"Cordialement, L'équipe {team.capitalize()}"

        html_body = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
    <head>
        <!--[if gte mso 9]>
        <xml>
            <o:OfficeDocumentSettings>
                <o:AllowPNG/>
                <o:PixelsPerInch>96</o:OfficeDocumentSettings>
            </xml>
        <![endif]-->
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta http-equiv="X-UA-Compatible" content="IE=edge" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="x-apple-disable-message-reformatting" />
        <link href="https://fonts.googleapis.com/css?family=PT+Serif:400,400i,700,700i|Poppins:400,400i,700,700i" rel="stylesheet" />
        <title>{title}</title>
        <style type="text/css">
            body {{ padding: 0 !important; margin: 0 !important; display: block !important; min-width: 100% !important; width: 100% !important; background: #ffffff; -webkit-text-size-adjust: none; }}
            .h3 {{ color: #000000; font-family: Arial, sans-serif; font-size: 22px; line-height: 32px; text-align: center; padding-bottom: 15px; }}
            .text {{ color: #666666; font-family: Arial, sans-serif; font-size: 15px; line-height: 28px; text-align: center; padding-bottom: 15px; }}
            .text-footer2 {{ color: #777777; font-family: Arial, sans-serif; font-size: 12px; line-height: 26px; text-align: center; padding-bottom: 20px; }}
        </style>
    </head>
    <body class="body">
        <span class="mcnPreviewText" style="display: none; font-size: 0px; line-height: 0px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; visibility: hidden; mso-hide: all;">*|MC_PREVIEW_TEXT|*</span>
        <table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#ffffff">
            <tr>
                <td align="center" valign="top">
                    <table width="650" border="0" cellspacing="0" cellpadding="0" class="mobile-shell">
                        <tr>
                            <td class="td" style="width: 650px; min-width: 650px; font-size: 0pt; line-height: 0pt; padding: 0; margin: 0; font-weight: normal;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td class="p30-15 tbrr" style="padding: 30px 0px 40px 0px; border-radius: 12px 12px 0px 0px;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="0"></table>
                                        </td>
                                    </tr>
                                </table>
                                <div mc:repeatable="Select" mc:variant="CTA">
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                        <tr>
                                            <td class="p30-15" style="padding: 60px 40px 60px 40px; background-color: #f4f4f4;">
                                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td class="h3">
                                                            <div mc:edit="text_11">
                                                                {greeting}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td class="text">
                                                            <div mc:edit="text_12">
                                                                {content}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td class="pb40" style="padding-bottom: 40px;"></td>
                                        </tr>
                                    </table>
                                </div>
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td class="p0-15-30" style="padding-bottom: 40px;">
                                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                                <tr>
                                                    <td class="text-footer2">
                                                        <div mc:edit="text_30">
                                                            <div class="footer">{signature}</div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """.format(
            title=title,
            greeting=greeting,
            content=content.replace('\n', '<br>'),
            signature=signature
        )
        return text_body, html_body


    async def send_otp_email(self, email: str, otp_code: str, language: str = "fr"):
        """Envoie un email avec un code OTP pour l'authentification.

        Args:
            email: Adresse email du destinataire.
            otp_code: Code OTP à envoyer.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info("[OTP] Préparation de l'envoi d'OTP...")
        if language == "en":
            content = (
                f"Following your request on our training platform, "
                f"please use the OTP code below to complete your authentication:\n\n"
                f"OTP Code: <b>{otp_code}</b>\n"
                f"This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes."
            )
            title = "Your OTP Code"
            subject = "OTP Code for Authentication"
        else:
            content = (
                f"Suite à votre demande sur notre plateforme de formation, "
                f"utilisez le code OTP suivant pour finaliser votre authentification :\n\n"
                f"Code OTP : <b>{otp_code}</b>\n"
                f"Ce code expirera dans {settings.OTP_EXPIRY_MINUTES} minutes."
            )
            title = "Votre code OTP"
            subject = "Code OTP pour authentification"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_new_user_email(self, email: str, new_password: str, language: str = "fr"):
        """Envoie un email avec un mot de passe temporaire pour un nouveau compte.

        Args:
            email: Adresse email du destinataire.
            new_password: Mot de passe temporaire.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info("[USER] Envoi des informations de nouveau compte...")
        if language == "en":
            content = (
                f"Your account has been successfully created on our training platform. "
                f"Your temporary password is: <b>{new_password}</b>\n"
                f"For security reasons, please change it upon your first login."
            )
            title = "Welcome to the Platform"
            subject = "Your New Account"
        else:
            content = (
                f"Votre compte a été créé avec succès sur notre plateforme de formation. "
                f"Votre mot de passe temporaire est : <b>{new_password}</b>\n"
                f"Pour des raisons de sécurité, veuillez le modifier lors de votre première connexion."
            )
            title = "Bienvenue sur la plateforme"
            subject = "Votre nouveau compte"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_change_password_email(self, email: str, new_password: str, language: str = "fr"):
        """Envoie un email de confirmation de changement de mot de passe.

        Args:
            email: Adresse email du destinataire.
            new_password: Nouveau mot de passe temporaire.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info("[PASSWORD] Envoi du nouveau mot de passe...")
        if language == "en":
            content = (
                f"Your password has been successfully changed on our platform. "
                f"Your new temporary password is: <b>{new_password}</b>."
            )
            title = "Password Change"
            subject = "Password Change Confirmation"
        else:
            content = (
                f"Votre mot de passe a été modifié avec succès sur notre plateforme. "
                f"Votre nouveau mot de passe temporaire est : <b>{new_password}</b>."
            )
            title = "Changement de mot de passe"
            subject = "Confirmation de changement de mot de passe"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_account_deleted_email(self, email: str, language: str = "fr"):
        """Envoie un email de notification de suppression de compte.

        Args:
            email: Adresse email du destinataire.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info("[ACCOUNT] Notification de suppression de compte...")
        local_tz = get_localzone()
        now = datetime.now(local_tz)
        date_str = now.strftime("%d/%m/%Y at %H:%M" if language == "en" else "%d/%m/%Y à %H:%M")
        if language == "en":
            content = (
                f"Your account has been <b>deleted</b> from our training platform on {date_str}.\n"
                f"If you believe this is an error, please contact our support."
            )
            title = "Account Deletion"
            subject = "Account Deletion Notification"
        else:
            content = (
                f"Votre compte a été <b>supprimé</b> de notre plateforme de formation le {date_str}.\n"
                f"Si vous pensez qu'il s'agit d'une erreur, contactez notre support."
            )
            title = "Suppression de compte"
            subject = "Notification de suppression de compte"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_password_reset(self, email: str, new_password: str, language: str = "fr"):
        """Envoie un email de réinitialisation de mot de passe.

        Args:
            email: Adresse email du destinataire.
            new_password: Nouveau mot de passe temporaire.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info("[RESET] Envoi du mot de passe réinitialisé...")
        if language == "en":
            content = (
                f"Your password reset request has been processed. "
                f"Your new password is: <b>{new_password}</b>\n"
                f"Please change it upon your next login for security."
            )
            title = "Password Reset"
            subject = "Password Reset"
        else:
            content = (
                f"Votre demande de réinitialisation de mot de passe a été prise en compte. "
                f"Votre nouveau mot de passe est : <b>{new_password}</b>\n"
                f"Modifiez-le dès votre prochaine connexion pour plus de sécurité."
            )
            title = "Réinitialisation de mot de passe"
            subject = "Réinitialisation de mot de passe"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_inscription_confirmation(self, email: str, formation_title: str, statut: StatutInscriptionEnum, language: str = "fr"):
        """Envoie un email de confirmation d'inscription à une formation.

        Args:
            email: Adresse email du destinataire.
            formation_title: Titre de la formation.
            statut: Statut de l'inscription (StatutInscriptionEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[INSCRIPTION] Envoi de confirmation d'inscription à {email}...")
        if language == "en":
            content = (
                f"Your registration for the training <b>{formation_title}</b> has been recorded with status <b>{statut.value}</b>.\n"
                f"Please check the details in your personal space on the platform."
            )
            title = "Registration Confirmation"
            subject = f"Registration: {formation_title}"
        else:
            content = (
                f"Votre inscription à la formation <b>{formation_title}</b> a été enregistrée avec le statut <b>{statut.value}</b>.\n"
                f"Consultez les détails dans votre espace personnel sur la plateforme."
            )
            title = "Confirmation d'inscription"
            subject = f"Inscription : {formation_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_inscription_status_update(self, email: str, formation_title: str, statut: StatutInscriptionEnum, language: str = "fr"):
        """Envoie un email de mise à jour du statut d'inscription.

        Args:
            email: Adresse email du destinataire.
            formation_title: Titre de la formation.
            statut: Statut de l'inscription (StatutInscriptionEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[INSCRIPTION] Envoi de mise à jour de statut d'inscription à {email}...")
        if language == "en":
            content = (
                f"The status of your registration for the training <b>{formation_title}</b> has been updated: <b>{statut.value}</b>.\n"
                f"Please check the details in your personal space on the platform."
            )
            title = "Registration Status Update"
            subject = f"Update: {formation_title}"
        else:
            content = (
                f"Le statut de votre inscription à la formation <b>{formation_title}</b> a été mis à jour : <b>{statut.value}</b>.\n"
                f"Consultez votre espace personnel pour plus de détails."
            )
            title = "Mise à jour de l'inscription"
            subject = f"Mise à jour : {formation_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_paiement_confirmation(self, email: str, montant: float, formation_title: str, methode: MethodePaiementEnum, statut: StatutPaiementEnum, language: str = "fr"):
        """Envoie un email de confirmation de paiement pour une formation.

        Args:
            email: Adresse email du destinataire.
            montant: Montant du paiement.
            formation_title: Titre de la formation.
            methode: Méthode de paiement (MethodePaiementEnum).
            statut: Statut du paiement (StatutPaiementEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[PAIEMENT] Envoi de confirmation de paiement à {email}...")
        if language == "en":
            content = (
                f"We confirm the receipt of your payment of <b>{montant} €</b> for the training <b>{formation_title}</b>.\n"
                f"Payment method: <b>{methode.value}</b> | Status: <b>{statut.value}</b>\n"
                f"Thank you for your payment. Please check the details in your personal space."
            )
            title = "Payment Confirmation"
            subject = "Payment Confirmation"
        else:
            content = (
                f"Nous confirmons la réception de votre paiement de <b>{montant} €</b> pour la formation <b>{formation_title}</b>.\n"
                f"Méthode de paiement : <b>{methode.value}</b> | Statut : <b>{statut.value}</b>\n"
                f"Merci pour votre règlement. Consultez les détails dans votre espace personnel."
            )
            title = "Confirmation de paiement"
            subject = "Confirmation de paiement"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_formation_status_update(self, email: str, formation_title: str, statut: StatutFormationEnum, language: str = "fr"):
        """Envoie un email de mise à jour du statut d'une formation.

        Args:
            email: Adresse email du destinataire.
            formation_title: Titre de la formation.
            statut: Statut de la formation (StatutFormationEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[FORMATION] Envoi de mise à jour de statut à {email}...")
        if language == "en":
            content = (
                f"The status of the training <b>{formation_title}</b> has been updated: <b>{statut.value}</b>.\n"
                f"Please check the details in your personal space on the platform."
            )
            title = "Training Status Update"
            subject = f"Update: {formation_title}"
        else:
            content = (
                f"Le statut de la formation <b>{formation_title}</b> a été mis à jour : <b>{statut.value}</b>.\n"
                f"Consultez votre espace personnel pour plus de détails."
            )
            title = "Mise à jour du statut de la formation"
            subject = f"Mise à jour : {formation_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_evaluation_result(self, email: str, evaluation_title: str, score: float, language: str = "fr"):
        """Envoie un email avec les résultats d'une évaluation.

        Args:
            email: Adresse email du destinataire.
            evaluation_title: Titre de l'évaluation.
            score: Score obtenu.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[EVALUATION] Envoi des résultats d'évaluation à {email}...")
        if language == "en":
            content = (
                f"Your evaluation <b>{evaluation_title}</b> has been completed.\n"
                f"Your score: <b>{score}</b>.\n"
                f"Please check the details in your personal space."
            )
            title = "Evaluation Results"
            subject = f"Results: {evaluation_title}"
        else:
            content = (
                f"Votre évaluation <b>{evaluation_title}</b> a été complétée.\n"
                f"Votre score : <b>{score}</b>.\n"
                f"Consultez les détails dans votre espace personnel."
            )
            title = "Résultats de l'évaluation"
            subject = f"Résultats : {evaluation_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_chef_d_oeuvre_submission(self, email: str, chef_d_oeuvre_title: str, statut: StatutProjetIndividuelEnum, language: str = "fr"):
        """Envoie un email de confirmation de soumission d'un chef-d'œuvre.

        Args:
            email: Adresse email du destinataire.
            chef_d_oeuvre_title: Titre du chef-d'œuvre.
            statut: Statut du chef-d'œuvre (StatutProjetIndividuelEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[CHEF_D_OEUVRE] Envoi de confirmation de soumission à {email}...")
        if language == "en":
            content = (
                f"Your masterpiece <b>{chef_d_oeuvre_title}</b> has been submitted with status <b>{statut.value}</b>.\n"
                f"You will receive a notification once it has been evaluated."
            )
            title = "Masterpiece Submission"
            subject = f"Submission: {chef_d_oeuvre_title}"
        else:
            content = (
                f"Votre chef-d'œuvre <b>{chef_d_oeuvre_title}</b> a été soumis avec le statut <b>{statut.value}</b>.\n"
                f"Vous recevrez une notification une fois qu'il sera évalué."
            )
            title = "Soumission de chef-d'œuvre"
            subject = f"Soumission : {chef_d_oeuvre_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_projet_collectif_invitation(self, email: str, projet_title: str, language: str = "fr"):
        """Envoie un email d'invitation à un projet collectif.

        Args:
            email: Adresse email du destinataire.
            projet_title: Titre du projet collectif.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[PROJET_COLLECTIF] Envoi d'invitation à {email}...")
        if language == "en":
            content = (
                f"You have been invited to join the collective project <b>{projet_title}</b>.\n"
                f"Please check the details and confirm your participation in your personal space."
            )
            title = "Collective Project Invitation"
            subject = f"Invitation: {projet_title}"
        else:
            content = (
                f"Vous avez été invité à rejoindre le projet collectif <b>{projet_title}</b>.\n"
                f"Consultez les détails et confirmez votre participation dans votre espace personnel."
            )
            title = "Invitation à un projet collectif"
            subject = f"Invitation : {projet_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_plan_intervention_update(self, email: str, plan_title: str, language: str = "fr"):
        """Envoie un email de mise à jour d'un plan d'intervention.

        Args:
            email: Adresse email du destinataire.
            plan_title: Titre du plan d'intervention.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[PLAN_INTERVENTION] Envoi de mise à jour à {email}...")
        if language == "en":
            content = (
                f"Your intervention plan <b>{plan_title}</b> has been updated.\n"
                f"Please check the details in your personal space."
            )
            title = "Intervention Plan Update"
            subject = f"Update: {plan_title}"
        else:
            content = (
                f"Votre plan d'intervention <b>{plan_title}</b> a été mis à jour.\n"
                f"Consultez les détails dans votre espace personnel."
            )
            title = "Mise à jour du plan d'intervention"
            subject = f"Mise à jour : {plan_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_accreditation_confirmation(self, email: str, accreditation_title: str, formation_title: str, language: str = "fr"):
        """Envoie un email de confirmation d'accréditation.

        Args:
            email: Adresse email du destinataire.
            accreditation_title: Titre de l'accréditation.
            formation_title: Titre de la formation.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[ACCREDITATION] Envoi de confirmation d'accréditation à {email}...")
        if language == "en":
            content = (
                f"Congratulations! You have obtained the accreditation <b>{accreditation_title}</b> for the training <b>{formation_title}</b>.\n"
                f"Please check the details in your personal space."
            )
            title = "Accreditation Confirmation"
            subject = f"Accreditation: {accreditation_title}"
        else:
            content = (
                f"Félicitations ! Vous avez obtenu l'accréditation <b>{accreditation_title}</b> pour la formation <b>{formation_title}</b>.\n"
                f"Consultez les détails dans votre espace personnel."
            )
            title = "Confirmation d'accréditation"
            subject = f"Accréditation : {accreditation_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_actualite_notification(self, email: str, actualite_title: str, language: str = "fr"):
        """Envoie un email de notification pour une nouvelle actualité.

        Args:
            email: Adresse email du destinataire.
            actualite_title: Titre de l'actualité.
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[ACTUALITE] Envoi de notification d'actualité à {email}...")
        if language == "en":
            content = (
                f"A new news item has been published: <b>{actualite_title}</b>.\n"
                f"Please check it in your personal space or on the platform."
            )
            title = "New News Item"
            subject = f"New News: {actualite_title}"
        else:
            content = (
                f"Une nouvelle actualité a été publiée : <b>{actualite_title}</b>.\n"
                f"Consultez-la dans votre espace personnel ou sur la plateforme."
            )
            title = "Nouvelle actualité"
            subject = f"Nouvelle actualité : {actualite_title}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_file_upload_confirmation(self, email: str, filename: str, file_type: FileTypeEnum, language: str = "fr"):
        """Envoie un email de confirmation de téléversement de fichier.

        Args:
            email: Adresse email du destinataire.
            filename: Nom du fichier téléversé.
            file_type: Type du fichier (FileTypeEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[FILE] Envoi de confirmation de téléversement à {email}...")
        if language == "en":
            content = (
                f"Your file <b>{filename}</b> (type: <b>{file_type.value}</b>) has been successfully uploaded.\n"
                f"Please check the details in your personal space."
            )
            title = "Upload Confirmation"
            subject = f"Upload: {filename}"
        else:
            content = (
                f"Votre fichier <b>{filename}</b> (type : <b>{file_type.value}</b>) a été téléversé avec succès.\n"
                f"Consultez les détails dans votre espace personnel."
            )
            title = "Confirmation de téléversement"
            subject = f"Téléversement : {filename}"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_multiple_files_upload_confirmation(self, email: str, filenames: List[str], file_type: FileTypeEnum, language: str = "fr"):
        """Envoie un email de confirmation de téléversement de plusieurs fichiers.

        Args:
            email: Adresse email du destinataire.
            filenames: Liste des noms des fichiers téléversés.
            file_type: Type des fichiers (FileTypeEnum).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[FILE] Envoi de confirmation de téléversement multiple à {email}...")
        files_list = "\n".join([f"- <b>{filename}</b>" for filename in filenames])
        if language == "en":
            content = (
                f"The following files (type: <b>{file_type.value}</b>) have been successfully uploaded:\n{files_list}\n"
                f"Please check the details in your personal space."
            )
            title = "Multiple Files Upload Confirmation"
            subject = "Files Upload Confirmation"
        else:
            content = (
                f"Les fichiers suivants (type : <b>{file_type.value}</b>) ont été téléversés avec succès :\n{files_list}\n"
                f"Consultez les détails dans votre espace personnel."
            )
            title = "Confirmation de téléversement multiple"
            subject = "Téléversement de fichiers"
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)

    async def send_custom_email(self, email: str, subject: str, content: str, title: str = None, language: str = "fr"):
        """Envoie un email personnalisé avec un sujet et contenu spécifiés.

        Args:
            email: Adresse email du destinataire.
            subject: Sujet de l'email.
            content: Contenu de l'email.
            title: Titre de l'email (optionnel, utilise le sujet si non spécifié).
            language: Langue de l'email ("fr" pour français, "en" pour anglais).

        Raises:
            HTTPException: 400 si l'email est invalide, 500 si erreur SMTP.
        """
        logger.info(f"[CUSTOM] Envoi d'un email personnalisé à {email}")
        title = title or subject
        text_body, html_body = self._get_email_template(content, title, language)
        await self._send_email(email, subject, text_body, html_body)