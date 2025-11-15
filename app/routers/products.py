from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.products import Product as ProductModel, Category as CategoryModel
from app.db_depends import get_db
from app.schemas import Product as ProductSchema, ProductCreate


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/")
async def get_all_products():
    """
    Возвращает список всех товаров.
    """
    return {"message": "Список всех товаров (заглушка)"}


@router.post("/products/", response_model=ProductSchema)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Создаёт новый товар.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id)
    category_db = db.scalars(stmt).first()
    if category_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product_db = ProductModel(**product.model_dump())
    db.add(product_db)
    db.commit()
    db.refresh(product_db) 
    return product_db


@router.get("/category/{category_id}")
async def get_products_by_category(category_id: int):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    return {"message": f"Товары в категории {category_id} (заглушка)"}


@router.get("/{product_id}")
async def get_product(product_id: int):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    return {"message": f"Детали товара {product_id} (заглушка)"}


@router.put("/{product_id}")
async def update_product(product_id: int):
    """
    Обновляет товар по его ID.
    """
    return {"message": f"Товар {product_id} обновлён (заглушка)"}


@router.delete("/{product_id}")
async def delete_product(product_id: int):
    """
    Удаляет товар по его ID.
    """
    return {"message": f"Товар {product_id} удалён (заглушка)"}

