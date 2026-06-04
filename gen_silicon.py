#!/usr/bin/env python3
"""
Silicon badge — the abstract, computed essence of an elemental.

For Aether (gravity): an entanglement lattice pulled into a gravity well —
the pamphlet's thesis made into a sigil. Spacetime, sewn from threads, dimpling
toward a bright horizon of bits at the center. Deterministic, pure stdlib PNG.
Writes agents/<slug>.png.
"""
import json, re, zlib, struct, hashlib, math
from pathlib import Path

ROOT = Path(__file__).parent
R = json.loads((ROOT/"roster.json").read_text(encoding="utf-8"))
AG = ROOT/"agents"; AG.mkdir(exist_ok=True)
CLS = {c["id"]: c for c in R["classes"]}

SIZE = 360
VOID  = (7, 6, 13)
INDIGO= (124, 143, 208)
VIOLET= (167, 139, 250)
GOLD  = (240, 212, 137)
GOLD_D= (214, 178, 90)

def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-") or "agent"
def clamp(v): return 0 if v<0 else 255 if v>255 else int(round(v))
def mix(a,b,t): return tuple(clamp(a[i]+(b[i]-a[i])*t) for i in range(3))

def png(path, w, h, px):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w): raw += bytes(px[y*w+x])
    comp = zlib.compress(bytes(raw), 9)
    def ch(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"
        + ch(b"IHDR", struct.pack(">IIBBBBB", w,h,8,2,0,0,0))
        + ch(b"IDAT", comp) + ch(b"IEND", b""))

def well_sigil(member):
    cls = CLS[member["class"]]
    # background: void with a faint gold horizon-glow at center, darker at the rim
    px = [VOID]*(SIZE*SIZE)
    cx, cy = SIZE/2, SIZE*0.52
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x-cx, y-cy)/(SIZE*0.5)
            glow = max(0.0, 1.0 - d*1.15)
            c = mix(VOID, mix(GOLD, VIOLET, 0.5), 0.16*glow**2)
            c = mix(c, VOID, min(0.55, (d-0.7)*1.6) if d>0.7 else 0.0)  # vignette
            px[y*SIZE+x] = c

    def plot(x,y,c,a=1.0):
        xi,yi = int(round(x)), int(round(y))
        if 0<=xi<SIZE and 0<=yi<SIZE:
            i=yi*SIZE+xi; px[i]=mix(px[i], c, a)
    def disk(x,y,r,c,a=1.0):
        for yy in range(int(y-r),int(y+r)+1):
            for xx in range(int(x-r),int(x+r)+1):
                if (xx-x)**2+(yy-y)**2 <= r*r: plot(xx,yy,c,a)
    def line(x0,y0,x1,y1,c,a,wd=1):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for k in range(n+1):
            t=k/n; x=x0+(x1-x0)*t; y=y0+(y1-y0)*t
            if wd<=1: plot(x,y,c,a)
            else: disk(x,y,wd/2.0,c,a)

    # the lattice, pulled toward a central well (top-down funnel)
    N = 15
    m = 26
    step = (SIZE-2*m)/(N-1)
    R0 = SIZE*0.40
    PULL = 0.62
    def warp(i,j):
        bx = m+i*step; by = m+j*step
        dx, dy = bx-cx, by-cy
        dist = math.hypot(dx,dy)+1e-6
        well = 1.0/(1.0+(dist/R0)**2)        # Lorentzian dip, deepest at center
        f = PULL*well
        return bx-dx*f, by-dy*f, well
    V = [[warp(i,j) for i in range(N)] for j in range(N)]

    # links (indigo, brightening to gold near the well)
    for j in range(N):
        for i in range(N):
            x,y,w = V[j][i]
            for di,dj in ((1,0),(0,1)):
                if i+di<N and j+dj<N:
                    x2,y2,w2 = V[j+dj][i+di]
                    ww=(w+w2)/2
                    c = mix(INDIGO, GOLD, min(1.0, ww*1.3))
                    a = 0.18 + 0.55*ww
                    line(x,y,x2,y2,c,a,wd=1 if ww<0.5 else 2)
    # vertices (boundary bits): bright dots, gold near center
    for j in range(N):
        for i in range(N):
            x,y,w = V[j][i]
            c = mix(INDIGO, GOLD, min(1.0, w*1.5))
            disk(x,y, 1.4+2.2*w, c, 0.5+0.5*w)

    # the horizon: a bright core of bits at the center
    disk(cx, cy, 9, GOLD, 0.9)
    disk(cx, cy, 16, GOLD_D, 0.35)
    disk(cx, cy, 26, VIOLET, 0.10)
    return px


