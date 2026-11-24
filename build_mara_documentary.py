"""Mara Ghodoy editorial preview from original downloadable artist press footage."""
import json, os, pathlib, tempfile, shutil, secrets, zipfile
from PIL import Image, ImageDraw, ImageFont
import engine,media_import
import urllib.request, urllib.parse, time, socket, ipaddress
W,H,FPS=540,960,25
ROOT=pathlib.Path("/app/examples")
BASE="https://drive.google.com/file/d/"
ASSETS={
 "bass":("1-17QluZ0QHol1wRPcbUbsRfgYdiJBqg1","Basshaus · Barcelona",26639163),
 "cosmos":("1kIs0ow6jtTZ7wUit4DDQ7IWwrAkjzUua","Cosmos · No Sleep",28898652),
 "pandora":("1c_cjhWZW90qkM9DAwt2pi-b3xljSyJXv","Pandora · Sevilla",19463967),
 "matadero":("1RdppRslPXaMTvaFQhrF9cNhR-ypz56uR","Matadero · Murcia",34624295),
 "bass2":("1XEBaKeKjEx0mrWxw63DGXyymS5W62Sl2","Basshaus · Archivo",43346908),
 "pandora2":("1Lo4vU4-29fEihqE5iShJcfOPlCnZxUe7","Pandora · Archivo",40875632)
}
CARDS=[
 ("cosmos",0,"MARA GHODOY","De los instrumentos a las cabinas del techno underground.",5.0),
 ("bass",0,"MÉRIDA / ORÍGENES","Su recorrido musical comienza como instrumentista en Mérida, Extremadura.",5.8),
 ("pandora",0,"2021 / EL SALTO A LA CABINA","En 2021 empieza a actuar como DJ dentro del movimiento rave.",5.5),
 ("bass2",2,"DE LA RAVE AL CLUB","Con el tiempo evoluciona hacia un sonido de club más personal.",5.5),
 ("cosmos",5,"SU IDENTIDAD","Hardgroove e hypnotic techno son hoy los ejes de su propuesta.",5.7),
 ("pandora2",4,"RITMO Y TENSIÓN","Percusión, mezclas precisas y tensión progresiva mantienen el movimiento de la pista.",6.5),
 ("bass",7,"2024 / ETIKA","Junto a Fhiga impulsa ETIKA, una plataforma para visibilizar el talento femenino en la electrónica.",7.0),
 ("matadero",0,"HÉKATE / MÁLAGA","El ciclo Hékate se presenta en Sala Marte, con una programación centrada en DJs mujeres.",6.8),
 ("bass2",9,"2025 / CIRCUITO CLUB","Su trayectoria se amplía con actuaciones en salas como Basshaus, Paris15 y Pandora.",6.8),
 ("pandora",6,"RASTRO LIVE","En julio de 2025 publica una sesión con Rastro Live que explora el techno hipnótico, el hardgroove y el raw.",7.6),
 ("cosmos",10,"SEVILLA / RESIDENCIA","Se establece en la escena sevillana como residente de Cosmos Club y artista de Oscura Techno.",7.0),
 ("matadero",8,"2026 / ELECTROLUNCH","En marzo figura en la programación de Electrolunch XXL, en el Parque Magallanes de Sevilla.",6.8),
 ("pandora2",10,"8 MAYO / PANDORA","Comparte cartel con 999999999 y Bárbara Lago en Rebels.",5.8),
 ("pandora",12,"4 JULIO / HYPERLINK","Vuelve a Pandora en una noche encabezada por Fantasm.",5.5),
 ("matadero",15,"12 SEPTIEMBRE / MURCIA","Actúa en Matadero, en un cartel con Luciid, Armero y Fhiga, entre otros.",6.3),
 ("bass2",15,"19 SEPTIEMBRE / MÁLAGA","Participa en la apertura de temporada de Orion en Paris15, con Fhiga.",6.2),
 ("cosmos",16,"2 OCTUBRE / HELION","Su agenda recoge una noche de Helion en Cosmos Club con Grace Dahl.",6.2),
 ("bass",12,"MÁS ALLÁ DE ESPAÑA","Su dossier también recoge una actuación en Los Ángeles, Estados Unidos.",5.8),
 ("pandora2",17,"NUEVA ETAPA","En paralelo a las cabinas, trabaja en sus primeras producciones musicales.",5.8),
 ("cosmos",22,"MARA GHODOY","Una artista que construye su identidad desde el ritmo, la cultura de club y la evolución constante.",7.0)
]
def log(status,**kwargs):
 print("MARA_DOC "+json.dumps({"status":status,**kwargs},ensure_ascii=True),flush=True)
def font(size,bold=False):
 return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans"+("-Bold" if bold else "")+".ttf",size)
