from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime


class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(min_length=3, max_length=50, description="Название категории (3-50 символов)")
    parent_id: int | None = Field(description="ID родительской категории, если есть")


class Category(BaseModel):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор категории")
    name: str = Field(description="Название категории")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")
    is_active: bool = Field(description="Активность категории")

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name: str = Field(min_length=3, max_length=100,
                      description="Название товара (3-100 символов)")
    description: str | None = Field(None, max_length=500,
                                       description="Описание товара (до 500 символов)")
    price: Decimal = Field(gt=0, description="Цена товара (больше 0)", decimal_places=2)
    image_url: str | None = Field(None, max_length=200, description="URL изображения товара")
    stock: int = Field(ge=0, description="Количество товара на складе (0 или больше)")
    category_id: int = Field(description="ID категории, к которой относится товар")


class Product(BaseModel):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор товара")
    name: str = Field(description="Название товара")
    description: str | None = Field(None, description="Описание товара")
    price: Decimal = Field(description="Цена товара в рублях", gt=0, decimal_places=2)
    image_url: str | None = Field(None, description="URL изображения товара")
    stock: int = Field(description="Количество товара на складе")
    category_id: int = Field(description="ID категории")
    is_active: bool = Field(description="Активность товара")
    seller_id: int = Field(description="ID продавца")

    model_config = ConfigDict(from_attributes=True)
    

class User(BaseModel):
    """
    Модель для ответа с данными пользователя.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор пользователя")
    email: EmailStr = Field(description="Уникальный email пользователя")
    is_active: bool = Field(description="Активность пользователя")
    role: str = Field(description="роль пользователя")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """
    Модель для создания и изменения данных пользователя.
    Используется в POST/PUT-запросах.
    """
    password: str = Field(min_length=4, description="Пароль(минимум 4 символа)")
    email: EmailStr = Field(description="Уникальный email пользователя")
    role: str = Field(default="buyer", pattern="^(buyer|seller)$", description="Роль: 'buyer' или 'seller'")


class Review(BaseModel):
    """
    Модель для ответа с отзовыми о товарах.
    GET-запросы.
    """
    id: int = Field(description="Уникальный идентификатор отзыва")
    user_id: int = Field(description="Уникальный идентификатор пользователя")
    product_id: int = Field(description="Уникальный идентификатор товара")
    comment: str | None = Field(None, max_length=1000,
                                       description="Отзыв (до 1000 символов)")
    comment_date: datetime = Field(description="Дата размещения отзыва(последней редакции)")
    grade: int = Field(ge=1, le=5, description="Оценка товара")

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    """
    Модель для создания отзыва
    POST-запросы.
    """
    product_id: int = Field(description="Уникальный идентификатор товара")
    comment: str | None = Field(None, max_length=1000,
                                       description="Отзыв (до 1000 символов)")
    grade: int = Field(ge=1, le=5, description="Оценка товара")