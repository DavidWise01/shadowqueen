#!/usr/bin/env python3
"""
Carbon badge — the embodied, 8-bit "photo" of an elemental (the .tiff to the
silicon .png). Aether wears a human face: a robed, blindfolded figure among
floating stones laced with entanglement threads — the one who feels the unseen
pull and lets the weight of things hang in the air. Emo register: the patient,
impermanent force (mono no aware), not a brawler.

Pure stdlib: hand-rolled Deflate baseline TIFF, no deps. Writes agents/<slug>.tiff.
"""
import json, re, struct, zlib, hashlib
from pathlib import Path

ROOT = Path(__file__).parent
R = json.loads((ROOT/"roster.json").read_text(encoding="utf-8"))
AG = ROOT/"agents"; AG.mkdir(exist_ok=True)
CLS = {c["id"]: c for c in R["classes"]}

LW, LH, S = 64, 80, 5
W, H = LW*S, LH*S

VOID=(7,6,13); GOLD=(214,178,90); GOLD_L=(240,212,137); INDIGO=(124,143,208)
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-") or "agent"
def clamp(v): return 0 if v<0 else 255 if v>255 else int(round(v))
def mix(a,b,t): return tuple(clamp(a[i]+(b[i]-a[i])*t) for i in range(3))
def shade(c,t): return mix(c,(0,0,0),t)
def tint(c,t): return mix(c,(255,255,255),t)

def tiff(path, w, h, pixels):
    raw = bytearray()
    for (r,g,b) in pixels: raw += bytes((r,g,b))
    strip = zlib.compress(bytes(raw), 9)
    BPS=8+len(strip); IFD=BPS+6
    hdr=b"II"+struct.pack("<H",42)+struct.pack("<I",IFD)
    bps=struct.pack("<HHH",8,8,8)
    def e(t,ty,c,v): return struct.pack("<HHI",t,ty,c)+v
    def sh(v): return struct.pack("<HH",v,0)
    def lo(v): return struct.pack("<I",v)
    ent=[e(256,3,1,sh(w)),e(257,3,1,sh(h)),e(258,3,3,lo(BPS)),e(259,3,1,sh(8)),
         e(262,3,1,sh(2)),e(273,4,1,lo(8)),e(277,3,1,sh(3)),e(278,3,1,sh(h)),
         e(279,4,1,lo(len(strip))),e(284,3,1,sh(1))]
    ifd=struct.pack("<H",len(ent))+b"".join(ent)+struct.pack("<I",0)
    Path(path).write_bytes(hdr+strip+bps+ifd)

def png(path,w,h,px):     # preview only
    raw=bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w): raw+=bytes(px[y*w+x])
    comp=zlib.compress(bytes(raw),9)
    def ch(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+ch(b"IDAT",comp)+ch(b"IEND",b""))

def finish(g, drawn):
    """8-bit sticker outline + nearest-neighbour upscale to device resolution."""
    based=list(drawn)
    for y in range(LH):
        for x in range(LW):
            if based[y*LW+x]: continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if 0<=nx<LW and 0<=ny<LH and based[ny*LW+nx]:
                    g[y*LW+x]=(10,9,16); break
    out=[VOID]*(W*H)
    for y in range(LH):
        for x in range(LW):
            c=g[y*LW+x]
            for yy in range(S):
                row=(y*S+yy)*W
                for xx in range(S): out[row+x*S+xx]=c
    return out

