from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel


async def check_category_id(category_id: int, db: AsyncSession) -> CategoryModel:
    stmt = select(CategoryModel).where(CategoryModel.id == category_id, 
                                       CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    category_db = result.first()
    if category_db is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")
    return category_db


async def check_product_id(product_id: int, db: AsyncSession) -> ProductModel:
    stmt = select(ProductModel).where(ProductModel.id == product_id, 
                                      ProductModel.is_active == True)
    result = await db.scalars(stmt)
    product_db = result.first()
    if product_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product_db


async def update_product_grade(product_id: int, db: AsyncSession):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product_db = await db.get(ProductModel, product_id)
    product_db.raiting = avg_rating
    await db.commit()


async def check_review_id(review_id: int, db: AsyncSession) -> ReviewModel:
    stmt = select(ReviewModel).where(ReviewModel.id == review_id,
                                     ReviewModel.is_active == True,
                                     ReviewModel.product.has(ProductModel.is_active == True))
    review_db = await db.scalar(stmt)
    if review_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review_db