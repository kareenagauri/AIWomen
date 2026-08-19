from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import content, goals_interests, health, me, onboarding, profile, recommendations, saved

settings = get_settings()

app = FastAPI(title="AI Women Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(profile.router)
app.include_router(onboarding.router)
app.include_router(goals_interests.router)
app.include_router(recommendations.router)
app.include_router(content.router)
app.include_router(saved.router)
