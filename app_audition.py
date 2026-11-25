from app_dora import app,Path,secrets,HTTPException,FileResponse,HTMLResponse
@app.api_route("/private-audition/{token}/{filename}",methods=["GET","HEAD"],include_in_schema=False)
def audition(token:str,filename:str,download:bool=False):
 root=Path("/app/examples");key=root/"audition.token"
 if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):raise HTTPException(404)
 headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow","Referrer-Policy":"no-referrer"}
 names={"elvira.mp3":"Elvira","abril.mp3":"Abril"}
 if filename=="listen":
  html='<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prueba de voz</title><style>body{font:18px system-ui;color:white;background:#141414;margin:24px}audio{width:min(100%,480px)}a{color:white}</style><h1>Mara Ghodoy — prueba de voz</h1>'
  for n,label in names.items():
   if (root/("audition-"+n)).is_file():html+=f'<h2>{label}</h2><audio controls preload="metadata" src="{n}"></audio><p><a href="{n}?download=true" download>Descargar MP3</a></p>'
  return HTMLResponse(html+"</html>",headers=headers)
 if filename not in names:raise HTTPException(404)
 p=root/("audition-"+filename)
 if not p.is_file():raise HTTPException(404)
 return FileResponse(p,media_type="audio/mpeg",filename=filename,content_disposition_type="attachment" if download else "inline",headers=headers)
