"""Serve the narrated Mara editorial preview, with its own unlisted token."""
from app_voice import app,Path,secrets,HTTPException,FileResponse
from fastapi.responses import HTMLResponse
@app.api_route("/private-mara-dora/{token}/{filename}",methods=["GET","HEAD"],include_in_schema=False)
def private_mara_dora(token:str,filename:str,inline:bool=False):
 root=Path("/app/examples")
 key=root/"mara-dora.token"
 if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):raise HTTPException(404,"Preview not found.")
 if filename=="watch":
  return HTMLResponse("""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mara Ghodoy | Documental</title><style>body{background:#101010;color:white;font:16px system-ui;margin:24px;text-align:center}video{width:min(100%,360px);max-height:70vh;background:black}a{color:white;display:block;margin:18px}</style><h1>MARA GHODOY · NUEVA LOCUCIÓN</h1><video controls playsinline preload="metadata" src="video.mp4?inline=true"></video><a href="narration.wav" download>Descargar nueva locución</a><a href="video.mp4" download>Descargar MP4</a><a href="delivery.zip" download>Descargar ZIP</a></html>""",headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow","Referrer-Policy":"no-referrer"})
 names={"video.mp4":("mara-dora.mp4","video/mp4","MARA_GHODOY_Documental_Dora.mp4"),"narration.wav":("mara-dora.wav","audio/wav","MARA_GHODOY_Locucion_ES.wav"),"delivery.zip":("mara-dora.zip","application/zip","MARA_GHODOY_Documental_Dora_Pack.zip")}
 if filename not in names:raise HTTPException(404,"Preview not found.")
 name,mime,download=names[filename];p=root/name
 if not p.is_file():raise HTTPException(404,"Preview not found.")
 return FileResponse(p,media_type=mime,filename=download,content_disposition_type="inline" if inline and filename in ("video.mp4","narration.wav") else "attachment",headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow"})
