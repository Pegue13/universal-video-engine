"""Independent video processing API, authenticated and bounded."""
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

import engine
import media_import

app=FastAPI(title="Universal Video Engine",version="0.2.0",
    description="Independent video editing with explicit media permissions.")
busy=threading.Lock()
MAX_REQUEST=engine.MAX_TOTAL_BYTES+2*1024*1024
API_KEY=os.environ.get("VIDEO_ENGINE_API_KEY","")

@app.middleware("http")
async def guard(request:Request,call_next):
    path=request.url.path
    if path.startswith("/v1/"):
        auth=request.headers.get("authorization","")
        if len(API_KEY)<24:
            return JSONResponse({"detail":"Service authentication has not been configured."},status_code=503)
        if not secrets.compare_digest(auth.encode(),("Bearer "+API_KEY).encode()):
            return JSONResponse({"detail":"Authentication required."},status_code=401,headers={"WWW-Authenticate":"Bearer"})
        if request.method in ("POST","PUT"):
            try: size=int(request.headers.get("content-length","-1"))
            except ValueError: size=-1
            if not 0<=size<=MAX_REQUEST:
                return JSONResponse({"detail":"A valid Content-Length within the upload limit is required."},status_code=413)
        if not busy.acquire(blocking=False):
            return JSONResponse({"detail":"Engine is busy. Retry after the active job."},status_code=429)
        try: return await call_next(request)
        finally: busy.release()
    return await call_next(request)

@app.get("/")
@app.get("/health")
def health():
    ready=bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    return JSONResponse({"service":"Universal Video Engine","version":"0.2.0",
        "ready":ready,"auth_configured":len(API_KEY)>=24,
        "instagram_enabled":os.getenv("ENABLE_INSTAGRAM","false")=="true",
        "max_clips":engine.MAX_CLIPS,"max_duration_seconds":engine.MAX_DURATION},status_code=200 if ready else 503)

def save(upload,path,limit):
    count=0
    with open(path,"wb") as f:
        while True:
            b=upload.file.read(1024*1024)
            if not b: break
            count+=len(b)
            if count>limit: raise engine.EngineError("Input exceeds size limit.")
            f.write(b)
    if count==0: raise engine.EngineError("Empty input.")
    return count

def fail(work,exc):
    shutil.rmtree(work,ignore_errors=True)
    if isinstance(exc,(engine.EngineError,ValueError,TypeError,KeyError)):
        raise HTTPException(422,str(exc)[:850])
    raise HTTPException(500,"Processing failed; retry with a smaller supported file.")

@app.post("/v1/inspect")
def inspect_video(video:UploadFile=File(...)):
    work=Path(tempfile.mkdtemp(prefix="uve-"))
    try:
        p=work/"source.bin"
        save(video,p,engine.MAX_ASSET_BYTES)
        info=engine.probe(p)
        return {"duration":info["duration"],"size":info["size"],"audio":info["audio"],
                "width":info["video"]["width"],"height":info["video"]["height"],
                "codec":info["video"].get("codec_name"),"sha256":engine.digest(p)}
    except Exception as e: fail(work,e)
    finally: shutil.rmtree(work,ignore_errors=True)

@app.post("/v1/render",responses={200:{"content":{"application/zip":{}}}})
def render_video(videos:list[UploadFile]=File(...),spec:str=Form(...),
                 logo:UploadFile|None=File(None),audio:UploadFile|None=File(None)):
    work=Path(tempfile.mkdtemp(prefix="uve-"))
    try:
        if not 1<=len(videos)<=engine.MAX_CLIPS: raise engine.EngineError("One to six videos required.")
        if len(spec)>24000: raise engine.EngineError("Edit specification too large.")
        edit=json.loads(spec)
        paths=[]
        total=0
        for i,v in enumerate(videos):
            p=work/f"input{i}.bin"
            total+=save(v,p,engine.MAX_ASSET_BYTES)
            paths.append(p)
        lp=ap=None
        if logo:
            lp=work/"logo.png"; total+=save(logo,lp,5*1024*1024)
        if audio:
            ap=work/"audio.bin"; total+=save(audio,ap,engine.MAX_ASSET_BYTES)
        if total>engine.MAX_TOTAL_BYTES: raise engine.EngineError("Combined input exceeds 80 MiB.")
        result,qa=engine.render(work,paths,edit,lp,ap)
        return FileResponse(result,media_type="application/zip",filename="universal-video-delivery.zip",
            background=BackgroundTask(shutil.rmtree,work,ignore_errors=True),
            headers={"Cache-Control":"no-store","X-Video-SHA256":qa["sha256"]})
    except Exception as e: fail(work,e)

class ReelRequest(BaseModel):
    url:str=Field(max_length=300)
    download_authorized:bool=False
    usage_authorized:bool=False
    permission_reference:str=Field(default="",max_length=400)

def canonical_reel(url):
    p=urlsplit(url)
    if p.scheme!="https" or p.netloc.lower() not in ("instagram.com","www.instagram.com") or p.fragment:
        raise engine.EngineError("Only HTTPS Instagram public Reel links are supported.")
    match=re.fullmatch(r"/(reel|reels|p|tv)/([A-Za-z0-9_-]{5,40})/?",p.path)
    if not match: raise engine.EngineError("Use a direct Instagram Reel URL.")
    return "https://www.instagram.com/"+("reel" if match.group(1)=="reels" else match.group(1))+"/"+match.group(2)+"/"

