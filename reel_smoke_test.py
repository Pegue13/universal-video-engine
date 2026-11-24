"""Bounded public-media transport probe; no full media download or redistribution.
Target is a Fran DC Instagram post embedded by LOS40:
https://los40.com/2024/06/01/vive-un-nuevo-in-sessions-all-night-long-con-fran-dc/
"""
import json, subprocess, urllib.request, urllib.parse, urllib.error, hashlib
URL="https://www.instagram.com/p/Bfl6OGNAub2/"
def report(status, **fields):
    print("DJ_SMOKE "+json.dumps({"status":status,**fields},ensure_ascii=True),flush=True)
def cdn_allowed(url):
    p=urllib.parse.urlsplit(url)
    h=(p.hostname or "").lower()
    return p.scheme=="https" and p.port in (None,443) and not p.username and not p.password and any(h==s or h.endswith("."+s) for s in ("cdninstagram.com","fbcdn.net"))
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not cdn_allowed(newurl): raise ValueError("Unapproved redirect host")
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def main():
    report("started",artist="Fran DC",source=URL)
    try:
        p=subprocess.run(["yt-dlp","--ignore-config","--no-cache-dir","--no-playlist",
            "--socket-timeout","12","--retries","0","--skip-download","--dump-single-json","--",URL],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=40)
        if p.returncode:
            report("metadata_failed",exit_code=p.returncode,error=p.stderr[-500:])
            return
        m=json.loads(p.stdout)
        formats=m.get("formats") or []
        options=[f for f in formats if f.get("ext")=="mp4" and f.get("vcodec") not in (None,"none") and f.get("url") and cdn_allowed(f["url"])]
        report("metadata_resolved",id=m.get("id"),uploader=m.get("uploader"),uploader_id=m.get("uploader_id"),
            formats=len(formats),mp4_formats=len(options),duration=m.get("duration"))
        if not options:
            report("no_public_mp4_format")
            return
        f=min(options,key=lambda f:(f.get("acodec")!="none",f.get("height") or 9999))
        headers={"Range":"bytes=0-65535","User-Agent":"Mozilla/5.0","Referer":"https://www.instagram.com/"}
        for k,v in (f.get("http_headers") or {}).items():
            if k.lower() in ("user-agent","referer","origin"): headers[k]=v
        request=urllib.request.Request(f["url"],headers=headers)
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=15) as resp:
            b=resp.read(65536)
            report("transport_verified",http=resp.status,bytes=len(b),
              content_range=resp.headers.get("Content-Range"),content_type=resp.headers.get("Content-Type"),
              mp4_signature=len(b)>=8 and b[4:8]==b"ftyp",sha256_prefix=hashlib.sha256(b).hexdigest(),
              width=f.get("width"),height=f.get("height"),
              full_file_saved=False)
    except urllib.error.HTTPError as e:
        report("transport_failed",http=e.code)
    except subprocess.TimeoutExpired:
        report("timeout")
    except Exception as e:
        report("diagnostic_error",error=type(e).__name__)
if __name__=="__main__": main()
