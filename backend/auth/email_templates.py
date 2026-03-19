"""
MATCHO — Templates Email Magic Link
© 2026 PEP's Swiss SA
"""


def magic_link_email_html(name: str, magic_url: str, expires_minutes: int = 15) -> str:
    """Template HTML pour l'email Magic Link de connexion"""
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#111;border-radius:16px;border:1px solid #222;overflow:hidden;">
  
  <!-- Header -->
  <tr><td style="padding:32px 32px 0;text-align:center;">
    <div style="display:inline-block;background:linear-gradient(135deg,#34d399,#059669);width:48px;height:48px;border-radius:12px;line-height:48px;font-weight:900;font-size:22px;color:#000;">M</div>
    <div style="color:#fff;font-size:20px;font-weight:700;margin-top:12px;letter-spacing:-0.3px;">MATCHO</div>
    <div style="color:#666;font-size:12px;margin-top:4px;">Matching comptable automatique</div>
  </td></tr>
  
  <!-- Content -->
  <tr><td style="padding:32px;">
    <div style="color:#fff;font-size:16px;margin-bottom:8px;">Bonjour {name},</div>
    <div style="color:#999;font-size:14px;line-height:1.6;margin-bottom:24px;">
      Cliquez sur le bouton ci-dessous pour vous connecter à MATCHO. Ce lien est valable <strong style="color:#fff;">{expires_minutes} minutes</strong> et ne peut être utilisé qu'une seule fois.
    </div>
    
    <!-- CTA Button -->
    <div style="text-align:center;margin:32px 0;">
      <a href="{magic_url}" style="display:inline-block;background:linear-gradient(135deg,#34d399,#059669);color:#000;font-weight:700;font-size:15px;padding:14px 40px;border-radius:12px;text-decoration:none;letter-spacing:-0.2px;">
        Se connecter à MATCHO →
      </a>
    </div>
    
    <div style="color:#666;font-size:12px;line-height:1.5;margin-bottom:16px;">
      Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur :
    </div>
    <div style="background:#0a0a0a;border:1px solid #222;border-radius:8px;padding:12px;word-break:break-all;">
      <a href="{magic_url}" style="color:#34d399;font-size:11px;text-decoration:none;">{magic_url}</a>
    </div>
  </td></tr>
  
  <!-- Security notice -->
  <tr><td style="padding:0 32px 24px;">
    <div style="background:#1a1a1a;border-radius:8px;padding:12px 16px;border-left:3px solid #34d399;">
      <div style="color:#999;font-size:11px;line-height:1.5;">
        🔒 Si vous n'avez pas demandé cette connexion, ignorez simplement cet email. Votre compte reste sécurisé.
      </div>
    </div>
  </td></tr>
  
  <!-- Footer -->
  <tr><td style="padding:20px 32px;border-top:1px solid #1a1a1a;text-align:center;">
    <div style="color:#444;font-size:11px;">
      MATCHO — Réconciliation bancaire automatique 🇨🇭<br>
      © 2026 PEP's Swiss SA · Courgenay, Jura, Suisse
    </div>
  </td></tr>
  
</table>
</td></tr>
</table>
</body>
</html>
"""


def invitation_email_html(
    name: str,
    inviter_name: str,
    role: str,
    invite_url: str,
) -> str:
    """Template HTML pour l'email d'invitation"""
    
    role_labels = {
        "collaborateur": "Collaborateur",
        "client": "Client",
        "reviseur": "Réviseur",
        "fiduciaire": "Fiduciaire",
    }
    role_label = role_labels.get(role, role.capitalize())
    
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#111;border-radius:16px;border:1px solid #222;overflow:hidden;">
  
  <!-- Header -->
  <tr><td style="padding:32px 32px 0;text-align:center;">
    <div style="display:inline-block;background:linear-gradient(135deg,#34d399,#059669);width:48px;height:48px;border-radius:12px;line-height:48px;font-weight:900;font-size:22px;color:#000;">M</div>
    <div style="color:#fff;font-size:20px;font-weight:700;margin-top:12px;">Vous êtes invité(e) !</div>
  </td></tr>
  
  <!-- Content -->
  <tr><td style="padding:32px;">
    <div style="color:#fff;font-size:16px;margin-bottom:8px;">Bonjour {name},</div>
    <div style="color:#999;font-size:14px;line-height:1.6;margin-bottom:16px;">
      <strong style="color:#fff;">{inviter_name}</strong> vous invite à rejoindre MATCHO en tant que <strong style="color:#34d399;">{role_label}</strong>.
    </div>
    
    <div style="color:#999;font-size:14px;line-height:1.6;margin-bottom:24px;">
      MATCHO est un outil de réconciliation bancaire automatique pour PME suisses. 
      Il matche vos relevés bancaires avec votre comptabilité grâce à l'intelligence artificielle.
    </div>
    
    <!-- Role badge -->
    <div style="text-align:center;margin:24px 0;">
      <span style="display:inline-block;background:#34d39920;color:#34d399;border:1px solid #34d39940;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;">
        ✨ Accès {role_label}
      </span>
    </div>
    
    <!-- CTA -->
    <div style="text-align:center;margin:32px 0;">
      <a href="{invite_url}" style="display:inline-block;background:linear-gradient(135deg,#34d399,#059669);color:#000;font-weight:700;font-size:15px;padding:14px 40px;border-radius:12px;text-decoration:none;">
        Accepter l'invitation →
      </a>
    </div>
  </td></tr>
  
  <!-- Footer -->
  <tr><td style="padding:20px 32px;border-top:1px solid #1a1a1a;text-align:center;">
    <div style="color:#444;font-size:11px;">
      MATCHO — Réconciliation bancaire automatique 🇨🇭<br>
      © 2026 PEP's Swiss SA · Courgenay, Jura, Suisse
    </div>
  </td></tr>
  
</table>
</td></tr>
</table>
</body>
</html>
"""
