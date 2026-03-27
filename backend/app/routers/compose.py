from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.route import SearchRequest, SearchResponse
from app.services.composer import compose_routes

router = APIRouter(prefix="/api", tags=["routes"])


@router.post("/compose", response_model=SearchResponse)
async def compose(request: SearchRequest) -> SearchResponse:
    if not request.origin.strip() or not request.destination.strip():
        raise HTTPException(status_code=400, detail="Origin and destination are required")

    routes = await compose_routes(
        request,
        google_key=settings.google_routes_api_key,
        serpapi_key=settings.serpapi_key,
    )

    if not routes:
        raise HTTPException(
            status_code=404,
            detail="No routes found between the given locations. Check that the addresses are valid.",
        )

    return SearchResponse(routes=routes)
