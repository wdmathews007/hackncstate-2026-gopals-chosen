from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  

try:
    from .spread.router import router as spread_router
    from .upload.router import router as upload_router
except ImportError:
    from spread.router import router as spread_router
    from upload.router import router as upload_router


app = FastAPI(
    title="Smoke and Mirrors",
    description="Who looks at these",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(upload_router)
app.include_router(spread_router)

@app.get("/")
async def heath():
    return{"status":"ok i guess"}
