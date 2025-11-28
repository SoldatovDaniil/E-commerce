from fastapi import File, HTTPException, UploadFile, status
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, update, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.database.db_depends import get_async_db
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.auth import get_current_seller
from app.database.db_services import check_category_id, check_product_id
from app.database.media import save_product_image, remove_product_image


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
                           search: str | None = Query(None, description="Поиск по названию товара"),
                           db: AsyncSession = Depends(get_async_db)
                           ):
    """
    Возвращает список всех активных товаров(С пагинацией, фильтрацией и поиком по названию).
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count(ProductModel.id)).where(*filters)

    rank_col = None
    if search:
        search_value = search.strip()
        if search_value:
            ts_query_eng = func.websearch_to_tsquery('english', search_value)
            ts_query_rus = func.websearch_to_tsquery('russian', search_value)
            ts_match_any = or_(
                ProductModel.tsv.op('@@')(ts_query_eng),
                ProductModel.tsv.op('@@')(ts_query_rus),
            )
            filters.append(ts_match_any)

            rank_col = func.greatest(func.ts_rank_cd(ProductModel.tsv, ts_query_eng),
                                     func.ts_rank_cd(ProductModel.tsv, ts_query_rus)
                                     ).label("rank")
            
            total_stmt = select(func.count(ProductModel.id)).where(*filters)

    total = await db.scalar(total_stmt) or 0
    ranks = []
    
    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(products_stmt)).all()
        products_db = [row[0] for row in rows]
        ranks = [row.rank for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        products_db = (await db.scalars(products_stmt)).all()
    
    return {
        "items": products_db,
        "ranks": ranks,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    

@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None), 
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар текущего продавца(роль: 'seller').
    """
    await check_category_id(product.category_id, db)

    image_url = await save_product_image(image) if image else None

    product_db = ProductModel(
        **product.model_dump(),
        seller_id=current_user.id, 
        image_url=image_url
        )
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
async def update_product(
    product_id: int, 
    product_update: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None),
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

    if image is not None:
        remove_product_image(product_db.image_url)
        product_db.image_url = await save_product_image(image)

    await db.commit()
    await db.refresh(product_db)
    return product_db


@router.delete("/{product_id}")
async def delete_product(
    product_id: int, 
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
    remove_product_image(product_db.image_url)
 
    await db.commit()
    await db.refresh(product_db)
    return product_db
