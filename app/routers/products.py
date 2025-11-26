from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.database.db_depends import get_async_db
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.auth import get_current_seller
from app.database.db_services import check_category_id, check_product_id


router = APIRouter(
    prefix="/products",
    tags=["products"],
    )


@router.get("/", response_model=ProductList)
async def get_all_products(page: int = Query(1, ge=1),
                           page_size: int = Query(20, ge=1, le=100),
                           category_id: int | None = Query(None, description="ID категории для фильтрации"),
                           min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
                           max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
                           in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
                           seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
                           db: AsyncSession = Depends(get_async_db)
                           ):
    """
    Возвращает список всех активных товаров(С пагинацией и фильтрацией).
    """
    total = await db.scalar(select(func.count(ProductModel.id)).where(ProductModel.is_active == True)) or 0
    product_stmt = (
        select(ProductModel)
        .where(ProductModel.is_active == True)
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        )
    products_db = (await db.scalars(product_stmt)).all()
    return {
        "items": products_db,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    

@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, 
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)
                         ):
    """
    Создаёт новый товар текущего продавца(роль: 'seller').
    """
    await check_category_id(product.category_id, db)

    product_db = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(product_db)
    await db.commit()
    await db.refresh(product_db) 
    return product_db


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    await check_category_id(category_id, db)

    stmt = select(ProductModel).where(ProductModel.category_id == category_id, 
                                      ProductModel.is_active == True)
    result = await db.scalars(stmt)
    products_in_category_db = result.all()
    return products_in_category_db


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product_db : ProductModel = await check_product_id(product_id, db) 
    await check_category_id(product_db.category_id, db)
    return product_db


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product_update: ProductCreate, 
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)
                         ):
    """
    Обновляет товар текущего продавца по его ID(роль: 'seller').
    """
    product_db = await check_product_id(product_id, db)
    if product_db.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
    await check_category_id(product_update.category_id, db)

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_update.model_dump())
    )
    await db.commit()
    await db.refresh(product_db)
    return product_db


@router.delete("/{product_id}")
async def delete_product(product_id: int, 
                         db : AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)
                         ):
    """
    Удаляет товар текущего продавца по его ID(роль: 'seller').
    """
    product_db: ProductModel = await check_product_id(product_id, db)
    if product_db.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
    product_db.is_active = False
    await db.commit()
    await db.refresh(product_db)
    return product_db