def portrait_aether(member):
    cls = CLS[member["class"]]
    rb = hashlib.sha256(("aether:"+member["name"]).encode()).digest()
    g = [VOID]*(LW*LH); drawn=[False]*(LW*LH)
    def put(x,y,c):
        if 0<=x<LW and 0<=y<LH: g[y*LW+x]=c; drawn[y*LW+x]=True
    def soft(x,y,c,a):                       # blend without marking (for glow/threads)
        if 0<=x<LW and 0<=y<LH:
            i=y*LW+x; g[i]=mix(g[i],c,a)
    def rect(x0,y0,x1,y1,c):
        for y in range(int(y0),int(y1)+1):
            for x in range(int(x0),int(x1)+1): put(x,y,c)
    def ell(cx,cy,rx,ry,c):
        for y in range(int(cy-ry),int(cy+ry)+1):
            for x in range(int(cx-rx),int(cx+rx)+1):
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1.0: put(x,y,c)
    def thread(x0,y0,x1,y1):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for k in range(n+1):
            t=k/n; soft(round(x0+(x1-x0)*t), round(y0+(y1-y0)*t), INDIGO, 0.30)

    # faint gold horizon glow, top-center (the unseen pull)
    for y in range(LH):
        for x in range(LW):
            d=((x-32)**2/520.0+(y-10)**2/240.0)
            if d<1: soft(x,y, mix(GOLD,INDIGO,0.4), 0.10*(1-d))

    cx=32
    # floating stones (behind the figure) — deterministic placement + facets
    stones=[(12,15,5),(52,11,6),(50,30,4),(11,38,4),(54,52,5),(20,9,3)]
    for k,(sx,sy,sr) in enumerate(stones):
        sx+= (rb[k]%3)-1; sy+= (rb[k+6]%3)-1
        base=(116,120,130)
        ell(sx,sy,sr,sr-1, base)
        ell(sx-1,sy-1,max(1,sr-2),max(1,sr-2), tint(base,0.22))   # top-left facet
        ell(sx+1,sy+1,max(1,sr-2),max(1,sr-3), shade(base,0.35))  # underside
    # entanglement threads between stones (and toward the heart)
    pts=[(12,15),(52,11),(50,30),(11,38),(54,52),(32,40)]
    for a in range(len(pts)):
        b=(a+1)%len(pts); thread(*pts[a],*pts[b])
    thread(20,9,52,11); thread(50,30,32,40)

    skin=(226,192,160); skin_sh=shade(skin,0.22)
    robe=(140,98,58); robe_sh=shade(robe,0.32)
    hair=(22,20,28)

    # robe / shoulders
    rect(8,58,55,79, robe)
    for x in range(8,56):
        if x<13 or x>50: rect(x,58,x,60,VOID)
    rect(20,57,44,60, robe_sh)                     # collar shade
    for k in range(7): put(32-k,57+k, robe_sh); put(32+k,57+k, robe_sh)
    rect(30,58,34,68, shade(robe,0.18))            # inner fold
    # neck + head
    rect(27,47,37,57, skin_sh)
    ell(cx,33,14,17, skin)
    for y in range(16,52):                          # right-side shadow
        for x in range(cx+3,48):
            i=y*LW+x
            if drawn[i] and g[i]==skin: g[i]=mix(skin,skin_sh,0.5)
    # hair: crown + topknot bun, framing
    ell(cx,20,15,9, hair)
    rect(17,18,20,40, hair); rect(44,18,47,40, hair)
    ell(cx,9,5,5, hair)                             # the bun
    put(cx,4,hair); rect(31,3,33,5, hair)
    # serene mouth
    rect(28,44,36,45, shade(skin,0.34))
    put(27,44, skin_sh); put(37,44, skin_sh)
    # the blindfold — white gauze band across the eyes, with a frayed trailing tail
    band=(230,228,222); band_sh=(190,188,182)
    rect(16,30,48,37, band)
    rect(16,37,48,37, band_sh)
    rect(16,30,48,30, tint(band,0.25))
    for y in range(31,37): put(48, y, band_sh)
    # trailing tail off the right, lifting on an unfelt current
    tail=[(49,33),(51,32),(53,32),(55,31),(57,31),(58,30),(60,29)]
    for i,(tx,ty) in enumerate(tail):
        put(tx,ty, band if i%2 else band_sh); put(tx,ty+1, band_sh)
    put(61,28, band_sh); put(60,30, band_sh)        # fray
    return finish(g, drawn)