def wrap(draw,text,f,limit):
 lines=[];line=""
 for word in text.split():
  test=(line+" "+word).strip()
  if draw.textlength(test,font=f)>limit and line:
   lines.append(line);line=word
  else:line=test
 if line:lines.append(line)
 return lines
def overlay(path,index,heading,body,label):
 im=Image.new("RGBA",(W,H));d=ImageDraw.Draw(im)
 # Dark overlays are confined to the safe title and caption areas.
 d.rectangle((0,0,W,108),fill=(12,12,12,211))
 d.text((32,25),"MARA GHODOY / PERFIL ARTÍSTICO",font=font(17,True),fill="#D8B987")
 d.text((32,55),label,font=font(18),fill="#F4F4F4")
 d.rectangle((0,615,W,H),fill=(12,12,12,229))
 d.rectangle((32,641,79,644),fill="#D8B987")
 hf=font(21,True)
 for i,l in enumerate(wrap(d,heading,hf,W-64)):
  d.text((32,659+i*28),l,font=hf,fill="#D8B987")
 bf=font(31,True);lines=wrap(d,body,bf,W-64)
 if len(lines)>5:bf=font(27,True);lines=wrap(d,body,bf,W-64)
 if len(lines)>5:raise ValueError("Text overflow")
 y=716
 for l in lines:
  d.text((32,y),l,font=bf,fill="#FFFFFF");y+=39
 d.rectangle((32,926,W-32,930),fill=(95,95,95,255))
 d.rectangle((32,926,32+int((W-64)*(index+1)/len(CARDS)),930),fill="#D8B987")
 im.save(path)
def download(id,path,expected):
 # Fixed public press-kit IDs. No account cookies or authentication bypass.
 url="https://drive.usercontent.google.com/download?id="+id+"&export=download&confirm=t"
 deadline=time.monotonic()+90
 for step in range(5):
  p=urllib.parse.urlsplit(url)
  host=p.hostname or ""
  if p.scheme!="https" or p.port not in (None,443) or p.username or p.password or not (host in ("drive.google.com","drive.usercontent.google.com") or host.endswith(".googleusercontent.com")):
   raise ValueError("Unexpected download host")
  ip=media_import.public_address(host)
  conn=media_import.PinnedHTTPS(host,ip,25)
  try:
   conn.request("GET",p.path+("?" + p.query if p.query else ""),headers={"User-Agent":"UniversalVideoEngine/0.2 editorial preview","Accept":"video/*,application/octet-stream","Accept-Encoding":"identity"})
   r=conn.getresponse()
   if r.status in (301,302,303,307,308):
    url=urllib.parse.urljoin(url,r.getheader("Location",""));continue
   if r.status!=200:raise ValueError("Drive HTTP "+str(r.status))
   mime=(r.getheader("Content-Type") or "").split(";")[0].lower()
   if not (mime.startswith("video/") or mime in ("application/octet-stream","application/mp4","application/quicktime")):
    raise ValueError("Drive returned non-video: "+mime)
   total=0
   with open(path,"wb") as out:
    while True:
     if time.monotonic()>deadline:raise ValueError("Download timeout")
     b=r.read(1024*1024)
     if not b:break
     total+=len(b)
     if total>expected:raise ValueError("File exceeds recorded size")
     out.write(b)
   if total!=expected:raise ValueError("Source size mismatch")
   return engine.probe(path)
  finally:conn.close()
 raise ValueError("Too many redirects")

