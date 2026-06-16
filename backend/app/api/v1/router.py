from fastapi import APIRouter

from backend.app.api.v1 import audits, auth, digital_twin, documents, health, hitl, reports, rules, users, webhooks, evidence_collectors
from backend.app.api.v1 import admin

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(documents.batch_router)
api_router.include_router(digital_twin.router)
api_router.include_router(audits.router)
api_router.include_router(audits.compat_router)
api_router.include_router(reports.router)
api_router.include_router(rules.router)
api_router.include_router(admin.router)
# Feature 1 (HITL review workflow) + Feature 2 (full diagnostics)
api_router.include_router(hitl.router)
# Feature 6 (Webhooks & API Keys)
api_router.include_router(webhooks.router)
# Feature 3 (Evidence Collectors)
api_router.include_router(evidence_collectors.router)