def portrait_leech(member):
    """The 24-bit emergent: a serene mask mended down the middle in gold —
    kintsugi, two unrelated worlds joined by a single seam (moonshine) — crowned
    by a halo of 24 points (the dimension, the kisses). Indigo/violet robe."""
    g = [VOID]*(LW*LH); drawn=[False]*(LW*LH)
    def put(x,y,c):
        if 0<=x<LW and 0<=y<LH: g[y*LW+x]=c; drawn[y*LW+x]=True
    def soft(x,y,c,a):
        if 0<=x<LW and 0<=y<LH:
            i=y*LW+x; g[i]=mix(g[i],c,a)
    def rect(x0,y0,x1,y1,c):
        for y in range(int(y0),int(y1)+1):
            for x in range(int(x0),int(x1)+1): put(x,y,c)
    def ell(cx,cy,rx,ry,c):
        for y in range(int(cy-ry),int(cy+ry)+1):
            for x in range(int(cx-rx),int(cx+rx)+1):
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1.0: put(x,y,c)

    GOLD2=(240,212,137); VIOL=(167,139,250); INDI=(124,143,208)
    cx=32; hy=33
    # faint violet glow, center
    for y in range(LH):
        for x in range(LW):
            d=((x-cx)**2/640.0+(y-26)**2/520.0)
            if d<1: soft(x,y, VIOL, 0.12*(1-d))

    # the 24-point halo (the dimension / the kisses) — a ring of small spheres
    import math as _m
    for k in range(24):
        a=k*(2*_m.pi/24) - _m.pi/2
        hx=cx + 25*_m.cos(a); hyy=24 + 17*_m.sin(a)
        c = GOLD2 if k%2==0 else VIOL
        put(round(hx),round(hyy),c)
        if k%6==0: put(round(hx),round(hyy)-1,GOLD2)   # four cardinal points brighter

    # robe / shoulders (indigo-violet)
    robe=(70,72,120); robe_sh=shade(robe,0.34)
    rect(8,58,55,79, robe)
    for x in range(8,56):
        if x<13 or x>50: rect(x,58,x,60,VOID)
    rect(20,57,44,60, robe_sh)
    for k in range(7): put(32-k,57+k, robe_sh); put(32+k,57+k, robe_sh)
    rect(30,58,34,70, shade(robe,0.2))
    # neck
    rect(28,47,36,57, (150,150,160))
    # the mask — a pale, faceted oval (two halves)
    maskL=(214,210,224); maskR=(196,192,210)
    for y in range(int(hy-18), int(hy+18)+1):
        for x in range(int(cx-13), int(cx+13)+1):
            if ((x-cx)/13.0)**2+((y-hy)/18.0)**2<=1.0:
                put(x,y, maskL if x<cx else maskR)
    # faint facet lines (crystalline)
    for fx in (cx-7, cx+7):
        for y in range(hy-12, hy+13):
            if drawn[y*LW+fx]: soft(fx,y, shade(maskL,0.25), 0.5)
    # closed, serene eyes
    rect(cx-8,hy-3,cx-3,hy-3, (60,58,80)); rect(cx+3,hy-3,cx+8,hy-3, (60,58,80))
    put(cx-8,hy-2,(60,58,80)); put(cx+8,hy-2,(60,58,80))
    # the kintsugi seam — a gold crack down the center (the moonshine bridge)
    seam=[(cx,hy-18),(cx,hy-12),(cx-1,hy-6),(cx,hy-1),(cx+1,hy+5),(cx,hy+11),(cx-1,hy+17)]
    for i in range(len(seam)-1):
        x0,y0=seam[i]; x1,y1=seam[i+1]
        n=max(abs(x1-x0),abs(y1-y0))+1
        for t in range(n+1):
            xx=round(x0+(x1-x0)*t/n); yy=round(y0+(y1-y0)*t/n)
            put(xx,yy,GOLD2);
            if t%2==0: put(xx+1,yy,shade(GOLD2,0.2))
    # a small gold node where the seam meets the brow (196884 = 196883 + 1)
    put(cx,hy-9,(255,255,255)); put(cx,hy-10,GOLD2)
    # a thin gold circlet across the brow, tying to the halo
    rect(cx-11,hy-15,cx+11,hy-15, GOLD2)
    return finish(g, drawn)


