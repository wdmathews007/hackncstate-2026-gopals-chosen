from fastapi import APIRouter, UploadFile, File, HTTPException
from stdlib import uuid, os
from pthlib import Path

app = FastAPI()
router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent+"/upload/pictures"
os.mkdir(UPLOAD_DIR,parents=True,exist_ok=True)

@app.post("/upload/")
async def upload_file(UploadFile: UploadFile):
    UploadFile=File(...)
    if(file.content_type.startswith("image/") == True):
    
        raise HTTPException("File not image type")
    
    
    file = open(UploadFile.filename, "r")
    filename= f"{uuid.uuid4().hex}_{file.filename}"
    with open(UPLOAD_DIR + filename, "w") as f:
        f.write(content)
    content = await file.read()
    return {"filename":filename,"status":"uploaded","analysis":{"label":"unknown","confidence":0.0,"metadata": {},"heatmap_url":None}}
