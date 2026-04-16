"""Top-level API router."""

from fastapi import APIRouter

from research_pulse_cn.api.routes.admin import router as admin_router
from research_pulse_cn.api.routes.auth import router as auth_router
from research_pulse_cn.api.routes.client_devices import router as client_devices_router
from research_pulse_cn.api.routes.delivery_jobs import router as delivery_jobs_router
from research_pulse_cn.api.routes.digest_admin import router as digest_admin_router
from research_pulse_cn.api.routes.external_retrieval import (
    router as external_retrieval_router,
)
from research_pulse_cn.api.routes.group_workspace_admin import (
    router as group_workspace_admin_router,
)
from research_pulse_cn.api.routes.health import router as health_router
from research_pulse_cn.api.routes.mini import router as mini_router
from research_pulse_cn.api.routes.mini_admin import router as mini_admin_router
from research_pulse_cn.api.routes.official_account_binding_handshake_admin import (
    router as official_account_binding_handshake_admin_router,
)
from research_pulse_cn.api.routes.official_account_integration import (
    router as official_account_integration_router,
)
from research_pulse_cn.api.routes.ops import router as ops_router
from research_pulse_cn.api.routes.papers import router as papers_router
from research_pulse_cn.api.routes.pulse import router as pulse_router
from research_pulse_cn.api.routes.research_watch_profiles import (
    router as research_watch_profiles_router,
)
from research_pulse_cn.api.routes.result_shares import router as result_shares_router
from research_pulse_cn.api.routes.subscription_editor import (
    router as subscription_editor_router,
)
from research_pulse_cn.api.routes.subscription_editor_handoff_admin import (
    router as subscription_editor_handoff_admin_router,
)
from research_pulse_cn.api.routes.subscription_policies import (
    router as subscription_policies_router,
)
from research_pulse_cn.api.routes.subscription_self_service import (
    router as subscription_self_service_router,
)
from research_pulse_cn.api.routes.subscription_self_service_admin import (
    router as subscription_self_service_admin_router,
)
from research_pulse_cn.api.routes.sync import router as sync_router
from research_pulse_cn.api.routes.users import router as users_router
from research_pulse_cn.api.routes.work_activity import router as work_activity_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(client_devices_router)
api_router.include_router(digest_admin_router)
api_router.include_router(mini_admin_router)
api_router.include_router(group_workspace_admin_router)
api_router.include_router(subscription_self_service_admin_router)
api_router.include_router(subscription_editor_handoff_admin_router)
api_router.include_router(official_account_binding_handshake_admin_router)
api_router.include_router(mini_router)
api_router.include_router(subscription_self_service_router)
api_router.include_router(subscription_editor_router)
api_router.include_router(official_account_integration_router)
api_router.include_router(result_shares_router)
api_router.include_router(users_router)
api_router.include_router(papers_router)
api_router.include_router(subscription_policies_router)
api_router.include_router(research_watch_profiles_router)
api_router.include_router(work_activity_router)
api_router.include_router(external_retrieval_router)
api_router.include_router(pulse_router)
api_router.include_router(delivery_jobs_router)
api_router.include_router(ops_router)
api_router.include_router(sync_router)