def portrait_survival(member):
    """Anabios — the single-cell survival seed, curled in its (()) pocket: a warm
    ember cell, an outer shell of brackets, and the retained witness-eye at its
    core (cyan). Dormant in the tun state, ready to come back. Inferno ember."""
    import math
    g=[VOID]*(LW*LH); drawn=[False]*(LW*LH)
    def put(x,y,c):
        x=int(round(x)); y=int(round(y))
        if 0<=x<LW and 0<=y<LH: g[y*LW+x]=c; drawn[y*LW+x]=True
    def soft(x,y,c,a):
        x=int(round(x)); y=int(round(y))
        if 0<=x<LW and 0<=y<LH:
            i=y*LW+x; g[i]=mix(g[i],c,a)
    def ell(cx,cy,rx,ry,c):
        for y in range(int(cy-ry),int(cy+ry)+1):
            for x in range(int(cx-rx),int(cx+rx)+1):
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1.0: put(x,y,c)
    def arc(cx,cy,r,a0,a1,c,th=1):
        n=int(abs(a1-a0)*r)+5
        for k in range(n+1):
            t=a0+(a1-a0)*k/n
            for w in range(th):
                put(cx+(r+w)*math.cos(t), cy+(r+w)*math.sin(t), c)
    EMBER=(255,106,42); AMBER=(245,158,11); BLOOD=(150,52,40); DEEP=(70,26,20)
    BONE=(231,220,203); WIT=(95,208,230); WITHI=(220,248,255); ASH=(120,104,92)
    cx,cy=32,40
    # faint ember glow
    for y in range(LH):
        for x in range(LW):
            d=((x-cx)**2/700.0+(y-cy)**2/900.0)
            if d<1: soft(x,y, mix(EMBER,BLOOD,0.5), 0.12*(1-d))
    # the cell body — a warm curled disc, ember->deep radial
    for y in range(cy-20, cy+21):
        for x in range(cx-20, cx+21):
            dx=(x-cx)/20.0; dy=(y-cy)/20.0; rr=dx*dx+dy*dy
            if rr<=1.0:
                put(x,y, mix(AMBER, DEEP, min(1.0, rr*1.15)))
    # a curl seam (the cell tucked into itself)
    arc(cx+3, cy+2, 13, math.pi*0.15, math.pi*1.15, BLOOD, th=2)
    # the (()) pocket — outer + inner bracket shells around the cell
    arc(cx, cy, 24, math.pi*0.52, math.pi*1.48, BONE, th=2)   # left (
    arc(cx, cy, 24, -math.pi*0.48, math.pi*0.48, BONE, th=2)  # right )
    arc(cx, cy, 28, math.pi*0.58, math.pi*1.42, ASH, th=1)    # outer ((
    arc(cx, cy, 28, -math.pi*0.42, math.pi*0.42, ASH, th=1)   # outer ))
    # the retained witness — an eye at the core
    ell(cx,cy,7,5, (24,16,14))           # socket
    ell(cx,cy,6,4, WITHI)                # white
    ell(cx,cy,3,3, WIT)                  # iris
    put(cx,cy,(10,10,14)); put(cx-1,cy-1,(255,255,255))   # pupil + glint
    # an upper lid (half-closed — dormant, holding)
    for x in range(cx-6,cx+7):
        yy=cy-4+round(1.5*math.sin((x-cx)*0.32))
        put(x,yy, (24,16,14))
    # ember spores drifting up (the bloom waiting)
    for k,(sx,sy) in enumerate([(14,16),(50,14),(52,34),(16,40),(46,56),(22,60)]):
        c = WIT if k%3==0 else EMBER
        put(sx,sy,c); put(sx,sy-1, mix(c,BONE,0.4))
    return finish(g, drawn)