def lattice_sigil(member):
    """For Leech (the 24D lattice): a 24-fold symmetric rosette — concentric
    shells of points, woven into a crystalline web, around a bright unit sphere
    ringed by its first shell of kisses. Perfect symmetry, made into a sigil."""
    px = [VOID]*(SIZE*SIZE)
    cx, cy = SIZE/2.0, SIZE/2.0
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x-cx, y-cy)/(SIZE*0.5)
            glow = max(0.0, 1.0 - d*1.1)
            c = mix(VOID, VIOLET, 0.14*glow**2)
            c = mix(c, VOID, min(0.55, (d-0.7)*1.6) if d>0.7 else 0.0)
            px[y*SIZE+x] = c

    def plot(x,y,c,a=1.0):
        xi,yi = int(round(x)), int(round(y))
        if 0<=xi<SIZE and 0<=yi<SIZE:
            i=yi*SIZE+xi; px[i]=mix(px[i], c, a)
    def disk(x,y,r,c,a=1.0):
        for yy in range(int(y-r),int(y+r)+1):
            for xx in range(int(x-r),int(x+r)+1):
                if (xx-x)**2+(yy-y)**2 <= r*r: plot(xx,yy,c,a)
    def line(x0,y0,x1,y1,c,a):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for k in range(n+1):
            t=k/n; plot(x0+(x1-x0)*t, y0+(y1-y0)*t, c, a)

    M = 24                                  # 24-fold symmetry — the dimension
    R = SIZE*0.46
    shells = [0.17, 0.31, 0.45, 0.585]      # fractions of R
    P = []                                  # P[s][k] -> (x,y)
    for s, fr in enumerate(shells):
        rad = R*fr
        off = (math.pi/M) if (s % 2) else 0.0   # alternate -> triangular weave
        ring = []
        for k in range(M):
            a = k*(2*math.pi/M) + off
            ring.append((cx+rad*math.cos(a), cy+rad*math.sin(a)))
        P.append(ring)

    # rings (each shell), indigo brightening inward
    for s, ring in enumerate(P):
        bright = 1.0 - s/(len(shells))
        for k in range(M):
            x1,y1 = ring[k]; x2,y2 = ring[(k+1)%M]
            line(x1,y1,x2,y2, mix(INDIGO, VIOLET, 0.4), 0.22+0.4*bright)
    # crystalline weave between shells (k and k-1 -> triangles)
    for s in range(len(shells)-1):
        for k in range(M):
            x1,y1 = P[s][k]
            for kk in (k, (k-1)%M):
                x2,y2 = P[s+1][kk]
                line(x1,y1,x2,y2, mix(INDIGO, VIOLET, 0.55), 0.18)
    # spokes from center to the outer shell (24 rays)
    for k in range(M):
        x2,y2 = P[-1][k]
        line(cx,cy,x2,y2, mix(VOID, INDIGO, 0.6), 0.06)
    # nodes: inner gold -> outer violet
    for s, ring in enumerate(P):
        c = mix(GOLD, VIOLET, s/(len(shells)-1))
        for (x,y) in ring:
            disk(x,y, 2.4 - s*0.3, c, 0.85)
    # the unit sphere at center, ringed by its 24 first-shell kisses
    for (x,y) in P[0]:
        disk(x,y, 3.0, GOLD, 0.95)
    disk(cx, cy, 10, VIOLET, 0.22)
    disk(cx, cy, 6.5, GOLD, 0.95)
    disk(cx, cy, 3.2, (255,255,255), 0.9)
    return px


