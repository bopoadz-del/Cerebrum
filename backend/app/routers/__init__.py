"""
FastAPI routers for the Cerebrum platform.
"""

from app.routers.blocks import router as blocks_router
from app.routers.chat import router as chat_router
from app.routers.chain import router as chain_router
from app.routers.execute import router as execute_router
from app.routers.health import router as health_router_root
from app.routers.monitoring import router as monitoring_router
from app.routers.root import router as root_router
from app.routers.upload import router as upload_router

__all__ = [
    "blocks_router",
    "chat_router",
    "chain_router",
    "execute_router",
    "health_router_root",
    "monitoring_router",
    "root_router",
    "upload_router",
]
