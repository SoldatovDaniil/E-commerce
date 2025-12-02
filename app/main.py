from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import categories, products, users, reviews, cart, orders
from app.middleware.log import log_middleware

app = FastAPI(
    title="FastAPI Интернет-магазин"
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.middleware("http")(log_middleware)

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(reviews.product_reviews_router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}
