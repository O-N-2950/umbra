"""
MATCHO — Module d'authentification
Magic Link + Multi-tenant Fiduciaire
© 2026 PEP's Swiss SA
"""
from .magic_link_auth import (
    AuthService,
    Role,
    Permission,
    User,
    Fiduciaire,
    Mandat,
    create_auth_routes,
)

__all__ = [
    "AuthService",
    "Role",
    "Permission",
    "User",
    "Fiduciaire",
    "Mandat",
    "create_auth_routes",
]
