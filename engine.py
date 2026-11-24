"""Bounded, brand-neutral FFmpeg editing. No arbitrary shell commands."""
import hashlib
import json
import math
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MAX_CLIPS = 6
MAX_DURATION = 30
MAX_ASSET_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 80 * 1024 * 1024
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
Image.MAX_IMAGE_PIXELS = 16_000_000

class EngineError(ValueError):
    pass

def run(args, timeout=90):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/tmp", "LANG": "C.UTF-8"}
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired:
        raise EngineError("Media processing timed out.")
    if p.returncode:
        raise EngineError("Media processing failed: " + p.stderr.decode("utf-8", "replace")[-650:])
    return p.stdout

def ff(args, timeout=90):
    return run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-filter_threads", "1", "-filter_complex_threads", "1"] + args, timeout)

def media_format(p, audio=False):
    with open(p, "rb") as f:
        h = f.read(32)
    if len(h) >= 12 and h[4:8] == b"ftyp":
        return "mov"
    if h[:4] == b"\x1a\x45\xdf\xa3":
        return "matroska"
    if audio and h[:4] == b"RIFF" and h[8:12] == b"WAVE":
        return "wav"
    if audio and (h[:3] == b"ID3" or (len(h) >= 2 and h[0] == 255 and h[1] & 224 == 224)):
        return "mp3"
    raise EngineError("Supported inputs: MP4, WebM; audio also MP3 or WAV.")

def source_args(p, audio=False):
    return ["-protocol_whitelist", "file,pipe", "-threads", "1", "-f", media_format(p, audio), "-i", str(p)]

def probe(p, audio=False):
    data = json.loads(run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                           "-f", media_format(p, audio), "-show_streams", "-show_format",
                           "-of", "json", str(p)], 20))
    streams = data.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    try:
        duration = float(data["format"]["duration"])
        if not math.isfinite(duration) or not 0 < duration <= 1800:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise EngineError("Unsupported or missing media duration.")
    if audio:
        if not audios:
            raise EngineError("Audio stream missing.")
    else:
        if not videos:
            raise EngineError("Video stream missing.")
        w, h = videos[0].get("width", 0), videos[0].get("height", 0)
        if not (1 <= w <= 4096 and 1 <= h <= 4096 and w * h <= 3840 * 2160):
            raise EngineError("Video resolution exceeds input limits.")
    return {"duration": duration, "video": videos[0] if videos else None,
            "audio": bool(audios), "size": Path(p).stat().st_size}

