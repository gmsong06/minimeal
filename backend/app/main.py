import os

import uvicorn
from fastapi import FastAPI

from .routers.auth import router as auth_router
from .routers.meals import router as meals_router
from .services.meal_service import initialize_app_data
from .services.storage import initialize_storage

app = FastAPI(title="Minimeal")


@app.on_event("startup")
def startup_event():
    initialize_app_data()
    initialize_storage()


app.include_router(meals_router)
app.include_router(auth_router)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
