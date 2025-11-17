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


async def check_category_id(category_id: int, db: Session) -> CategoryModel:
    stmt = select(CategoryModel).where(CategoryModel.id == category_id, 
                                       CategoryModel.is_active == True)
    category_db = db.scalars(stmt).first()
    if category_db is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
    return category_db


async def check_product_id(product_id: int, db: Session) -> ProductModel:
    stmt = select(ProductModel).where(ProductModel.id == product_id, 
                                      ProductModel.is_active == True)
    product_db = db.scalars(stmt).first()
    if product_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product_db


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: Session = Depends(get_db)):
    """
    Возвращает список всех активных товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    products_db = db.scalars(stmt).all()
    return products_db

    
@router.post("/products/", response_model=ProductSchema)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Создаёт новый товар.
    """
    check_category_id(product.category_id, db)

    product_db = ProductModel(**product.model_dump())
    db.add(product_db)
    db.commit()
    db.refresh(product_db) 
    return product_db


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: Session = Depends(get_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    check_category_id(category_id, db)

    stmt = select(ProductModel).where(ProductModel.category_id == category_id, 
                                      ProductModel.is_active == True)
    products_in_category_db = db.scalars(stmt).all()
    return products_in_category_db


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product_db : ProductModel = check_product_id(product_id, db) 
    check_category_id(product_db.category_id, db)
    return product_db


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product_update: ProductSchema, db: Session = Depends(get_db)):
    """
    Обновляет товар по его ID.
    """
    product_db = check_product_id(product_id, db)
    check_category_id(product_update.category_id, db)

    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_update.model_dump())
    )
    db.commit()
    db.refresh(product_db)
    return product_db


@router.delete("/{product_id}")
async def delete_product(product_id: int, db : Session = Depends(get_db)):
    """
    Удаляет товар по его ID.
    """
    check_product_id(product_id, db)
    
    db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    db.commit()

    return {"status": "success", "message": "Product marked as inactive"}

