"""Private, unlisted editing preview using files expressly offered in Henners' media package."""
import html,json,os,pathlib,re,secrets,shutil,tempfile,urllib.parse,urllib.request
from html.parser import HTMLParser
import engine,media_import
PAGE="https://www.dj.henners.bio/media-package"
DEST=pathlib.Path("/app/examples")
HOSTS={"www.dj.henners.bio","dj.henners.bio","www.henners.bio","henners.bio"}
def log(status,**fields):
    print("HENNERS_PREVIEW "+json.dumps({"status":status,**fields},ensure_ascii=True),flush=True)
class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ("href","src","data-src","data-href","data-url","data-download") and v:
                self.urls.append(v)
def safe_url(url,base=PAGE):
    u=urllib.parse.urljoin(base,html.unescape(url))
    p=urllib.parse.urlsplit(u)
    if p.scheme!="https" or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443): return None
    return u
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not safe_url(newurl,req.full_url): raise ValueError("Media package redirect outside approved artist domain.")
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def main():
    DEST.mkdir(exist_ok=True)
    opener=urllib.request.build_opener(Redirect())
    req=urllib.request.Request(PAGE,headers={"User-Agent":"UniversalVideoEngine/0.2 media-package preview"})
    with opener.open(req,timeout=15) as r:
        body=r.read(2_000_000).decode("utf-8","replace"); base=r.url
    log("page_loaded",bytes=len(body),url=base)
    decoded=html.unescape(body).replace("\\/","/").replace("\\u0026","&")
    parser=Parser();parser.feed(decoded)
    raw=parser.urls+re.findall(r'''["']([^"'<>\s]+?\.(?:mp4|webm)(?:\?[^"'<>\s]*)?)["']''',decoded,re.I)
    urls=[]
    for u in raw:
        u=safe_url(u,base)
        if u and urllib.parse.urlsplit(u).path.lower().endswith((".mp4",".webm")) and u not in urls: urls.append(u)
    log("download_candidates",count=len(urls),paths=[urllib.parse.urlsplit(u).path for u in urls[:12]])
    if not urls: return
    os.environ["MEDIA_ALLOWED_HOSTS"]=",".join(HOSTS)
    ranked=sorted(urls,key=lambda u:(not any(k in u.lower() for k in ("ambrosia","lundjuweel","basement","rijksmuseum")),len(u)))
    with tempfile.TemporaryDirectory(prefix="uve-henners-") as td:
        work=pathlib.Path(td);paths=[];sources=[]
        for u in ranked[:6]:
            p=work/f"source{len(paths)}.bin"
            try:
                m=media_import.fetch(u,p)
                if m["duration"]<2: continue
                paths.append(p);sources.append({"url":u,"duration":m["duration"],"size":m["size"]})
                log("source_verified",path=urllib.parse.urlsplit(u).path,duration=m["duration"],size=m["size"])
                if len(paths)>=3:break
            except Exception as e:
                log("source_failed",path=urllib.parse.urlsplit(u).path,reason=str(e)[:180])
        if not paths: return
        segments=[]
        for i,m in enumerate(sources):
            dur=min(5,m["duration"]-0.2)
            segments.append({"asset":i,"start":min(1,max(0,m["duration"]-dur-0.1)),"duration":dur})
        spec={"usage_authorized":True,"permission_reference":"Artist's public downloadable press package; private review only. Not licensed for publication without confirmation.",
              "width":540,"ratio":"9:16","fit":"contain","fps":25,"audio_mode":"mute",
              "title":"HENNERS","subtitle":"Live sessions / preview",
              "segments":segments,"copy":"Private editing demonstration. Not a final release; confirm reuse rights before publication.",
              "credits":"Original downloadable press assets: "+PAGE+"\n"+json.dumps(sources)+"\nEdits: cuts, reframing, title and mute. No artist endorsement."}
        bundle,qa=engine.render(work,paths,spec)
        token=secrets.token_urlsafe(24)
        shutil.copyfile(work/"video.mp4",DEST/"henners-preview.mp4")
        shutil.copyfile(bundle,DEST/"henners-preview.zip")
        (DEST/"henners-preview.token").write_text(token)
        log("render_verified",qa=qa,zip_bytes=bundle.stat().st_size,download_path="/private-preview/"+token+"/video.mp4",zip_path="/private-preview/"+token+"/delivery.zip")
if __name__=="__main__":
    try:main()
    except Exception as e:log("failed",reason=str(e)[:300])
