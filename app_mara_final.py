"""Finish the Mara documentary with the existing seven-block narration.
Never regenerate or change the approved speech's pitch, tempo, or voice."""
import json, pathlib, subprocess, hashlib, zipfile, tempfile, math, wave, array, secrets
ROOT=pathlib.Path("/app/examples")
EXPECTED_SPEECH="c1966ba7c05abb88758a5216b577ddb1c21ec9618a5eb7bb3cea79655518a6c0"
FPS=25
GROUPS=[3,3,2,3,3,3,3]
# Approximate card boundaries are estimated from the actual spoken phrases, then
# snapped to nearby low-energy speech gaps when available; no audio is cut.
PHRASES=[
 ["¿Sabías que Mara Ghodoy empezó haciendo música en Mérida? Pues sí.","Y antes de llegar a las cabinas... ya tocaba instrumentos.","Pero lo interesante viene después: en dos mil veintiuno, descubre el mundo de las raves. Y ahí, empieza a construir su propio sonido."],
 ["Y poco a poco, de la rave al club, encuentra un sonido mucho más personal.","¿Su sonido? Jard gruv y techno hipnótico. Dos pilares de su identidad.","Percusión, mezclas precisas, y tensión progresiva. La pista no para de moverse."],
 ["En dos mil veinticuatro, junto a Figa, impulsa Étika, para visibilizar el talento femenino en la electrónica.","Su ciclo Hékate llega a Sala Marte, en Málaga, con una programación de diyeis mujeres."],
 ["En dos mil veinticinco, su recorrido se amplía por Basshaus, París quince y Pandora.","En julio, Rastro Live publica una sesión suya que explora el techno hipnótico, el jard gruv y el raw.","Se afianza en Sevilla, como residente de Cosmos Club y artista de Oscura Techno."],
 ["En marzo de dos mil veintiséis, figura en Electrolunch, en el Parque Magallanes de Sevilla.","El ocho de mayo, comparte cartel con Nine Times Nine y Bárbara Lago, en Rebels.","Y en julio... vuelve a Pandora, en una noche de Hyperlink encabezada por Fantasm."],
 ["En septiembre, Matadero, Murcia. Un cartel con Luciid, Armero y Figa, entre otros.","Una semana después, apertura de temporada de Orion, en París quince, junto a Figa.","En octubre, su agenda la sitúa en Helion, en Cosmos Club, con Grace Dahl."],
 ["Pero su recorrido no termina en España. Su dossier recoge una actuación en Los Ángeles.","Y mientras sigue recorriendo cabinas, trabaja también en sus primeras producciones.","Mara Ghodoy. Una identidad que se construye entre el ritmo, la cultura de club y la evolución constante."]
]
def log(status,**kw):
 print("MARA_FINAL "+json.dumps(dict(status=status,**kw),ensure_ascii=False),flush=True)
def run(args,timeout=180):
 subprocess.run(["ffmpeg","-hide_banner","-v","error","-nostdin","-y"]+list(map(str,args)),check=True,timeout=timeout)
def digest(p):
 return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):
 return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)],timeout=30))
def rms(samples,start,stop,sr):
 a=max(0,int(start*sr));b=min(len(samples),int(stop*sr))
 if b<=a:return 999999
 return math.sqrt(sum(v*v for v in samples[a:b])/(b-a))