@app.post("/v1/import/instagram",responses={200:{"content":{"video/mp4":{}}}})
def import_reel(req:ReelRequest):
    if os.getenv("ENABLE_INSTAGRAM","false")!="true":
        raise HTTPException(503,"Instagram import disabled.")
    if not(req.download_authorized and req.usage_authorized and req.permission_reference.strip()):
        raise HTTPException(422,"Both permissions and a reference are required.")
    work=Path(tempfile.mkdtemp(prefix="uve-"))
    try:
        url=canonical_reel(req.url)
        # Never use credentials, login bypasses, playlists or user-supplied downloader options.
        engine.run(["yt-dlp","--ignore-config","--no-cache-dir","--no-playlist",
            "--socket-timeout","12","--retries","1","--fragment-retries","1",
            "--max-downloads","1","--max-filesize","32M","--no-progress",
            "--format","best[ext=mp4][height<=720]/best[ext=mp4]",
            "--output",str(work/"source.%(ext)s"),"--",url],90,accepted_exit_codes=(0,101))
        p=work/"source.mp4"
        if not p.is_file() or p.stat().st_size>engine.MAX_ASSET_BYTES:
            raise engine.EngineError("No supported, authorized public MP4 could be retrieved.")
        info=engine.probe(p)
        return FileResponse(p,media_type="video/mp4",filename="instagram-reel.mp4",
            background=BackgroundTask(shutil.rmtree,work,ignore_errors=True),
            headers={"Cache-Control":"no-store","X-Source-SHA256":engine.digest(p)})
    except Exception as e: fail(work,e)


class DirectRequest(BaseModel):
    url:str=Field(max_length=4096)
    download_authorized:bool=False
    usage_authorized:bool=False
    permission_reference:str=Field(default="",max_length=400)

@app.post("/v1/import/direct")
def import_direct(req:DirectRequest):
    if not(req.download_authorized and req.usage_authorized and req.permission_reference.strip()):
        raise HTTPException(422,"Both permissions and a reference are required.")
    work=Path(tempfile.mkdtemp(prefix="uve-direct-"))
    try:
        p=work/"source.bin"
        info=media_import.fetch(req.url,p)
        ext="mp4" if engine.media_format(p)=="mov" else "webm"
        return FileResponse(p,media_type="video/"+ext,filename="imported."+ext,
            background=BackgroundTask(shutil.rmtree,work,ignore_errors=True),
            headers={"Cache-Control":"no-store","X-Source-SHA256":engine.digest(p)})
    except Exception as e: fail(work,e)

class DirectRenderRequest(BaseModel):
    sources:list[DirectRequest]=Field(min_length=1,max_length=6)
    spec:dict

@app.post("/v1/render/direct",responses={200:{"content":{"application/zip":{}}}})
def direct_render(req:DirectRenderRequest):
    work=Path(tempfile.mkdtemp(prefix="uve-direct-render-"))
    try:
        if len(json.dumps(req.spec))>24000: raise engine.EngineError("Edit specification too large.")
        paths=[]
        total=0
        for i,s in enumerate(req.sources):
            if not(s.download_authorized and s.usage_authorized and s.permission_reference.strip()):
                raise engine.EngineError("Every source requires both permissions and a reference.")
            p=work/f"source{i}.bin"
            left=min(engine.MAX_ASSET_BYTES,engine.MAX_TOTAL_BYTES-total)
            if left<1: raise engine.EngineError("Combined media limit exceeded.")
            media_import.fetch(s.url,p,left)
            total+=p.stat().st_size
            paths.append(p)
        edit=dict(req.spec)
        edit["usage_authorized"]=True
        edit["permission_reference"]="; ".join(s.permission_reference for s in req.sources)[:400]
        bundle,qa=engine.render(work,paths,edit)
        return FileResponse(bundle,media_type="application/zip",filename="universal-video-delivery.zip",
            background=BackgroundTask(shutil.rmtree,work,ignore_errors=True),
            headers={"Cache-Control":"no-store","X-Video-SHA256":qa["sha256"]})
    except Exception as e: fail(work,e)


@app.get("/examples/dj-qbert-source-clips.zip",include_in_schema=False)
def example_dj_pack():
    # This single immutable asset contains only publicly licensed material.
    # No user uploads, directory listing, parameters, or API credentials are exposed.
    p=Path("/app/examples/dj-qbert-source-clips.zip")
    if not p.is_file():
        raise HTTPException(404,"Example pack not available.")
    return FileResponse(p,media_type="application/zip",filename="DJ_QBert_Source_Clips_CC_BY_3.zip")


@app.get("/examples/dj-liek-reel.mp4",include_in_schema=False)
def dj_liek_video():
    p=Path("/app/examples/dj-liek-reel.mp4")
    if not p.is_file(): raise HTTPException(404,"Verified example not available.")
    return FileResponse(p,media_type="video/mp4",filename="DJ_Liek_Reel_CC_BY_SA_4.mp4")

@app.get("/examples/dj-liek-reel.zip",include_in_schema=False)
def dj_liek_bundle():
    p=Path("/app/examples/dj-liek-reel.zip")
    if not p.is_file(): raise HTTPException(404,"Verified example not available.")
    return FileResponse(p,media_type="application/zip",filename="DJ_Liek_Reel_CC_BY_SA_4.zip")
