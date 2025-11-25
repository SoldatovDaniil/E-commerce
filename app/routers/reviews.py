from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.database.db_depends import get_async_db
from app.schemas import Review as ReviewSchema, ReviewCreate, ReviewUpdate
from app.auth import get_current_buyer, get_current_admin
from app.database.db_services import check_product_id, update_product_grade, check_review_id


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
    )

product_reviews_router = APIRouter(
    tags=["reviews"]
    )


@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов об активных товарах.
    """
    stmt = select(ReviewModel).where(ReviewModel.is_active == True,
                                     ReviewModel.product.has(ProductModel.is_active == True))
    result = await db.scalars(stmt)
    reviews_db = result.all()
    return reviews_db


@router.post("/", response_model=ReviewSchema)
async def create_review(review_create: ReviewCreate,
                        db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)
                        ):
    """
    Создаёт новый отзыв о товаре(только "buyler")
    """
    product_db = await check_product_id(review_create.product_id, db)
    new_review = ReviewModel(**review_create.model_dump(), user_id=current_user.id)
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)
    await update_product_grade(product_db.id, db)
    return new_review


@router.put("/{review_id}/", response_model=ReviewSchema)
async def update_review(review_id: int, 
                        review_update: ReviewUpdate,
                        db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)
                        ):
    """
    Обновление отзыва(только "buyler")
    """
    review_db = await check_review_id(review_id, db)
    if review_db.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own reviews")
    await db.execute(
        update(ReviewModel)
        .where(ReviewModel.id == review_id)
        .values(**review_update.model_dump(), comment_date=datetime.now())
    )
    await db.commit()
    await db.refresh(review_db)
    await update_product_grade(review_db.product_id, db)
    return review_db


@router.delete("/{review_id}/")
async def delete_review(review_id: int,
                        db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_admin)
                        ) -> dict:
    """
    Мягкое удаление отзыва(только "admin")
    """
    review_db: ReviewModel = await check_review_id(review_id, db)
    review_db.is_active = False
    await db.commit()
    await update_product_grade(review_db.product_id, db)
    return {"message": "Review deleted"}


@product_reviews_router.get("/products/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов товара.
    """
    await check_product_id(product_id, db)
    stmt = select(ReviewModel).where(ReviewModel.is_active == True,
                                     ReviewModel.product_id == product_id)
    result = await db.scalars(stmt)
    reviews_db = result.all()
    return reviews_db


