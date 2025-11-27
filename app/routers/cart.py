from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database.db_depends import get_async_db
from app.database.db_services import check_product_id, get_cart_item
from app.models.cart_items import CartItem as CartItemModel
from app.models.users import User as UserModel
from app.schemas import (
    Cart as CartSchema,
    CartItem as CartItemSchema,
    CartItemCreate,
    CartItemUpdate,
)


router = APIRouter(
    prefix="/cart",
    tags=["carts"]
)


@router.get("/", response_model=CartSchema)
async def get_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Получение данных о корзине текущего пользователя  
    """
    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id)
    )
    items = result.all()

    total_quantity = 0
    total_price = Decimal(0)
    for item in items:
        total_quantity += item.quantity
        total_price += Decimal(item.quantity) * (item.product.price if item.product.price is not None else Decimal(0))
    
    return CartSchema(
        user_id=current_user.id,
        items=items,
        total_quantity=total_quantity,
        total_price=total_price
    )


@router.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    cart_item_create: CartItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Добавление товара в корзину текущего пользователя
    """
    await check_product_id(cart_item_create.product_id, db)
    cart_item = await get_cart_item(current_user.id, cart_item_create.product_id, db)
    if cart_item is not None:
        cart_item.quantity += cart_item_create.quantity
    else:
        cart_item = CartItemModel(
            user_id=current_user.id,
            product_id = cart_item_create.product_id,
            quantity=cart_item_create.quantity
        )
        db.add(cart_item)

    await db.commit()
    item = await get_cart_item(current_user.id, cart_item_create.product_id, db)
    return item


@router.put("items/{product_id}", response_model=CartItemSchema)
async def update_cart_item(
    product_id: int,
    cart_item_update: CartItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Обновление количества товара в корзину текущего пользователя
    """
    await check_product_id(product_id, db)

    cart_item = await get_cart_item(current_user.id, product_id, db)
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    cart_item.quantity = cart_item_update.quantity
    await db.commit()
    item = await get_cart_item(current_user.id, product_id, db)
    return item


@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Удаление товара из корзины текущего пользователя
    """
    cart_item = await get_cart_item(current_user.id, product_id, db)
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    await db.delete(cart_item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Полная очитска корзины текущего пользователя
    """
    await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

