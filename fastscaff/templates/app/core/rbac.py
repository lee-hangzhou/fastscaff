import asyncio
from pathlib import Path
from typing import Any, List, Optional, Union

from fastapi import Request

from app.core.logger import logger
from app.core.singleton import Singleton
from app.exceptions.codes import ErrForbidden, ErrUnauthorized

CASBIN_AVAILABLE = False

try:
    import casbin

    CASBIN_AVAILABLE = True
except ImportError:
    casbin = None  # type: ignore[assignment]


# Default RBAC model definition (ACL with role hierarchy)
DEFAULT_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""

# RBAC model with domain/tenant support
DOMAIN_MODEL = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
"""


class RBACEnforcer(Singleton):
    """Async RBAC enforcer using Casbin."""

    _enforcer: Optional[Any] = None
    _initialized: bool = False
    _init_lock: Optional[asyncio.Lock] = None

    def __init__(self) -> None:
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

    async def init(
        self,
        model: Optional[str] = None,
        adapter: Optional[str] = None,
        use_domain: bool = False,
    ) -> None:
        if not CASBIN_AVAILABLE or casbin is None:
            logger.warning(
                "Casbin not installed. RBAC disabled. "
                "Install with: pip install casbin casbin-async-sqlalchemy-adapter"
            )
            return

        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            if self._initialized:
                return

            model_text = model or (DOMAIN_MODEL if use_domain else DEFAULT_MODEL)

            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".conf", delete=False
            ) as f:
                f.write(model_text)
                model_path = f.name

            try:
                if adapter is None or adapter == "memory":
                    enforcer_instance = casbin.AsyncEnforcer(model_path)
                elif adapter.startswith(("postgresql", "mysql", "sqlite")):
                    from casbin_async_sqlalchemy_adapter import Adapter

                    db_adapter = Adapter(adapter)
                    enforcer_instance = casbin.AsyncEnforcer(model_path, db_adapter)
                else:
                    enforcer_instance = casbin.AsyncEnforcer(model_path, adapter)

                await enforcer_instance.load_policy()
                self._enforcer = enforcer_instance
                self._initialized = True
                logger.info("RBAC enforcer initialized")

            finally:
                Path(model_path).unlink(missing_ok=True)

    async def enforce(
        self,
        subject: Union[str, int],
        resource: str,
        action: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            logger.error("RBAC not initialized, denying by default")
            return False

        sub = str(subject)

        try:
            if domain:
                return await self._enforcer.enforce(sub, domain, resource, action)
            return await self._enforcer.enforce(sub, resource, action)
        except Exception as e:
            logger.error("RBAC enforce error", exc=e)
            return False

    async def add_policy(
        self,
        subject: Union[str, int],
        resource: str,
        action: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        sub = str(subject)

        try:
            if domain:
                return await self._enforcer.add_policy(sub, domain, resource, action)
            return await self._enforcer.add_policy(sub, resource, action)
        except Exception as e:
            logger.error("RBAC add_policy error", exc=e)
            return False

    async def remove_policy(
        self,
        subject: Union[str, int],
        resource: str,
        action: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        sub = str(subject)

        try:
            if domain:
                return await self._enforcer.remove_policy(sub, domain, resource, action)
            return await self._enforcer.remove_policy(sub, resource, action)
        except Exception as e:
            logger.error("RBAC remove_policy error", exc=e)
            return False

    async def add_role_for_user(
        self,
        user: Union[str, int],
        role: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        user_str = str(user)

        try:
            if domain:
                return await self._enforcer.add_role_for_user_in_domain(
                    user_str, role, domain
                )
            return await self._enforcer.add_role_for_user(user_str, role)
        except Exception as e:
            logger.error("RBAC add_role_for_user error", exc=e)
            return False

    async def delete_role_for_user(
        self,
        user: Union[str, int],
        role: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        user_str = str(user)

        try:
            if domain:
                return await self._enforcer.delete_role_for_user_in_domain(
                    user_str, role, domain
                )
            return await self._enforcer.delete_role_for_user(user_str, role)
        except Exception as e:
            logger.error("RBAC delete_role_for_user error", exc=e)
            return False

    async def get_roles_for_user(
        self,
        user: Union[str, int],
        domain: Optional[str] = None,
    ) -> List[str]:
        if not self._initialized or not self._enforcer:
            return []

        user_str = str(user)

        try:
            if domain:
                return await self._enforcer.get_roles_for_user_in_domain(
                    user_str, domain
                )
            return await self._enforcer.get_roles_for_user(user_str)
        except Exception as e:
            logger.error("RBAC get_roles_for_user error", exc=e)
            return []

    async def get_users_for_role(
        self,
        role: str,
        domain: Optional[str] = None,
    ) -> List[str]:
        if not self._initialized or not self._enforcer:
            return []

        try:
            if domain:
                return await self._enforcer.get_users_for_role_in_domain(role, domain)
            return await self._enforcer.get_users_for_role(role)
        except Exception as e:
            logger.error("RBAC get_users_for_role error", exc=e)
            return []

    async def has_role_for_user(
        self,
        user: Union[str, int],
        role: str,
        domain: Optional[str] = None,
    ) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        user_str = str(user)

        try:
            if domain:
                roles = await self.get_roles_for_user(user_str, domain)
                return role in roles
            return await self._enforcer.has_role_for_user(user_str, role)
        except Exception as e:
            logger.error("RBAC has_role_for_user error", exc=e)
            return False

    async def get_permissions_for_user(
        self,
        user: Union[str, int],
        domain: Optional[str] = None,
    ) -> List[List[str]]:
        if not self._initialized or not self._enforcer:
            return []

        user_str = str(user)

        try:
            if domain:
                return await self._enforcer.get_implicit_permissions_for_user(
                    user_str, domain
                )
            return await self._enforcer.get_implicit_permissions_for_user(user_str)
        except Exception as e:
            logger.error("RBAC get_permissions_for_user error", exc=e)
            return []

    async def delete_user(self, user: Union[str, int]) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        user_str = str(user)

        try:
            return await self._enforcer.delete_user(user_str)
        except Exception as e:
            logger.error("RBAC delete_user error", exc=e)
            return False

    async def delete_role(self, role: str) -> bool:
        if not self._initialized or not self._enforcer:
            return False

        try:
            return await self._enforcer.delete_role(role)
        except Exception as e:
            logger.error("RBAC delete_role error", exc=e)
            return False


enforcer = RBACEnforcer()


class RequirePermission:
    def __init__(
        self,
        resource: str,
        action: str,
        domain: Optional[str] = None,
    ) -> None:
        self.resource = resource
        self.action = action
        self.domain = domain

    async def __call__(self, request: Request) -> None:
        user_id = getattr(request.state, "user_id", None)

        if user_id is None:
            raise ErrUnauthorized.new("Authentication required")

        domain = self.domain
        if domain is None:
            domain = getattr(request.state, "domain", None)

        if not await enforcer.enforce(user_id, self.resource, self.action, domain):
            raise ErrForbidden.new(
                f"Permission denied: {self.action} on {self.resource}"
            )


def require_permission(
    resource: str,
    action: str,
    domain: Optional[str] = None,
) -> RequirePermission:
    return RequirePermission(resource, action, domain)


def require_role(role: str, domain: Optional[str] = None):
    async def check_role(request: Request) -> None:
        user_id = getattr(request.state, "user_id", None)

        if user_id is None:
            raise ErrUnauthorized.new("Authentication required")

        check_domain = domain or getattr(request.state, "domain", None)

        if not await enforcer.has_role_for_user(user_id, role, check_domain):
            raise ErrForbidden.new(f"Role required: {role}")

    return check_role
