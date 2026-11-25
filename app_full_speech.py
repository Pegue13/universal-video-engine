from app_audition import app,Path,secrets,HTTPException,FileResponse,HTMLResponse
@app.api_route("/private-full-speech/{token}/{filename}",methods=["GET","HEAD"],include_in_schema=False)
def full_speech(token:str,filename:str,download:bool=False):
 root=Path("/app/examples");key=root/"mara-full-speech.token"
 if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):raise HTTPException(404)
 headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow","Referrer-Policy":"no-referrer"}
 if filename=="listen":
  return HTMLResponse('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mara Ghodoy — Locución completa</title><style>body{font:18px system-ui;color:white;background:#141414;margin:24px}audio{width:min(100%,480px)}a{color:white}</style><h1>Mara Ghodoy — Locución completa</h1><audio controls preload="metadata" src="speech.mp3"></audio><p><a href="speech.mp3?download=true" download>Descargar MP3</a></p><p><a href="speech.wav?download=true" download>Descargar WAV</a></p></html>',headers=headers)
 files={"speech.mp3":("mara-full-speech.mp3","audio/mpeg","Mara_Ghodoy_Locucion_Completa.mp3"),"speech.wav":("mara-full-speech.wav","audio/wav","Mara_Ghodoy_Locucion_Completa.wav"),"timing.json":("mara-full-speech.json","application/json","Mara_Ghodoy_Locucion_Tiempos.json")}
 if filename not in files:raise HTTPException(404)
 name,mime,out=files[filename];p=root/name
 if not p.is_file():raise HTTPException(404)
 return FileResponse(p,media_type=mime,filename=out,content_disposition_type="attachment" if download else "inline",headers=headers)
