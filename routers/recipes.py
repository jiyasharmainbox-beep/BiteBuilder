import json
from pathlib import Path
from typing import Annotated, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser
from config import settings
from database import get_db
import models
from schemas import FavouriteRecipeCreate, FavouriteRecipeResponse


RECIPES_DATA_PATH = Path(__file__).parent / "recipesData.json"
RECIPES_PER_PAGE = 6

router = APIRouter()


def _load_recipes() -> list[dict]:
    with RECIPES_DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


# GET https://api.spoonacular.com/recipes/findByIngredients?ingredients=apples,+flour,+sugar&number=2
def _fetch_recipes_from_api(ingredients: list[str], number: int = 10) -> list[dict]:
    params = {
        "ingredients": ",".join(ingredients),
        "number": number,
        "apiKey": settings.spoonacular_api_key,
    }
    response = httpx.get("https://api.spoonacular.com/recipes/findByIngredients", params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _search_recipes(recipes: list[dict], terms: list[str]) -> list[dict]:
    """Return recipes where at least one ingredient name matches any search term."""
    lower_terms = [t.lower().strip() for t in terms if t.strip()]
    if not lower_terms:
        return list(recipes)

    def matches(recipe: dict) -> bool:
        all_ingredients = (
            recipe.get("usedIngredients", [])
            + recipe.get("missedIngredients", [])
            + recipe.get("unusedIngredients", [])
        )
        names = [i.get("name", "").lower() for i in all_ingredients]
        return any(term in name for term in lower_terms for name in names)

    matched = [r for r in recipes if matches(r)]
    # Recipes that use more of the provided ingredients appear first
    matched.sort(
        key=lambda r: (r.get("usedIngredientCount", 0), r.get("likes", 0)),
        reverse=True,
    )
    return matched


class IngredientSummary(BaseModel):
    id: int
    name: str
    image: str


class RecipeSummary(BaseModel):
    id: int
    title: str
    image: str
    likes: int
    usedIngredientCount: int
    missedIngredientCount: int
    usedIngredients: list[IngredientSummary]
    missedIngredients: list[IngredientSummary]


class RecipeSearchResponse(BaseModel):
    recipes: list[RecipeSummary]
    total: int
    skip: int
    limit: int
    has_more: bool


@router.get(
    "/search",
    response_model=RecipeSearchResponse,
    summary="Search recipes by ingredients",
    description=(
        "Searches the local recipe dataset for recipes that contain any of the "
        "provided comma-separated ingredient names. Results are ordered by how "
        "many of the given ingredients are already used in the recipe."
    ),
)
def search_recipes(
    ingredients: Annotated[str, Query(description="Comma-separated ingredient names")],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = RECIPES_PER_PAGE,
) -> RecipeSearchResponse:
    terms = [t.strip() for t in ingredients.split(",") if t.strip()]
    #matched = _search_recipes(all_recipes, terms)
    try:
        matched = _fetch_recipes_from_api(terms, number=100)  # Fetch from API instead of local dataset
    except httpx.HTTPError:
        # If API call fails, fall back to local dataset search
        all_recipes = _load_recipes()
        matched = _search_recipes(all_recipes, terms)

    total = len(matched)
    page = matched[skip : skip + limit]

    def to_summary(r: dict) -> RecipeSummary:
        def slim(lst: list[dict]) -> list[IngredientSummary]:
            return [
                IngredientSummary(
                    id=i.get("id", 0),
                    name=i.get("name", ""),
                    image=i.get("image", ""),
                )
                for i in lst
            ]

        return RecipeSummary(
            id=r["id"],
            title=r["title"],
            image=r.get("image", ""),
            likes=r.get("likes", 0),
            usedIngredientCount=r.get("usedIngredientCount", 0),
            missedIngredientCount=r.get("missedIngredientCount", 0),
            usedIngredients=slim(r.get("usedIngredients", [])),
            missedIngredients=slim(r.get("missedIngredients", [])),
        )

    return RecipeSearchResponse(
        recipes=[to_summary(r) for r in page],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(page) < total,
    )


class ClassifyImageResponse(BaseModel):
    ingredient: str
    confidence: float


@router.post(
    "/classify-image",
    response_model=ClassifyImageResponse,
    summary="Identify an ingredient from a photo",
    description=(
        "Uploads a food photo and uses the Spoonacular image-classification API "
        "to identify the ingredient. Requires SPOONACULAR_API_KEY to be set in .env."
    ),
)
async def classify_ingredient_image(file: UploadFile) -> ClassifyImageResponse:
    if not settings.spoonacular_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Image classification is not configured. "
                "Set SPOONACULAR_API_KEY in your .env file."
            ),
        )

    content = await file.read()

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.spoonacular.com/food/images/classify",
            params={"apiKey": settings.spoonacular_api_key},
            files={
                "file": (
                    file.filename or "ingredient.jpg",
                    content,
                    file.content_type or "image/jpeg",
                )
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image classification service returned an error. Please try again.",
        )

    data = response.json()
    return ClassifyImageResponse(
        ingredient=data.get("category", ""),
        confidence=data.get("probability", 0.0),
    )


# ── Favourites ────────────────────────────────────────────────────────────────

@router.get(
    "/favourites",
    response_model=list[FavouriteRecipeResponse],
    summary="Get current user's favourite recipes",
)
async def get_favourites(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FavouriteRecipeResponse]:
    result = await db.execute(
        select(models.FavouriteRecipe)
        .where(models.FavouriteRecipe.user_id == current_user.id)
        .order_by(models.FavouriteRecipe.saved_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/favourites",
    response_model=FavouriteRecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a recipe to favourites",
)
async def add_favourite(
    payload: FavouriteRecipeCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FavouriteRecipeResponse:
    # Check for duplicate
    existing = await db.execute(
        select(models.FavouriteRecipe).where(
            models.FavouriteRecipe.user_id == current_user.id,
            models.FavouriteRecipe.recipe_id == payload.recipe_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recipe already in favourites.",
        )
    fav = models.FavouriteRecipe(
        user_id=current_user.id,
        recipe_id=payload.recipe_id,
        recipe_title=payload.recipe_title,
        recipe_image=payload.recipe_image,
    )
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


@router.delete(
    "/favourites/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a recipe from favourites",
)
async def remove_favourite(
    recipe_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        delete(models.FavouriteRecipe).where(
            models.FavouriteRecipe.user_id == current_user.id,
            models.FavouriteRecipe.recipe_id == recipe_id,
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favourite not found.",
        )