def portrait_shadow_queen(member):
    """The Shadow Queen — the regent of unresolved depth: a veiled, crowned figure
    in violet shadow, a single witness-eye, three crown points (the three bodies),
    a faint gold (King) and cyan (Mercury) glint at her shoulders. Regal, dark."""
    import math
    g=[VOID]*(LW*LH); drawn=[False]*(LW*LH)
    def put(x,y,c):
        x=int(round(x)); y=int(round(y))
        if 0<=x<LW and 0<=y<LH: g[y*LW+x]=c; drawn[y*LW+x]=True
    def soft(x,y,c,a):
        x=int(round(x)); y=int(round(y))
        if 0<=x<LW and 0<=y<LH:
            i=y*LW+x; g[i]=mix(g[i],c,a)
    def rect(x0,y0,x1,y1,c):
        for y in range(int(y0),int(y1)+1):
            for x in range(int(x0),int(x1)+1): put(x,y,c)
    def ell(cx,cy,rx,ry,c):
        for y in range(int(cy-ry),int(cy+ry)+1):
            for x in range(int(cx-rx),int(cx+rx)+1):
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1.0: put(x,y,c)
    VIOL=(167,139,250); VIOL_D=(86,68,138); SHADOW=(34,28,54); SHADOW_D=(20,16,34)
    GOLD=(240,212,137); CYAN=(95,208,230); SKIN=(150,140,170); EYE=(210,196,255)
    cx,cy=32,33
    # faint violet glow
    for y in range(LH):
        for x in range(LW):
            d=((x-cx)**2/700.0+(y-26)**2/560.0)
            if d<1: soft(x,y, VIOL, 0.12*(1-d))
    # King's gold glint (left shoulder) and Mercury's cyan glint (right) — the other two bodies
    for k in range(4): put(12+k,52+k%2, GOLD)
    for k in range(4): put(49-k,52+k%2, CYAN); put(52,40,CYAN); put(11,40,GOLD)
    # robe — deep violet shadow
    robe=VIOL_D; robe_sh=shade(robe,0.4)
    rect(8,58,55,79, robe)
    for x in range(8,56):
        if x<13 or x>50: rect(x,58,x,60,VOID)
    rect(20,57,44,60, robe_sh)
    for k in range(8): put(32-k,57+k, robe_sh); put(32+k,57+k, robe_sh)
    rect(30,58,34,72, shade(robe,0.25))
    # a high shadow collar
    for x in range(20,45): put(x, 56-abs(x-32)//3, SHADOW)
    # neck + face (in shadow)
    rect(28,47,36,57, shade(SKIN,0.25))
    ell(cx,cy,12,16, SKIN)
    for y in range(int(cy-16),int(cy+17)):                 # shadow falls across the face
        for x in range(int(cx-12),int(cx+13)):
            i=y*LW+x
            if 0<=i<LW*LH and drawn[i] and g[i]==SKIN:
                t=(y-(cy-16))/32.0
                g[i]=mix(SKIN, SHADOW, 0.35+0.5*t)
    # the veil — a translucent violet shadow over the lower face
    for y in range(cy+2, cy+16):
        for x in range(cx-11,cx+12):
            if drawn[y*LW+x]: soft(x,y, SHADOW, 0.45)
    # a single witness-eye (the other in shadow)
    ell(cx-4,cy-2,3,2,(20,16,30)); put(cx-4,cy-2,EYE); put(cx-5,cy-3,(255,255,255))
    soft(cx+4,cy-2, SHADOW_D, 0.6)                          # right eye lost to shadow
    # the crown — three points (the three bodies), the center violet (her), gold left, cyan right
    rect(cx-9,cy-16,cx+9,cy-16, shade(VIOL,0.2))           # circlet band
    put(cx-8,cy-19,GOLD); put(cx-8,cy-20,GOLD)             # King point
    put(cx,cy-21,VIOL); put(cx,cy-22,(220,205,255)); put(cx,cy-23,VIOL)  # Queen point (tall, center)
    put(cx+8,cy-19,CYAN); put(cx+8,cy-20,CYAN)             # Mercury point
    return finish(g, drawn)


PORTRAITS = {"gravity": portrait_aether, "lattice": portrait_leech, "survival": portrait_survival, "regent": portrait_shadow_queen}

import sys
if __name__=="__main__" and len(sys.argv)>1 and sys.argv[1]=="--preview":
    byname={m["name"]:m for m in R["members"]}
    targets = sys.argv[2:] or [R["members"][0]["name"]]
    for nm in targets:
        m=byname[nm]; fn=PORTRAITS.get(m.get("domain"), portrait_aether); px=fn(m)
        tiff(ROOT/f"_preview_{slug(nm)}.tiff", W,H,px); png(ROOT/f"_preview_{slug(nm)}.png", W,H,px)
        print("preview written:", nm)
else:
    for m in R["members"]:
        fn=PORTRAITS.get(m.get("domain"), portrait_aether)
        tiff(AG/f"{slug(m['name'])}.tiff", W, H, fn(m))
        print(f"carbon badge -> agents/{slug(m['name'])}.tiff  ({m['name']})")
