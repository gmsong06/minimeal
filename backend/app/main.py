import os

import uvicorn
from fastapi import FastAPI

from .routers.meals import router as meals_router
from .services.meal_service import initialize_app_data

app = FastAPI(title="Minimeal")


@app.on_event("startup")
def startup_event():
    initialize_app_data()


app.include_router(meals_router)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
