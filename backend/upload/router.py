from fastapi import APIRouter, UploadFile, File, HTTPException, FastAPI
import uuid, os, string
from pathlib import Path

app = FastAPI()
router = APIRouter()

UPLOAD_DIR = Path(str(Path(__file__).parent.parent)+"/upload/pictures").mkdir(parents=True,exist_ok=True)
#os.mkdir(UPLOAD_DIR,parents=True,exist_ok=True)

@app.post("/upload/")
async def upload_file(UF:UploadFile):
    #UF=File(...)
    if(UF.content_type.startswith("image/") == True):
    
        raise HTTPException("File not image type")
    
    
    file = open(UF.filename, "r")
    filename= f"{uuid.uuid4().hex}_{file.filename}"
    content = await file.read()
    with open(Path(str(UPLOAD_DIR) + filename), "w") as f:
        f.write(content)

    return {"filename":filename,"status":"uploaded","analysis":{"label":"unknown","confidence":0.0,"metadata": {},"heatmap_url":None}}

@app.post("/")
async def test():
    print("I guess this works")
    return("working")
