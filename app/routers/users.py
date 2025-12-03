import jwt
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User as UserModel
from app.schemas import UserCreate, User as UserSchema
from app.database.db_depends import get_async_db
from app.auth import create_refresh_token, hash_password, verify_password, create_access_token
from app.config import get_settings


settings = get_settings()
secret_key = settings.secret_key
algorithm = settings.algorithm

router = APIRouter(
    prefix="/users",
    tags=["users"]
    )


async def check_users_email(email: str, db: AsyncSession) -> None:
    user_db = await db.scalar(select(UserModel).where(UserModel.email == email))
    if user_db:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user_create: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Регистрирует нового пользователя с ролью 'buyer' или 'seller'.
    """
    await check_users_email(user_create.email, db)

    user_new = UserModel(
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        role=user_create.role
        )
    
    db.add(user_new)
    await db.commit()
    await db.refresh(user_new)
    return user_new


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), 
                db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """
    user_db = await db.scalar(select(UserModel).where(UserModel.email == form_data.username, UserModel.is_active == True))
    if not user_db or not verify_password(form_data.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user_db.email, "role": user_db.role, "id": user_db.id})
    refresh_token = create_refresh_token(data={"sub": user_db.email, "role": user_db.role, "id": user_db.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh-token")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет access_token с помощью refresh_token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, secret_key, algorithms=[algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user_db = await db.scalar(select(UserModel).where(UserModel.email == email, UserModel.is_active == True))
    if user_db is None:
        raise credentials_exception
    access_token = create_access_token(data={"sub": user_db.email, "role": user_db.role, "id": user_db.id})
    return {"access_token": access_token, "token_type": "bearer"}