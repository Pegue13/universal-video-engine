"""Serve the narrated Mara editorial preview, with its own unlisted token."""
from app_mara import app,Path,secrets,HTTPException,FileResponse
@app.get("/private-mara-voice/{token}/{filename}",include_in_schema=False)
def private_mara_voice(token:str,filename:str):
 root=Path("/app/examples")
 key=root/"mara-voice.token"
 if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):raise HTTPException(404,"Preview not found.")
 names={"video.mp4":("mara-voice.mp4","video/mp4","MARA_GHODOY_Documental_Voz.mp4"),"narration.wav":("mara-voice.wav","audio/wav","MARA_GHODOY_Locucion_ES.wav"),"delivery.zip":("mara-voice.zip","application/zip","MARA_GHODOY_Documental_Voz_Pack.zip")}
 if filename not in names:raise HTTPException(404,"Preview not found.")
 name,mime,download=names[filename];p=root/name
 if not p.is_file():raise HTTPException(404,"Preview not found.")
 return FileResponse(p,media_type=mime,filename=download,headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow"})
