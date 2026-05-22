import resend
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


async def send_verification_email(to_email: str, name: str, token: str) -> None:
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    resend.Emails.send({
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": "Verifica tu cuenta - Warehouse DT",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                    <td style="background: #185FA5; border-radius: 8px; width: 36px; height: 36px; text-align: center; vertical-align: middle;">
                        <span style="color: white; font-size: 18px; font-weight: bold; line-height: 36px; padding: 0 8px;">W</span>
                    </td>
                    <td style="padding-left: 10px; vertical-align: middle;">
                        <span style="font-size: 16px; font-weight: 600; color: #2C2C2A;">Warehouse DT</span>
                    </td>
                </tr>
            </table>
            <h1 style="font-size: 22px; font-weight: 600; color: #2C2C2A; margin: 0 0 12px 0;">Verifica tu cuenta</h1>
            <p style="font-size: 15px; color: #5F5E5A; margin: 0 0 28px 0; line-height: 1.5;">
                Hola <strong>{name}</strong>, haz clic en el botón para activar tu cuenta.<br>El enlace expira en 24 horas.
            </p>
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                    <td style="background: #185FA5; border-radius: 8px;">
                        <a href="{verification_url}"
                           style="display: inline-block; background: #185FA5; color: white; text-decoration: none; border-radius: 8px; padding: 13px 28px; font-size: 15px; font-weight: 600; font-family: Arial, sans-serif;">
                            Verificar cuenta
                        </a>
                    </td>
                </tr>
            </table>
            <p style="font-size: 12px; color: #888780; margin: 0; line-height: 1.5;">
                Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                <a href="{verification_url}" style="color: #185FA5; word-break: break-all;">{verification_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #E8E6DF; margin: 24px 0;">
            <p style="font-size: 12px; color: #AAAAAA; margin: 0;">
                Si no creaste esta cuenta, puedes ignorar este correo.
            </p>
        </div>
        """,
    })


async def send_reset_password_email(to_email: str, name: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    resend.Emails.send({
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": "Recuperar contraseña - Warehouse DT",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                    <td style="background: #185FA5; border-radius: 8px; width: 36px; height: 36px; text-align: center; vertical-align: middle;">
                        <span style="color: white; font-size: 18px; font-weight: bold; line-height: 36px; padding: 0 8px;">W</span>
                    </td>
                    <td style="padding-left: 10px; vertical-align: middle;">
                        <span style="font-size: 16px; font-weight: 600; color: #2C2C2A;">Warehouse DT</span>
                    </td>
                </tr>
            </table>
            <h1 style="font-size: 22px; font-weight: 600; color: #2C2C2A; margin: 0 0 12px 0;">Recuperar contraseña</h1>
            <p style="font-size: 15px; color: #5F5E5A; margin: 0 0 28px 0; line-height: 1.5;">
                Hola <strong>{name}</strong>, haz clic en el botón para establecer una nueva contraseña.<br>El enlace expira en 30 minutos.
            </p>
            <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
                <tr>
                    <td style="background: #185FA5; border-radius: 8px;">
                        <a href="{reset_url}"
                           style="display: inline-block; background: #185FA5; color: white; text-decoration: none; border-radius: 8px; padding: 13px 28px; font-size: 15px; font-weight: 600; font-family: Arial, sans-serif;">
                            Restablecer contraseña
                        </a>
                    </td>
                </tr>
            </table>
            <p style="font-size: 12px; color: #888780; margin: 0; line-height: 1.5;">
                Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                <a href="{reset_url}" style="color: #185FA5; word-break: break-all;">{reset_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #E8E6DF; margin: 24px 0;">
            <p style="font-size: 12px; color: #AAAAAA; margin: 0;">
                Si no solicitaste este cambio, puedes ignorar este correo.
            </p>
        </div>
        """,
    })
