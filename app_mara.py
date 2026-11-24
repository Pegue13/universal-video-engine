"""Register Mara's fixed private editorial preview alongside previous routes."""
from app import app, Path, secrets, HTTPException, FileResponse
@app.get("/private-mara/{token}/{filename}",include_in_schema=False)
def private_mara(token:str,filename:str):
    root=Path("/app/examples")
    key=root/"mara-doc.token"
    if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):
        raise HTTPException(404,"Preview not found.")
    names={"video.mp4":("mara-doc.mp4","video/mp4","MARA_GHODOY_Documental_Textos.mp4"),"delivery.zip":("mara-doc.zip","application/zip","MARA_GHODOY_Documental_Pack.zip"),"contact.jpg":("mara-doc-contact.jpg","image/jpeg","Contacto.jpg")}
    if filename not in names:raise HTTPException(404,"Preview not found.")
    name,mime,download=names[filename]
    p=root/name
    if not p.is_file():raise HTTPException(404,"Preview not found.")
    return FileResponse(p,media_type=mime,filename=download,headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow"})