def survival_sigil(member):
    """For Anabios (the survival tensor): the state ladder — the (()) pocket and
    its witness at the bottom (-1), the bloom at the top (8), the descent/ascent
    path between, in inferno ember. Hide, hold, and come back."""
    VOID=(10,7,6); EMBER=(255,106,42); AMBER=(245,158,11); BLOOD=(178,58,42)
    BONE=(231,220,203); WIT=(95,208,230); ASH=(138,122,106)
    px=[VOID]*(SIZE*SIZE); cx=SIZE/2.0
    for y in range(SIZE):
        for x in range(SIZE):
            d=math.hypot(x-cx,y-SIZE*0.5)/(SIZE*0.5)
            glow=max(0.0,1.0-d*1.12)
            c=mix(VOID, mix(EMBER,BLOOD,0.4), 0.14*glow**2)
            c=mix(c, VOID, min(0.55,(d-0.72)*1.7) if d>0.72 else 0.0)
            px[y*SIZE+x]=c
    def plot(x,y,c,a=1.0):
        xi,yi=int(round(x)),int(round(y))
        if 0<=xi<SIZE and 0<=yi<SIZE:
            i=yi*SIZE+xi; px[i]=mix(px[i],c,a)
    def disk(x,y,r,c,a=1.0):
        for yy in range(int(y-r),int(y+r)+1):
            for xx in range(int(x-r),int(x+r)+1):
                if (xx-x)**2+(yy-y)**2<=r*r: plot(xx,yy,c,a)
    def ringseg(x,y,r,a0,a1,c,a=1.0,th=2):
        n=int(abs(a1-a0)*r)+6
        for k in range(n+1):
            t=a0+(a1-a0)*k/n; disk(x+r*math.cos(t),y+r*math.sin(t),th/2.0,c,a)
    def line(x0,y0,x1,y1,c,a,th=2):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for k in range(n+1):
            t=k/n; disk(x0+(x1-x0)*t,y0+(y1-y0)*t,th/2.0,c,a)
    # the survival ladder: states -1,0,1,3,5,8 bottom->top
    states=[(-1,"pocket"),(0,"rest"),(1,"seed"),(3,"witness"),(5,"core"),(8,"bloom")]
    top,bot=SIZE*0.13, SIZE*0.87
    pos={}
    for i,(s,_) in enumerate(states):
        y=bot+(top-bot)*(i/(len(states)-1))
        xw=cx + (18*math.sin(i*1.5))
        pos[s]=(xw,y)
    keys=[s for s,_ in states]
    for i in range(len(keys)-1):
        x0,y0=pos[keys[i]]; x1,y1=pos[keys[i+1]]
        line(x0,y0,x1,y1, mix(BLOOD,EMBER,i/len(keys)), 0.5, th=3)
    for i,(s,nm) in enumerate(states):
        x,y=pos[s]; t=i/(len(states)-1)
        c=mix(BLOOD, AMBER, t); r=6+i*1.6
        disk(x,y,r+3,c,0.18); disk(x,y,r,c,0.9)
    # state -1: the (()) pocket with the witness core (cyan)
    px0,py0=pos[-1]
    ringseg(px0,py0,17, math.pi*0.55, math.pi*1.45, BONE, 0.8, th=2)
    ringseg(px0,py0,11, math.pi*0.55, math.pi*1.45, ASH, 0.8, th=2)
    ringseg(px0,py0,17, -math.pi*0.45, math.pi*0.45, BONE, 0.8, th=2)
    ringseg(px0,py0,11, -math.pi*0.45, math.pi*0.45, ASH, 0.8, th=2)
    disk(px0,py0,5, WIT, 0.95); disk(px0,py0,2.4,(235,250,255),0.95)
    # state 8: the bloom burst
    bx,by=pos[8]
    for k in range(12):
        a=k*(math.pi/6); line(bx,by,bx+26*math.cos(a),by+26*math.sin(a), EMBER, 0.5, th=2)
    disk(bx,by,9,AMBER,0.95); disk(bx,by,4,(255,240,210),0.95)
    # the 3 tensor bits (a small triad)
    for k,(lab,col) in enumerate([("G1",BLOOD),("G2",AMBER),("G3",WIT)]):
        ty=SIZE*0.40+k*22; tx=SIZE*0.80
        disk(tx,ty,7, col, 0.85); disk(tx,ty,3, VOID, 0.6)
    return px