def main():
 wav=ROOT/"mara-full-speech.wav";mp3=ROOT/"mara-full-speech.mp3"
 timing=json.loads((ROOT/"mara-full-speech.json").read_text())
 assert len(timing)==7 and digest(mp3)==EXPECTED_SPEECH,"Existing exact seven-block narration required"
 with wave.open(str(wav)) as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2
  sr=w.getframerate();samples=array.array("h",w.readframes(w.getnframes()))
 speech_len=len(samples)/sr
 assert 99.7<speech_len<100.3
 src=ROOT/"mara-doc.mp4"
 with zipfile.ZipFile(ROOT/"mara-doc.zip") as z:
  timeline=json.loads(z.read("Montaje.json"))
  credits=z.read("Creditos.json")
 assert len(timeline)==20
 assert digest(src)=="d08a076ecd54141470bb4774018b6614a6730b25ce4df238bf5325f79c07f352","Original verified picture required"
 lead=0.80;tail=1.8
 # Group boundaries include the original inter-block conversational pauses.
 cuts=[0.0]; methods=[]; index=0
 for i,(block,phrases) in enumerate(zip(timing,PHRASES)):
  start=float(block["start"]);end=float(block["end"]);span=end-start
  assert len(phrases)==GROUPS[i] and " ".join(phrases)==block["text"]
  weights=[sum(c.isalnum() for c in phrase) for phrase in phrases]
  acc=0
  for j in range(len(phrases)-1):
   acc+=weights[j];est=start+span*acc/sum(weights)
   lo=max(start+1.4,cuts[-1]-lead+1.5,est-0.9);hi=min(end-1.4*(len(phrases)-j-1),est+0.9)
   candidates=[lo+k*0.04 for k in range(max(0,int((hi-lo)/0.04)+1))]
   if candidates:
    best=min(candidates,key=lambda t:rms(samples,t-0.06,t+0.06,sr)+110*abs(t-est))
    if rms(samples,best-0.06,best+0.06,sr)<450:
     target=best;method="nearby low-energy gap"
    else:
     target=est;method="estimated phrase boundary"
   else:target=est;method="estimated phrase boundary"
   cuts.append(round((target+lead)*FPS)/FPS);methods.append(method)
  boundary=(float(timing[i+1]["start"])+end)/2+lead if i<6 else speech_len+lead+tail
  cuts.append(round(boundary*FPS)/FPS);methods.append("block boundary")
 assert len(cuts)==21 and all(b-a>=1.3 for a,b in zip(cuts,cuts[1:]))
 with tempfile.TemporaryDirectory(prefix="mara-final-") as tmp:
  work=pathlib.Path(tmp);parts=[];edit=[]
  for i,card in enumerate(timeline):
   dur=round((cuts[i+1]-cuts[i])*FPS)/FPS
   available=float(card["end"])-float(card["start"])
   # Preserve movement at source speed. Only hold the last frame if a longer
   # card is necessary to let the unmodified narration finish naturally.
   trim_start=float(card["start"])
   trim_len=min(available,dur)
   p=work/("part%02d.mp4"%i)
   graph="trim=duration=%.3f,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=%.3f,fps=25,format=yuv420p"%(trim_len,max(0,dur-trim_len)+0.05)
   run(["-ss",str(trim_start),"-i",src,"-vf",graph,"-t",str(dur),"-an","-c:v","libx264","-preset","veryfast","-crf","18","-threads","2",p])
   parts.append(p)
   edit.append(dict(card,original_start=card["start"],original_end=card["end"],start=cuts[i],end=cuts[i+1],timing_method=methods[i]))
   log("scene",number=i+1,total=20,seconds=dur)
  concat=work/"concat.txt";concat.write_text("".join("file '%s'\n"%p.name for p in parts))
  picture=work/"picture.mp4"
  run(["-f","concat","-safe","1","-i",concat,"-c:v","copy","-an",picture])
  final=work/"MARA_GHODOY_Documental_AMBER.mp4"
  # Keep the exact speech waveform timing; add only intro/outro space and
  # normalize perceived volume. No music, artificial speed or pitch effects.
  run(["-i",picture,"-i",wav,"-map","0:v:0","-map","1:a:0","-c:v","copy","-af","loudnorm=I=-16:TP=-1.5:LRA=11,adelay=800:all=1,apad","-ar","48000","-c:a","aac","-b:a","160k","-t",str(cuts[-1]),"-movflags","+faststart",final])
  info=probe(final);v=next(s for s in info["streams"] if s["codec_type"]=="video");a=next(s for s in info["streams"] if s["codec_type"]=="audio")
  duration=float(info["format"]["duration"])
  assert (v["width"],v["height"],v["codec_name"],a["codec_name"])==(540,960,"h264","aac")
  assert abs(duration-cuts[-1])<0.15 and abs(float(a["duration"])-duration)<0.15
  run(["-i",final,"-map","0:v:0","-map","0:a:0","-f","null","-"])
  qa=dict(passed=True,full_decode=True,duration=duration,width=540,height=960,fps=25,scenes=len(edit),speech_blocks=7,speech_duration=speech_len,voice_source_sha256=EXPECTED_SPEECH,voice_tempo=1.0,pitch_unchanged=True,music=False,scene_timing="seven exact block boundaries; within-block estimates refined by low-energy gaps",visual_audio_review_required=True,sha256=digest(final),bytes=final.stat().st_size)
  import shutil
  shutil.copyfile(final,ROOT/"mara-final.mp4")
  (ROOT/"mara-final-qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2))
  (ROOT/"mara-final-timeline.json").write_text(json.dumps(edit,ensure_ascii=False,indent=2))
  with zipfile.ZipFile(ROOT/"mara-final.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
   z.write(final,final.name);z.write(mp3,"Mara_Ghodoy_Locucion.mp3");z.write(ROOT/"mara-final-timeline.json","Montaje.json");z.write(ROOT/"mara-final-qa.json","QA.json");z.writestr("Creditos.json",credits)
  with zipfile.ZipFile(ROOT/"mara-final.zip") as z:assert z.testzip() is None
  token=(ROOT/"mara-full-speech.token").read_text().strip()
  log("verified",qa=qa,video="/private-mara-final/"+token+"/video.mp4",zip="/private-mara-final/"+token+"/delivery.zip")
if __name__=="__main__":
 main()
else:
 from app_full_speech import app, HTTPException,FileResponse,HTMLResponse
 @app.api_route("/private-mara-final/{token}/{filename}",methods=["GET","HEAD"],include_in_schema=False)
 def mara_final(token:str,filename:str,download:bool=False):
  key=ROOT/"mara-full-speech.token"
  if not key.is_file() or len(token)>128 or not secrets.compare_digest(token,key.read_text().strip()):raise HTTPException(404)
  headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow","Referrer-Policy":"no-referrer"}
  if filename=="watch":
   if not (ROOT/"mara-final.mp4").is_file():raise HTTPException(404)
   return HTMLResponse('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AMBER — Mara Ghodoy</title><style>body{font:18px system-ui;color:white;background:#141414;margin:24px}video{width:min(100%,420px);max-height:76vh}a{color:white}</style><h1>Mara Ghodoy</h1><video controls playsinline preload="metadata" src="video.mp4"></video><p><a href="video.mp4?download=true" download>Descargar MP4</a> · <a href="delivery.zip?download=true" download>Pack ZIP</a></p></html>',headers=headers)
  names={"video.mp4":("mara-final.mp4","video/mp4","MARA_GHODOY_Documental_AMBER.mp4"),"delivery.zip":("mara-final.zip","application/zip","MARA_GHODOY_Documental_AMBER.zip"),"qa.json":("mara-final-qa.json","application/json","QA.json")}
  if filename not in names:raise HTTPException(404)
  name,mime,out=names[filename];p=ROOT/name
  if not p.is_file():raise HTTPException(404)
  return FileResponse(p,media_type=mime,filename=out,content_disposition_type="attachment" if download else "inline",headers=headers)
