from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from upload.router import router


app = FastAPI(
    title="Smoke and Mirrors",
    description="Who looks at these",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=[""],
    allow_headers=[""],
    allow_credentials=True,
)
app.include_router(router)

@app.get("/")
async def heath():
    return{"status":"ok i guess"}