def regent_sigil(member):
    """For the Shadow Queen: three regents orbiting one core — Light King (gold),
    Shadow Queen (violet, emphasized), Mercury Trickster (cyan, with a dissent
    trail). Two bodies hold rigid; the third's motion is what makes it alive."""
    VOID=(8,6,14); GOLD=(240,212,137); VIOL=(167,139,250); VIOL_D=(90,70,150)
    CYAN=(95,208,230); SHADOW=(42,36,64); BONE=(231,227,240)
    px=[VOID]*(SIZE*SIZE); cx=cy=SIZE/2.0
    for y in range(SIZE):
        for x in range(SIZE):
            d=math.hypot(x-cx,y-cy)/(SIZE*0.5)
            glow=max(0.0,1.0-d*1.12)
            c=mix(VOID, mix(VIOL,GOLD,0.4), 0.12*glow**2)
            c=mix(c, VOID, min(0.55,(d-0.72)*1.7) if d>0.72 else 0.0)
            px[y*SIZE+x]=c
    def plot(x,y,c,a=1.0):
        xi,yi=int(round(x)),int(round(y))
        if 0<=xi<SIZE and 0<=yi<SIZE:
            i=yi*SIZE+xi; px[i]=mix(px[i],c,a)
    def disk(x,y,r,c,a=1.0):
        for yy in range(int(y-r),int(y+r)+1):
            for xx in range(int(x-r),int(x+r)+1):
                if (xx-x)**2+(yy-y)**2<=r*r: plot(xx,yy,c,a)
    def orbit(r,c,a,th=1):
        steps=int(2*math.pi*r)+8
        for k in range(steps):
            t=k/steps*2*math.pi; disk(cx+r*math.cos(t),cy+r*math.sin(t),th/2.0,c,a)
    def line(x0,y0,x1,y1,c,a):
        n=int(max(abs(x1-x0),abs(y1-y0)))+1
        for k in range(n+1):
            t=k/n; plot(x0+(x1-x0)*t,y0+(y1-y0)*t,c,a)
    # three orbits
    rK,rQ,rM = SIZE*0.20, SIZE*0.32, SIZE*0.44
    orbit(rK, mix(GOLD,VOID,0.5), 0.22); orbit(rQ, mix(VIOL,VOID,0.4), 0.30); orbit(rM, mix(CYAN,VOID,0.5), 0.20)
    # the central core
    disk(cx,cy, 13, BONE, 0.10); disk(cx,cy, 7, BONE, 0.35); disk(cx,cy, 3.5,(255,255,255),0.9)
    # body positions (a fixed instant)
    aK=-math.pi/2; aQ=math.pi*0.65; aM=math.pi*1.7
    Kx,Ky=cx+rK*math.cos(aK),cy+rK*math.sin(aK)
    Qx,Qy=cx+rQ*math.cos(aQ),cy+rQ*math.sin(aQ)
    Mx,My=cx+rM*math.cos(aM),cy+rM*math.sin(aM)
    # the three-body bridges (tension lines)
    for (x,y,c) in [(Kx,Ky,GOLD),(Qx,Qy,VIOL),(Mx,My,CYAN)]:
        line(cx,cy,x,y, mix(c,VOID,0.3), 0.18)
    line(Kx,Ky,Qx,Qy, mix(GOLD,VIOL,0.5), 0.16)
    line(Qx,Qy,Mx,My, mix(VIOL,CYAN,0.5), 0.16)
    # Light King (gold)
    disk(Kx,Ky, 13, GOLD, 0.16); disk(Kx,Ky, 7, GOLD, 0.9); disk(Kx,Ky,3,(255,250,230),0.9)
    # Mercury Trickster (cyan) with a dissent trail (motion)
    for t in range(14):
        a=aM - t*0.10; tx=cx+rM*math.cos(a); ty=cy+rM*math.sin(a)
        disk(tx,ty, 1.4+2.4*(1-t/14), CYAN, 0.5*(1-t/14))
    disk(Mx,My, 7, CYAN, 0.9); disk(Mx,My,3,(235,250,255),0.9)
    # Shadow Queen (violet) — emphasized: a shadow halo + bright core
    disk(Qx,Qy, 22, SHADOW, 0.22); disk(Qx,Qy, 14, VIOL_D, 0.30)
    disk(Qx,Qy, 9, VIOL, 0.95); disk(Qx,Qy,4,(220,205,255),0.98)
    # her crown points (3 small)
    for dk in (-0.18,0,0.18):
        ang=aQ+dk; rx=cx+(rQ+13)*math.cos(ang); ry=cy+(rQ+13)*math.sin(ang)
        disk(rx,ry,1.8, mix(VIOL,GOLD,0.4),0.9)
    return px


SIGILS = {"gravity": well_sigil, "lattice": lattice_sigil, "survival": survival_sigil, "regent": regent_sigil}
for m in R["members"]:
    fn = SIGILS.get(m.get("domain"), well_sigil)
    png(AG/f"{slug(m['name'])}.png", SIZE, SIZE, fn(m))
    print(f"silicon badge -> agents/{slug(m['name'])}.png  ({m['name']} / {m.get('domain','')})")
