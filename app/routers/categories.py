from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.database.db_depends import get_async_db


router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    )


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех категорий товаров.
    """
    stmt = select(CategoryModel).where(CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    categories = result.all()
    return categories
    

@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новую категорию.
    """
    if category.parent_id is not None:
        stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                           CategoryModel.is_active == True)
        result = await db.scalars(stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")
    
    db_categry = CategoryModel(**category.model_dump())
    db.add(db_categry)
    await db.commit()
    await db.refresh(db_categry)
    return db_categry


@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(category_id: int, category_update: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет категорию по её ID.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == category_id,
                                       CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    db_category = result.first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category_update.parent_id is not None:
        parent_stmt = select(CategoryModel).where(CategoryModel.id == category_update.parent_id,
                                           CategoryModel.is_active == True)
        result = await db.scalars(parent_stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")
        if parent.id == category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category cannot be its own parent")
    
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**category_update.model_dump(exclude_unset=True))
    )
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Удаляет категорию по её ID.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == category_id)
    result = await db.scalars(stmt)
    category = result.first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    elif not category.is_active:
        raise HTTPException(status_code=400, detail="Category already marked as inactive")
    
    await db.execute(update(CategoryModel).where(CategoryModel.id == category_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Category marked as inactive"}