"""Opt-in Render build diagnostic: public NASA Earth Reel, no login or persistence.
NASA media guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/
Public Reel provenance: https://doi.org/10.3390/insects13080675, figure 3B.
Private technical verification only; not clearance for redistribution.
"""
import json, subprocess, tempfile, pathlib, hashlib
URL="https://www.instagram.com/reel/CSzbNMyluzg/"
BASE=["yt-dlp","--ignore-config","--no-cache-dir","--no-playlist",
      "--socket-timeout","12","--retries","0","--fragment-retries","0",
      "--no-progress","--max-downloads","1","--max-filesize","32M"]
def run(args, timeout):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
def result(status, **kw):
    print("REEL_SMOKE "+json.dumps({"status":status,**kw},ensure_ascii=True), flush=True)
def category(text):
    t=text.lower()
    for words,label in [
        (("login required","login","log in","sign in","cookies","rate-limit","rate limit","429","checkpoint"),"access_restricted"),
        (("403","forbidden","access denied"),"access_denied"),
        (("not available","unavailable","404","not found"),"unavailable"),
        (("resolve","dns","network","connection","timeout"),"network"),
        (("requested format","no video formats"),"format_unavailable")]:
        if any(w in t for w in words): return label
    return "extractor_error"
def main():
    try:
        result("started",source="NASA Earth public Reel",url=URL)
        p=run(BASE+["--skip-download","--dump-single-json","--",URL],40)
        if p.returncode:
            result("metadata_failed",category=category(p.stderr),exit_code=p.returncode,
                   error=p.stderr[-600:])
            return
        m=json.loads(p.stdout)
        if m.get("_type") in ("playlist","multi_video"):
            result("unsupported_multiple_items")
            return
        owner=str(m.get("uploader_id") or m.get("channel_id") or m.get("uploader") or "").lower().replace(" ","")
        formats=m.get("formats") or []
        result("metadata_resolved",id=m.get("id"),uploader=owner,formats=len(formats),duration=m.get("duration"))
        # The sample's source is documented, but third-party sound is not cleared.
        # Only request a genuinely video-only stream, with confirmed NASA Earth attribution.
        if owner.lstrip("@") not in ("nasaearth","nasa_earth"):
            result("download_skipped",reason="Source attribution not confirmed by extractor")
            return
        visual=[f for f in formats if f.get("ext")=="mp4" and f.get("acodec")=="none" and f.get("vcodec") not in (None,"none") and (f.get("height") or 0)<=720]
        if not visual:
            result("download_skipped",reason="No separate MP4 video-only stream within limit; soundtrack rights not established")
            return
        with tempfile.TemporaryDirectory(prefix="reel-smoke-") as d:
            path=pathlib.Path(d)/"reel.mp4"
            p=run(BASE+["--format","bestvideo[ext=mp4][height<=720]","--output",str(path),"--",URL],70)
            if p.returncode or not path.is_file():
                result("download_failed",category=category(p.stderr),exit_code=p.returncode,error=p.stderr[-600:])
                return
            if path.stat().st_size>32*1024*1024:
                result("file_rejected",reason="size limit")
                return
            probe=run(["ffprobe","-v","error","-protocol_whitelist","file,pipe","-f","mov","-show_streams","-show_format","-of","json",str(path)],20)
            if probe.returncode:
                result("file_rejected",reason="ffprobe failed")
                return
            data=json.loads(probe.stdout)
            video=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),None)
            if not video or any(s.get("codec_type")=="audio" for s in data.get("streams",[])):
                result("file_rejected",reason="expected video-only stream")
                return
            h=hashlib.sha256()
            with path.open("rb") as f:
                for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
            result("download_verified",bytes=path.stat().st_size,sha256=h.hexdigest(),
                   width=video.get("width"),height=video.get("height"),duration=data.get("format",{}).get("duration"))
    except subprocess.TimeoutExpired:
        result("timeout")
    except Exception as e:
        result("diagnostic_error",error=type(e).__name__)
if __name__=="__main__": main()
