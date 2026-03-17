from fastapi import FastAPI

from .routers.meals import router as meals_router
from .services.meal_service import initialize_app_data

app = FastAPI(title="Minimeal")


@app.on_event("startup")
def startup_event():
    initialize_app_data()


app.include_router(meals_router)