def number(v, label, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise EngineError("Invalid " + label)
    return float(v)

def plain(v, label, n):
    if not isinstance(v,str) or len(v)>n or "\x00" in v:
        raise EngineError("Invalid " + label)
    return v

def parse_edit(spec, metadata, external=False):
    if not isinstance(spec, dict):
        raise EngineError("spec must be a JSON object.")
    if spec.get("usage_authorized") is not True or not plain(spec.get("permission_reference",""),"permission reference",400).strip():
        raise EngineError("Authorized usage and a permission reference are required.")
    width = spec.get("width",720)
    if width not in (360,540,720,1080) or isinstance(width,bool):
        raise EngineError("width must be 360, 540, 720 or 1080.")
    ratio = spec.get("ratio","9:16")
    if ratio not in ("9:16","1:1","16:9"):
        raise EngineError("Unsupported ratio.")
    w, h = (width, width*16//9) if ratio=="9:16" else ((width,width) if ratio=="1:1" else (width*16//9,width))
    w, h = w//2*2,h//2*2
    fps=spec.get("fps",24)
    if fps not in (24,25,30):
        raise EngineError("Unsupported fps.")
    fit=spec.get("fit","crop")
    if fit not in ("crop","contain"):
        raise EngineError("Unsupported fit.")
    shots = spec.get("segments")
    if shots is None:
        left=MAX_DURATION
        shots=[]
        for i,m in enumerate(metadata):
            d=min(5.0,m["duration"],left)
            if d<0.25: break
            shots.append({"asset":i,"start":0,"duration":d})
            left-=d
    if not isinstance(shots,list) or not 1<=len(shots)<=12:
        raise EngineError("One to twelve segments required.")
    out=[]
    total=0
    for s in shots:
        if not isinstance(s,dict):
            raise EngineError("Invalid segment.")
        i=s.get("asset")
        if isinstance(i,bool) or not isinstance(i,int) or not 0<=i<len(metadata):
            raise EngineError("Invalid segment asset index.")
        st=number(s.get("start",0),"start",0,metadata[i]["duration"])
        d=number(s.get("duration"),"duration",0.25,MAX_DURATION)
        if st+d>metadata[i]["duration"]+0.03:
            raise EngineError("Segment exceeds source duration.")
        total+=d
        out.append({"asset":i,"start":st,"duration":d})
    if total>MAX_DURATION+0.001 or total<0.5:
        raise EngineError("Output duration must be 0.5 to 30 seconds.")
    mode=spec.get("audio_mode","mute")
    if mode not in ("mute","source","external"):
        raise EngineError("Unsupported audio mode.")
    if mode!="mute" and spec.get("audio_authorized") is not True:
        raise EngineError("Audio reuse requires explicit authorization.")
    audio_asset=spec.get("audio_asset",0)
    if mode=="source" and (type(audio_asset) is not int or not 0<=audio_asset<len(metadata) or not metadata[audio_asset]["audio"]):
        raise EngineError("Requested source has no audio.")
    if mode=="external" and not external:
        raise EngineError("External audio file is required.")
    audio_start=number(spec.get("audio_start",0),"audio start",0,1800)
    if mode=="source" and audio_start>=metadata[audio_asset]["duration"]:
        raise EngineError("Audio start exceeds source.")
    cues=spec.get("captions",[])
    if not isinstance(cues,list) or len(cues)>12:
        raise EngineError("At most twelve captions.")
    clean=[]
    for c in cues:
        if not isinstance(c,dict): raise EngineError("Invalid caption.")
        a=number(c.get("start"),"caption start",0,total)
        b=number(c.get("end"),"caption end",0,total)
        if b<=a: raise EngineError("Invalid caption interval.")
        clean.append({"start":a,"end":b,"text":plain(c.get("text"),"caption",140)})
    return {"width":w,"height":h,"fps":fps,"fit":fit,"segments":out,"duration":total,
            "audio_mode":mode,"audio_asset":audio_asset,"audio_start":audio_start,
            "title":plain(spec.get("title",""),"title",140),"subtitle":plain(spec.get("subtitle",""),"subtitle",140),
            "captions":clean,"copy":plain(spec.get("copy",""),"copy",5000),
            "credits":plain(spec.get("credits",""),"credits",5000),
            "permission_reference":spec["permission_reference"]}

def encode_flags():
    return ["-c:v","libx264","-preset","veryfast","-crf","21","-threads","1","-pix_fmt","yuv420p"]

def text_fit(draw, s, width, size):
    for z in range(size, max(12,size//2)-1, -2):
        f=ImageFont.truetype(FONT,z)
        if draw.textbbox((0,0),s,font=f)[2]<=width: return f,s
    f=ImageFont.truetype(FONT,max(12,size//2))
    while len(s)>1 and draw.textbbox((0,0),s+"…",font=f)[2]>width: s=s[:-1]
    return f,s+"…"

def overlay_image(path, edit, logo=None):
    w,h=edit["width"],edit["height"]
    im=Image.new("RGBA",(w,h))
    d=ImageDraw.Draw(im)
    margin=max(12,w//15)
    if logo is not None:
        with Image.open(logo) as x:
            if x.format!="PNG" or x.width*x.height>4_000_000:
                raise EngineError("Logo must be a PNG under 4 megapixels.")
            x=x.convert("RGBA")
            x.thumbnail((int(w*.23),int(h*.09)),Image.Resampling.LANCZOS)
            im.alpha_composite(x,(margin,margin))
    title,sub=edit["title"],edit["subtitle"]
    if title or sub:
        y=int(h*.66)
        d.rectangle((0,y-margin,w,y+int(h*.17)),fill=(0,0,0,115))
        for s,size in [(title,max(18,w//13)),(sub,max(14,w//25))]:
            if s:
                f,s=text_fit(d,s,w-2*margin,size)
                d.text((margin,y),s,font=f,fill="white")
                y+=f.size+max(4,w//100)
    im.save(path)

def frame_at(path, t, out):
    ff(["-ss",str(t)]+source_args(path)+["-frames:v","1","-q:v","3",str(out)],30)

def srt_time(x):
    ms=round(x*1000); sec,ms=divmod(ms,1000); minute,sec=divmod(sec,60); hour,minute=divmod(minute,60)
    return f"{hour:02d}:{minute:02d}:{sec:02d},{ms:03d}"

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def render(work, videos, spec, logo=None, audio=None):
    work=Path(work)
    if not 1<=len(videos)<=MAX_CLIPS: raise EngineError("One to six source videos required.")
    md=[probe(p) for p in videos]
    edit=parse_edit(spec,md,audio is not None)
    if audio is not None and edit["audio_mode"]=="external":
        ad=probe(audio,True)
        if edit["audio_start"]>=ad["duration"]: raise EngineError("Audio start exceeds source.")
    w,h,fps=edit["width"],edit["height"],edit["fps"]
    if edit["fit"]=="crop":
        vf=f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"
    else:
        vf=f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}"
    parts=[]
    for n,s in enumerate(edit["segments"]):
        part=work/f"shot{n:02d}.mp4"
        ff(["-ss",str(s["start"])]+source_args(videos[s["asset"]])+["-t",str(s["duration"]),"-map","0:v:0","-an","-sn","-dn","-vf",vf]+encode_flags()+[str(part)])
        parts.append(part)
    # The concat manifest contains only fixed filenames we generated.
    manifest=work/"concat.txt"
    manifest.write_text("".join("file '"+p.name+"'\n" for p in parts))
    joined=work/"joined.mp4"
    ff(["-f","concat","-safe","1","-protocol_whitelist","file,pipe","-i",str(manifest),"-c","copy",str(joined)])
    joined_duration=probe(joined)["duration"]
    overlay=work/"overlay.png"
    overlay_image(overlay,edit,logo)
    inputs=source_args(joined)+["-f","image2","-i",str(overlay)]
    vf2="[0:v][1:v]overlay=0:0:repeatlast=1"
    for i,c in enumerate(edit["captions"]):
        # Drawtext reads fixed local files; expansion disabled; text is not filter syntax.
        p=work/f"caption{i}.txt"
        p.write_text(c["text"],encoding="utf-8")
        vf2+=f",drawtext=fontfile={FONT}:textfile={p}:expansion=none:fontsize={max(14,w//28)}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8:x=(w-tw)/2:y=h*0.82:enable='between(t,{c['start']},{c['end']})'"
    vf2+="[v]"
    mode=edit["audio_mode"]
    if mode=="mute":
        inputs+=["-f","lavfi","-i","anullsrc=r=48000:cl=stereo"]
    else:
        a=audio if mode=="external" else videos[edit["audio_asset"]]
        inputs+=["-ss",str(edit["audio_start"])]+source_args(a,True)
    final=work/"video.mp4"
    ff(inputs+["-filter_complex",vf2,"-map","[v]","-map","2:a:0","-af","apad","-t",str(joined_duration)]+encode_flags()+["-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-movflags","+faststart",str(final)],180)
    info=probe(final)
    v=info["video"]
    checks={"dimensions":v["width"]==w and v["height"]==h,"h264":v.get("codec_name")=="h264",
            "duration":abs(info["duration"]-edit["duration"])<=0.45,"audio_stream":info["audio"],
            "nonempty":info["size"]>1000}
    qa={"passed":all(checks.values()),"checks":checks,"duration_seconds":info["duration"],"width":v["width"],"height":v["height"],"size_bytes":info["size"],"sha256":digest(final),
        "note":"Technical checks only. Human review of identity, framing, audio and permissions required."}
    if not qa["passed"]: raise EngineError("Output failed technical checks: "+json.dumps(checks))
    frame_at(final,min(0.8,info["duration"]/2),work/"cover.jpg")
    thumbw=180
    thumbh=max(90,int(thumbw*h/w))
    sheet=Image.new("RGB",(thumbw*3,thumbh),(20,20,20))
    for n,fraction in enumerate((0.1,0.5,0.9)):
        p=work/f"sample{n}.jpg"
        frame_at(final,info["duration"]*fraction,p)
        with Image.open(p) as im:
            sheet.paste(im.resize((thumbw,thumbh)),(n*thumbw,0))
    sheet.save(work/"contact_sheet.jpg",quality=88)
    (work/"caption.txt").write_text(edit["copy"],encoding="utf-8")
    (work/"credits.json").write_text(json.dumps({"credits":edit["credits"],"permission_reference":edit["permission_reference"],
          "source_sha256":[digest(p) for p in videos],"audio_mode":mode},ensure_ascii=False,indent=2))
    (work/"edit.json").write_text(json.dumps(edit,ensure_ascii=False,indent=2))
    (work/"qa.json").write_text(json.dumps(qa,indent=2))
    (work/"captions.srt").write_text("\n\n".join(f"{i+1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}" for i,c in enumerate(edit["captions"]))+"\n",encoding="utf-8")
    names=["video.mp4","cover.jpg","contact_sheet.jpg","caption.txt","credits.json","edit.json","qa.json","captions.srt"]
    bundle=work/"delivery.zip"
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name in names: z.write(work/name,name)
    return bundle,qa
