from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.db_depends import get_async_db
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.auth import get_current_buyler


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
    )


