"""Henners: private text-only documentary, using identified artist press clips."""
import json, os, pathlib, tempfile, shutil, secrets, zipfile
from PIL import Image, ImageDraw, ImageFont
import engine,media_import
W,H,FPS=540,960,25
ROOT=pathlib.Path("/app/examples")
BASE="https://www.dj.henners.bio/downloads/videos/"
ASSETS={
 "land":("lundjuweel-2025.mp4","Landjuweel 2025"),
 "basement":("edfh%20basement.mp4","Archivo · EDFH Basement"),
 "sieraad":("ambrosia-het-sieraad.mp4","Ambrosia · Het Sieraad"),
 "museum":("ambrosia-rijksmuseum.mp4","Ambrosia · Rijksmuseum"),
 "nye":("new%20years%20eve.mp4","Archivo · Nochevieja"),
 "nye2":("new%20years%20evee.mp4","Archivo · Nochevieja"),
 "this":("this%20is%20what%20we%20do.mp4","Archivo de actuaciones")
}
# Each card holds a short consecutive portion of the agreed narrative.
CARDS=[
 ("land",0,"01 / DESCUBRIMIENTO","¿Y si una sesión de DJ pudiera contar una historia sin palabras?",5.0),
 ("sieraad",0,"HENNERS","Un artista afincado en Ámsterdam, dentro del movimiento ecstatic dance.",5.2),
 ("this",0,"ECSTATIC DANCE","Música y baile libre como formas de expresión colectiva.",4.8),
 ("basement",0,"2021 / PRIMERAS ACTUACIONES","Su archivo documenta actuaciones desde 2021.",5.0),
 ("nye",0,"ODESSA / ÁMSTERDAM","Odessa, un barco convertido en punto de encuentro musical, es clave en su evolución.",6.2),
 ("nye2",0,"UNA COMUNIDAD","Allí acumula más de cien sesiones, según su archivo artístico.",5.2),
 ("land",5,"IDENTIDAD MUSICAL","No construye sus sets alrededor de un único género.",5.0),
 ("this",4,"RITMOS GLOBALES","Combina percusiones, ritmos de distintas culturas y sonidos electrónicos.",5.6),
 ("basement",5,"EL VIAJE","Su forma de organizar cada sesión se inspira en los cinco ritmos y el viaje del héroe.",6.7),
 ("sieraad",2,"01 / MOVIMIENTO","Comienza con sonidos que invitan al movimiento.",4.8),
 ("nye",5,"02 / INTENSIDAD","Aumenta progresivamente la energía.",4.4),
 ("nye2",5,"03 / CALMA","Y termina llevando al público hacia la calma.",4.6),
 ("this",8,"2024–2025 / EXPANSIÓN","Su propuesta cruzó las fronteras de los Países Bajos.",5.3),
 ("basement",2,"ESCENA INTERNACIONAL","Su recorrido incluye actuaciones en Hawái y Tailandia.",5.0),
 ("land",9,"LANDJUWEEL / RUIGOORD","También ha formado parte del festival Landjuweel.",5.3),
 ("sieraad",0,"AMBROSIA ECSTATIC RAVE","Llevó su concepto a espacios como Het Sieraad.",5.2),
 ("museum",0,"RIJKSMUSEUM","Su archivo audiovisual incluye una actuación de Ambrosia en el Rijksmuseum.",5.7),
 ("land",2,"2026 / CONTINUIDAD","Su agenda recoge nuevas actuaciones de Ecstatic Dance Festival Holland.",5.7),
 ("this",2,"MÁS DE 130 ACTUACIONES","Una trayectoria que propone otra manera de entender la figura del DJ.",5.7),
 ("museum",4,"EXPERIENCIA COLECTIVA","No solo como selector musical, sino como conductor de una experiencia compartida.",6.0),
 ("land",7,"HENNERS","Para algunos artistas, la pista de baile también es un lugar de transformación.",6.0)
]
def log(status,**kwargs):
 print("HENNERS_DOC "+json.dumps({"status":status,**kwargs},ensure_ascii=True),flush=True)
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
 d.text((32,25),"PERFIL ARTÍSTICO",font=font(17,True),fill="#D8B987")
 d.text((32,55),label,font=font(18),fill="#F4F4F4")
 d.rectangle((0,615,W,H),fill=(12,12,12,229))
 d.rectangle((32,641,79,644),fill="#D8B987")
 hf=font(23,True)
 for i,l in enumerate(wrap(d,heading,hf,W-64)):
  d.text((32,659+i*28),l,font=hf,fill="#D8B987")
 bf=font(31,True);lines=wrap(d,body,bf,W-64)
 if len(lines)>5:bf=font(27,True);lines=wrap(d,body,bf,W-64)
 if len(lines)>5:raise ValueError("Text overflow")
 y=710
 for l in lines:
  d.text((32,y),l,font=bf,fill="#FFFFFF");y+=39
 d.rectangle((32,926,W-32,930),fill=(95,95,95,255))
 d.rectangle((32,926,32+int((W-64)*(index+1)/len(CARDS)),930),fill="#D8B987")
 im.save(path)
