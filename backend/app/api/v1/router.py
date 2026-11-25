from fastapi import APIRouter

from app.api.v1 import (
    admin,
    applications,
    assistant,
    auth,
    health,
    notifications,
    profile,
    saved,
    scholarships,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(scholarships.router)
api_router.include_router(saved.router)
api_router.include_router(applications.router)
api_router.include_router(notifications.router)
api_router.include_router(assistant.router)
api_router.include_router(admin.router)