def main():
 ROOT.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="mara-doc-") as temp:
  work=pathlib.Path(temp);sources={}
  for k,(id,label,expected) in ASSETS.items():
   p=work/(k+".mp4")
   try:
    info=download(id,p,expected)
    sources[k]={"path":p,"url":BASE+id+"/view","label":label,"duration":info["duration"],"size":info["size"],"sha256":engine.digest(p)}
    log("source_verified",key=k,seconds=info["duration"],bytes=info["size"])
   except Exception as e:log("source_failed",key=k,reason=str(e)[:180])
  if len(sources)<3:raise RuntimeError("Not enough authentic footage")
  parts=[];timeline=[];elapsed=0
  for i,(key,start,head,body,seconds) in enumerate(CARDS):
   actual=key if key in sources else next(iter(sources))
   src=sources[actual]
   duration=round(seconds*FPS)/FPS
   # Never label fallback footage as the planned event.
   start=min(start,max(0,src["duration"]-duration-0.12))
   img=work/f"overlay{i:02d}.png";overlay(img,i,head,body,src["label"])
   part=work/f"part{i:02d}.mp4"
   # Fit original shot into upper area, blurred fill behind it, text remains independent.
   graph=("[0:v]fps=25,setsar=1,split=2[bg][fg];"
          "[bg]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,boxblur=12:2[blur];"
          "[fg]scale=540:600:force_original_aspect_ratio=decrease:force_divisible_by=2[fit];"
          "[blur][fit]overlay=(W-w)/2:108+(507-h)/2[base];"
          "[base][1:v]overlay=0:0:repeatlast=1,tpad=stop_mode=clone:stop_duration=10[v]")
   engine.ff(["-ss",str(start)]+engine.source_args(src["path"])+["-i",str(img),"-filter_complex",graph,"-map","[v]","-t",str(duration),"-an","-sn","-dn"]+engine.encode_flags()+["-threads","1","-movflags","+faststart",str(part)],120)
   info=engine.probe(part)
   if abs(info["duration"]-duration)>.16:raise RuntimeError("Segment duration mismatch")
   parts.append(part);timeline.append({"start":elapsed,"end":round(elapsed+duration,3),"chapter":head,"text":body,"footage":src["label"],"source":src["url"],"source_start":start,"source_duration":src["duration"]})
   elapsed=round(elapsed+duration,3)
   log("card",number=i+1,total=len(CARDS),seconds=elapsed)
  concat=work/"concat.txt";concat.write_text("".join("file '"+p.name+"'\n" for p in parts))
  final=work/"MARA_GHODOY_Documental_Textos.mp4"
  engine.ff(["-f","concat","-safe","1","-protocol_whitelist","file,pipe","-i",str(concat),"-c:v","copy","-an","-movflags","+faststart",str(final)],120)
  info=engine.probe(final);v=info["video"]
  assert v["width"]==W and v["height"]==H and v["codec_name"]=="h264" and not info["audio"] and abs(info["duration"]-elapsed)<.5
  # Full decode catches damaged streams after concatenation.
  engine.ff(engine.source_args(final)+["-map","0:v:0","-f","null","-"],120)
  def ts(s):
   ms=round(s*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
   return f"{h:02}:{m:02}:{sec:02},{ms:03}"
  (work/"Guion.txt").write_text("\n\n".join(c["text"] for c in timeline),encoding="utf-8")
  (work/"Subtitulos.srt").write_text("\n\n".join(f"{i+1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}" for i,c in enumerate(timeline))+"\n",encoding="utf-8")
  (work/"Montaje.json").write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding="utf-8")
  credits={"artist":"Mara Ghodoy","press_kit":"https://www.maraghodoy.com/","press_videos":"https://drive.google.com/drive/folders/1DVhzB5YnAPdW2DC6T1v_alM4aATC--B0","research_sources":["https://www.maraghodoy.com/","https://ra.co/dj/maraghodoy","https://beatandmix.com/etika-una-promotora-que-impulsa-el-talento-femenino-en-la-escena-electronica/","https://www.youtube.com/watch?v=MSB1qcutY_M","https://cesevillatechpark.com/la-vigesimoprimera-edicion-de-electrolunch-xxl-se-celebrara-el-sabado-7-de-marzo-en-el-parque-magallanes/"],"use":"Private editorial review; confirm permission before public use.","sources":[{k:v for k,v in s.items() if k!="path"} for s in sources.values()],"note":"Archive labels identify source footage, not necessarily the event mentioned in the narrative. No original audio or voice."}
  (work/"Creditos.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
  sheet=Image.new("RGB",(6*135,4*240),(20,20,20))
  for i,c in enumerate(timeline):
   frame=work/f"frame{i}.jpg";engine.frame_at(final,c["start"]+0.5,frame)
   with Image.open(frame) as im:sheet.paste(im.resize((135,240)),((i%6)*135,(i//6)*240))
  sheet.save(work/"Contacto.jpg",quality=90)
  qa={"passed":True,"duration":info["duration"],"width":W,"height":H,"fps":FPS,"codec":v["codec_name"],"audio":False,"bytes":info["size"],"sha256":engine.digest(final),"source_count":len(sources),"cards":len(timeline),"full_decode":True,"visual_review_required":True}
  (work/"QA.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
  bundle=work/"MARA_GHODOY_Documental_Pack.zip"
  with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
   for p in [final]+[work/n for n in ("Guion.txt","Subtitulos.srt","Montaje.json","Creditos.json","Contacto.jpg","QA.json")]:z.write(p,p.name)
  with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
  token=secrets.token_urlsafe(24)
  shutil.copyfile(final,ROOT/"mara-doc.mp4");shutil.copyfile(bundle,ROOT/"mara-doc.zip")
  shutil.copyfile(work/"Contacto.jpg",ROOT/"mara-doc-contact.jpg")
  (ROOT/"mara-doc.token").write_text(token)
  log("verified",qa=qa,zip_bytes=bundle.stat().st_size,path="/private-mara/"+token+"/video.mp4",zip_path="/private-mara/"+token+"/delivery.zip",contact_path="/private-mara/"+token+"/contact.jpg")
if __name__=="__main__":
 try:main()
 except Exception as e:log("failed",reason=str(e)[:500])
