"""Authenticated HTTPS media imports. Explicit approved hostnames, pinned DNS, no private addresses."""
import http.client, ipaddress, os, socket, ssl, time
from urllib.parse import urlsplit, urljoin
import engine

def allowed_hosts():
    return {"interactive-examples.mdn.mozilla.net","upload.wikimedia.org"} | {
        h.strip().lower() for h in os.getenv("MEDIA_ALLOWED_HOSTS","").split(",")
        if h.strip()}

def validate(url):
    p=urlsplit(url)
    host=(p.hostname or "").lower()
    if p.scheme!="https" or host not in allowed_hosts() or p.port not in (None,443) or p.username or p.password or p.fragment:
        raise engine.EngineError("Only HTTPS links on explicitly approved media hosts are accepted.")
    if len(url)>4096 or not p.path.startswith("/") or any(ord(c)<32 for c in url):
        raise engine.EngineError("Invalid media URL.")
    return p,host

def public_address(host):
    infos=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    ips=list(dict.fromkeys(i[4][0] for i in infos))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise engine.EngineError("Media host must resolve to public addresses.")
    return next((ip for ip in ips if ":" not in ip),ips[0])

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,ip,timeout):
        super().__init__(host,443,timeout=timeout,context=ssl.create_default_context())
        self.ip=ip
    def connect(self):
        sock=socket.create_connection((self.ip,443),self.timeout)
        try: self.sock=self._context.wrap_socket(sock,server_hostname=self.host)
        except Exception:
            sock.close()
            raise

def fetch(url,path,max_bytes=engine.MAX_ASSET_BYTES):
    end=time.monotonic()+60
    for _ in range(4):
        p,host=validate(url)
        ip=public_address(host)
        conn=PinnedHTTPS(host,ip,min(12,max(1,end-time.monotonic())))
        try:
            if time.monotonic()>end: raise engine.EngineError("Media transfer timed out.")
            target=p.path+("?" + p.query if p.query else "")
            conn.request("GET",target,headers={"User-Agent":"UniversalVideoEngine/0.2","Accept":"video/mp4,video/webm,application/octet-stream","Accept-Encoding":"identity"})
            r=conn.getresponse()
            if r.status in (301,302,303,307,308):
                url=urljoin(url,r.getheader("Location",""))
                continue
            if r.status!=200:
                raise engine.EngineError("Media host returned HTTP "+str(r.status))
            mime=(r.getheader("Content-Type") or "").split(";")[0].lower()
            if mime not in ("video/mp4","video/webm","application/octet-stream","application/mp4"):
                raise engine.EngineError("URL did not return a supported video.")
            n=r.getheader("Content-Length")
            if n is not None and int(n)>max_bytes:
                raise engine.EngineError("Media file exceeds import limit.")
            total=0
            with open(path,"wb") as f:
                while True:
                    if time.monotonic()>end: raise engine.EngineError("Media transfer timed out.")
                    b=r.read(min(65536,max_bytes-total+1))
                    if not b: break
                    total+=len(b)
                    if total>max_bytes: raise engine.EngineError("Media file exceeds import limit.")
                    f.write(b)
            if not total or (n is not None and total!=int(n)):
                raise engine.EngineError("Empty or incomplete media file.")
            if engine.media_format(path)!="mov" and mime=="video/mp4":
                raise engine.EngineError("Media signature mismatch.")
            info=engine.probe(path)
            return info
        except (OSError,http.client.HTTPException) as e:
            raise engine.EngineError("HTTPS media transfer failed: "+type(e).__name__) from None
        finally: conn.close()
    raise engine.EngineError("Too many media redirects.")
