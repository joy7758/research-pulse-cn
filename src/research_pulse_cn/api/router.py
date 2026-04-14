"""Top-level API router."""

from fastapi import APIRouter

from research_pulse_cn.api.routes.admin import router as admin_router
from research_pulse_cn.api.routes.auth import router as auth_router
from research_pulse_cn.api.routes.delivery_jobs import router as delivery_jobs_router
from research_pulse_cn.api.routes.health import router as health_router
from research_pulse_cn.api.routes.ops import router as ops_router
from research_pulse_cn.api.routes.papers import router as papers_router
from research_pulse_cn.api.routes.pulse import router as pulse_router
from research_pulse_cn.api.routes.subscription_policies import (
    router as subscription_policies_router,
)
from research_pulse_cn.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(users_router)
api_router.include_router(papers_router)
api_router.include_router(subscription_policies_router)
api_router.include_router(pulse_router)
api_router.include_router(delivery_jobs_router)
api_router.include_router(ops_router)
