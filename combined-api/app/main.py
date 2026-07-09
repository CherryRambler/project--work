from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.areas import router as areas_router
from app.routers.surveys import router as surveys_router

app = FastAPI(title="Combined API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://172.28.8.84:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(areas_router)
app.include_router(surveys_router)


@app.get("/")
async def root():
    return {"status": "ok", "app": "Combined API"}