def main():
 ROOT.mkdir(exist_ok=True)
 os.environ["MEDIA_ALLOWED_HOSTS"]="www.dj.henners.bio,dj.henners.bio,www.henners.bio,henners.bio"
 with tempfile.TemporaryDirectory(prefix="henners-doc-") as temp:
  work=pathlib.Path(temp);sources={}
  for k,(url,label) in ASSETS.items():
   p=work/(k+".mp4")
   try:
    info=media_import.fetch(BASE+url,p)
    sources[k]={"path":p,"url":BASE+url,"label":label,"duration":info["duration"],"size":info["size"],"sha256":engine.digest(p)}
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
  final=work/"HENNERS_Documental_Textos.mp4"
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
  credits={"artist":"Henners","press_kit":"https://www.dj.henners.bio/media-package","event_archive":"https://www.dj.henners.bio/events","use":"Private editorial review; confirm permission before public use.","sources":[{k:v for k,v in s.items() if k!="path"} for s in sources.values()],"note":"Archive labels identify source footage, not necessarily the event mentioned in the narrative. No original audio or voice."}
  (work/"Creditos.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
  sheet=Image.new("RGB",(6*135,4*240),(20,20,20))
  for i,c in enumerate(timeline):
   frame=work/f"frame{i}.jpg";engine.frame_at(final,c["start"]+0.5,frame)
   with Image.open(frame) as im:sheet.paste(im.resize((135,240)),((i%6)*135,(i//6)*240))
  sheet.save(work/"Contacto.jpg",quality=90)
  qa={"passed":True,"duration":info["duration"],"width":W,"height":H,"fps":FPS,"codec":v["codec_name"],"audio":False,"bytes":info["size"],"sha256":engine.digest(final),"source_count":len(sources),"cards":len(timeline),"full_decode":True,"visual_review_required":True}
  (work/"QA.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
  bundle=work/"HENNERS_Documental_Pack.zip"
  with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
   for p in [final]+[work/n for n in ("Guion.txt","Subtitulos.srt","Montaje.json","Creditos.json","Contacto.jpg","QA.json")]:z.write(p,p.name)
  with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
  token=secrets.token_urlsafe(24)
  shutil.copyfile(final,ROOT/"henners-doc.mp4");shutil.copyfile(bundle,ROOT/"henners-doc.zip")
  shutil.copyfile(work/"Contacto.jpg",ROOT/"henners-doc-contact.jpg")
  (ROOT/"henners-doc.token").write_text(token)
  log("verified",qa=qa,zip_bytes=bundle.stat().st_size,path="/private-documentary/"+token+"/video.mp4",zip_path="/private-documentary/"+token+"/delivery.zip",contact_path="/private-documentary/"+token+"/contact.jpg")
if __name__=="__main__":
 try:main()
 except Exception as e:log("failed",reason=str(e)[:500])
