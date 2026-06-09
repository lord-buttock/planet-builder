"""
planet_gen.py — Server-side planet generator.

Pipeline:
  1. Generate 2048×1024 PBR textures (numpy / Pillow)
  2. Call Blender headlessly to:
       a) Build displaced sphere with real terrain geometry
       b) Export .glb for Three.js interactive viewer
       c) Render cinematic .png preview (Eevee)
  3. Return URLs for all assets

If Blender is unavailable the function returns texture URLs only and
the frontend falls back to its GLSL shader renderer.
"""

import os, hashlib, subprocess, shutil, json
import numpy as np
from scipy import ndimage
from PIL import Image

W, H       = 2048, 1024
NOISE_TILE = 256
BLENDER_BIN = shutil.which('blender') or shutil.which('blender3') or '/usr/bin/blender'
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'blender_planet.py')

ATMO = {
    'rocky':[.40,.55,1.00],'watery / ocean':[.20,.50,1.00],
    'icy':[.65,.82,1.00],'volcanic / lava':[1.00,.32,.08],
    'desert / sandy':[.85,.65,.35],'forest / jungle':[.35,.72,.42],
    'gas giant':[.62,.50,.85],'toxic / acid':[.42,.82,.20],
    'crystal':[.62,.42,1.00],
}

RAMPS = {
    'rocky':[(0.00,(28,18,12)),(0.18,(65,45,30)),(0.38,(95,70,48)),(0.55,(120,90,62)),(0.70,(145,115,82)),(0.83,(175,148,118)),(0.92,(205,190,170)),(1.00,(238,228,218))],
    'watery / ocean':[(0.00,(8,22,88)),(0.20,(14,42,136)),(0.36,(22,62,158)),(0.44,(32,85,165)),(0.49,(195,178,105)),(0.54,(80,135,58)),(0.68,(55,108,42)),(0.80,(70,82,60)),(0.90,(120,118,112)),(1.00,(242,242,255))],
    'icy':[(0.00,(28,58,138)),(0.22,(58,105,195)),(0.40,(128,168,218)),(0.58,(185,210,232)),(0.75,(215,230,245)),(0.88,(232,242,252)),(1.00,(248,252,255))],
    'volcanic / lava':[(0.00,(255,160,0)),(0.08,(240,80,0)),(0.18,(180,40,0)),(0.32,(100,28,8)),(0.48,(52,22,12)),(0.62,(38,18,10)),(0.75,(48,40,32)),(0.88,(65,58,52)),(1.00,(82,72,68))],
    'desert / sandy':[(0.00,(55,28,8)),(0.18,(105,62,22)),(0.35,(162,105,45)),(0.52,(205,158,72)),(0.68,(222,178,98)),(0.82,(200,155,88)),(0.92,(165,118,72)),(1.00,(138,95,58))],
    'forest / jungle':[(0.00,(14,45,25)),(0.22,(18,72,32)),(0.42,(24,100,40)),(0.60,(30,118,48)),(0.74,(35,100,42)),(0.84,(42,72,38)),(0.92,(62,72,58)),(1.00,(205,215,210))],
    'gas giant':[(0.00,(188,148,118)),(0.15,(165,128,148)),(0.30,(148,128,175)),(0.45,(162,145,162)),(0.60,(175,162,145)),(0.75,(188,172,138)),(0.88,(200,188,165)),(1.00,(218,210,200))],
    'toxic / acid':[(0.00,(28,88,12)),(0.20,(38,118,18)),(0.38,(48,148,22)),(0.55,(60,162,28)),(0.70,(42,128,20)),(0.82,(32,98,15)),(0.92,(28,78,12)),(1.00,(55,88,32))],
    'crystal':[(0.00,(38,18,115)),(0.18,(58,32,158)),(0.35,(88,55,198)),(0.52,(118,82,225)),(0.68,(148,115,238)),(0.82,(188,158,252)),(0.92,(218,200,255)),(1.00,(245,238,255))],
}

MAIN_COLOURS = {'deep crimson red':(160,30,30),'vivid orange':(220,95,20),'golden yellow':(200,175,40),'lush green':(40,130,50),'ocean blue':(30,90,180),'pale icy white':(210,225,240),'dark ash grey':(70,75,80),'sandy tan-brown':(185,155,90),'vivid purple':(110,40,180),'toxic neon green':(60,200,55),'midnight black':(25,25,35)}
SPECIAL_COLOURS = {'bright cyan':(0,230,230),'electric blue':(40,110,255),'glowing lime green':(100,255,60),'golden yellow':(255,205,0),'vivid purple':(190,55,255),'hot pink':(255,60,155),'deep red':(210,20,20),'shimmering silver':(195,205,215)}

def _noise_tile(seed):
    rng = np.random.RandomState(seed%(2**31))
    s = rng.random((NOISE_TILE//8,NOISE_TILE//8)).astype(np.float32)
    b = ndimage.zoom(s,8,order=3,mode='wrap')
    return b[:NOISE_TILE,:NOISE_TILE]

def _sample(tile,U,V):
    u=(U%1.0)*(NOISE_TILE-1); v=(V%1.0)*(NOISE_TILE-1)
    return ndimage.map_coordinates(tile,[v,u],order=1,mode='wrap').astype(np.float32)

def fbm_tri(NX,NY,NZ,scale,seed,octaves=7):
    result,amp=np.zeros(NX.shape,np.float32),0.5
    rot=np.array([[1.6,1.2],[-1.2,1.6]],np.float32)
    tyz=[_noise_tile(seed+i*997) for i in range(octaves)]
    txz=[_noise_tile(seed+i*997+1000) for i in range(octaves)]
    txy=[_noise_tile(seed+i*997+2000) for i in range(octaves)]
    yu,yv=NY.copy(),NZ.copy(); xu,xv=NX.copy(),NZ.copy(); pu,pv=NX.copy(),NY.copy()
    for i in range(octaves):
        s=scale*(2.0**i)
        nyz=_sample(tyz[i],yu*s,yv*s); nxz=_sample(txz[i],xu*s,xv*s); nxy=_sample(txy[i],pu*s,pv*s)
        wx,wy,wz=np.abs(NX)**6,np.abs(NY)**6,np.abs(NZ)**6; ws=wx+wy+wz+1e-6
        result+=(nyz*(wx/ws)+nxz*(wy/ws)+nxy*(wz/ws))*amp; amp*=0.5
        yu,yv=rot[0,0]*yu+rot[0,1]*yv,rot[1,0]*yu+rot[1,1]*yv
        xu,xv=rot[0,0]*xu+rot[0,1]*xv,rot[1,0]*xu+rot[1,1]*xv
        pu,pv=rot[0,0]*pu+rot[0,1]*pv,rot[1,0]*pu+rot[1,1]*pv
    mn,mx=result.min(),result.max(); return (result-mn)/(mx-mn+1e-8)

def domain_warp(NX,NY,NZ,seed,strength=0.38):
    wx=fbm_tri(NX,NY,NZ,1.8,seed+500,4)-0.5; wy=fbm_tri(NX,NY,NZ,1.8,seed+600,4)-0.5; wz=fbm_tri(NX,NY,NZ,1.8,seed+700,4)-0.5
    return np.clip(NX+wx*strength,-1,1),np.clip(NY+wy*strength,-1,1),np.clip(NZ+wz*strength,-1,1)

def sample_ramp(ramp,h):
    R,G,B=np.zeros_like(h),np.zeros_like(h),np.zeros_like(h)
    for i in range(len(ramp)-1):
        lh,lc=ramp[i]; hh,hc=ramp[i+1]; mask=(h>=lh)&(h<hh); t=np.where(mask,(h-lh)/max(hh-lh,1e-6),0.0)
        R=np.where(mask,lc[0]+t*(hc[0]-lc[0]),R); G=np.where(mask,lc[1]+t*(hc[1]-lc[1]),G); B=np.where(mask,lc[2]+t*(hc[2]-lc[2]),B)
    R=np.where(h>=ramp[-1][0],ramp[-1][1][0],R); G=np.where(h>=ramp[-1][0],ramp[-1][1][1],G); B=np.where(h>=ramp[-1][0],ramp[-1][1][2],B)
    return R,G,B

def parse_sc(s):
    if s in SPECIAL_COLOURS: return SPECIAL_COLOURS[s]
    s=s.lower()
    if 'cyan' in s or 'teal' in s: return (0,220,220)
    if 'blue' in s: return (40,110,255)
    if 'green' in s: return (100,255,60)
    if 'gold' in s or 'yellow' in s: return (255,205,0)
    if 'purple' in s or 'violet' in s: return (190,55,255)
    if 'pink' in s: return (255,60,155)
    if 'red' in s: return (230,40,40)
    if 'orange' in s: return (255,130,0)
    return (180,180,255)

def spec_h(t,h):
    if t=='watery / ocean': return np.where(h<0.45,0.85,np.where(h<0.50,0.30,0.04))
    if t=='icy': return np.clip(0.5+h*0.4,0,1)
    if t=='volcanic / lava': return np.where(h<0.2,0.6,0.05)
    if t=='crystal': return np.clip(0.3+h*0.5,0,1)
    if t=='toxic / acid': return np.where(h<0.3,0.45,0.06)
    return np.full(h.shape,0.04)


def generate_planet_textures(params, out_dir):
    name        = params.get('name','unknown')
    ptype       = params.get('type','rocky')
    main_col    = params.get('mainColour','')
    special_col = params.get('specialColour','')
    has_special = bool(params.get('special',''))
    clouds_str  = params.get('clouds','')
    extreme     = params.get('extreme',[])
    light       = params.get('light','')
    glow        = params.get('glow','')

    seed = int(hashlib.md5(name.encode()).hexdigest()[:8],16)%(2**31)

    lon=np.linspace(0,2*np.pi,W,endpoint=False,dtype=np.float32)
    lat=np.linspace(0,np.pi,H,endpoint=True,dtype=np.float32)
    LON,LAT=np.meshgrid(lon,lat)
    NX=(np.sin(LAT)*np.cos(LON)).astype(np.float32)
    NY=np.cos(LAT).astype(np.float32)
    NZ=(np.sin(LAT)*np.sin(LON)).astype(np.float32)

    if ptype=='gas giant':
        warp=fbm_tri(NX,NY,NZ,3.0,seed+300,3)*0.18
        height=np.clip(np.clip(LAT/np.pi+warp,0,1)*0.4+fbm_tri(NX,NY,NZ,8.0,seed,4)*0.7,0,1)
    else:
        wNX,wNY,wNZ=domain_warp(NX,NY,NZ,seed,0.42)
        height=np.clip(fbm_tri(wNX,wNY,wNZ,2.2,seed,6)*0.60+fbm_tri(NX,NY,NZ,9.0,seed+33,5)*0.28+fbm_tri(NX,NY,NZ,22.0,seed+77,4)*0.12,0,1)
        if ptype in ('icy','watery / ocean'):
            pole=np.abs(NY); ice=np.clip((pole-0.60)/0.25,0,1); height=height*(1-ice)+0.94*ice

    R,G,B=sample_ramp(RAMPS.get(ptype,RAMPS['rocky']),height)
    mc=MAIN_COLOURS.get(main_col)
    if mc:
        bl=np.clip(1.0-np.abs(height-0.55)/0.45,0,1)*0.35
        R,G,B=R*(1-bl)+mc[0]*bl,G*(1-bl)+mc[1]*bl,B*(1-bl)+mc[2]*bl
    if has_special:
        sc=parse_sc(special_col); vn=fbm_tri(NX,NY,NZ,5.5,seed+9999,5)
        vm=np.clip(1.0-np.abs(vn-0.5)/0.055,0,1)**3
        R,G,B=R*(1-vm)+sc[0]*vm,G*(1-vm)+sc[1]*vm,B*(1-vm)+sc[2]*vm
    if ptype=='volcanic / lava':
        gm=np.clip(1.0-height/0.35,0,1); R,G=np.clip(R+80*gm,0,255),np.clip(G+15*gm,0,255)

    col_img=Image.fromarray(np.stack([np.clip(R,0,255).astype(np.uint8),np.clip(G,0,255).astype(np.uint8),np.clip(B,0,255).astype(np.uint8)],axis=-1),'RGB')
    st=6.0; dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*st; dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*st; ln=np.sqrt(dx**2+dy**2+1.0)
    nor_img=Image.fromarray(np.stack([((-dx/ln*0.5+0.5)*255).clip(0,255).astype(np.uint8),((-dy/ln*0.5+0.5)*255).clip(0,255).astype(np.uint8),((1/ln*0.5+0.5)*255).clip(0,255).astype(np.uint8)],axis=-1),'RGB')
    spec_img=Image.fromarray((spec_h(ptype,height)*255).clip(0,255).astype(np.uint8),'L')

    cloud_img=None
    if clouds_str and 'no cloud' not in clouds_str:
        cn=fbm_tri(NX,NY,NZ,4.2,seed+4000,5); ca=np.clip((cn-0.52)/0.30,0,1)**2
        op=0.80 if 'thick' in clouds_str else 0.65 if 'storm' in clouds_str else 0.50
        ca_arr=(ca*op*255).clip(0,255).astype(np.uint8); cw=np.full_like(ca_arr,245)
        cloud_img=Image.fromarray(np.stack([cw,cw,cw,ca_arr],axis=-1),'RGBA')

    safe=''.join(c if c.isalnum() else '_' for c in name)[:32]
    uid=hashlib.md5(f'{name}{ptype}{main_col}'.encode()).hexdigest()[:8]
    pfx=f'{safe}_{uid}'

    def save(img,suffix):
        fname=f'{pfx}_{suffix}.png'
        img.save(os.path.join(out_dir,fname),'PNG',optimize=True)
        return f'/static/textures/{fname}'

    result={'color':save(col_img,'color'),'normal':save(nor_img,'normal'),'specular':save(spec_img.convert('RGB'),'spec')}
    cloud_url=None
    if cloud_img: cloud_url=save(cloud_img,'cloud'); result['cloud']=cloud_url

    # ── Blender stage ──────────────────────────────────────────────────────────
    result['blender_available']=False
    blender_exe=BLENDER_BIN if os.path.isfile(BLENDER_BIN) else shutil.which('blender')
    if blender_exe and os.path.isfile(SCRIPT_PATH):
        glb_path=os.path.join(out_dir,f'{pfx}.glb')
        png_path=os.path.join(out_dir,f'{pfx}_render.png')
        bp={
            'type':ptype,
            'color_tex': os.path.join(out_dir,os.path.basename(result['color'])),
            'normal_tex':os.path.join(out_dir,os.path.basename(result['normal'])),
            'spec_tex':  os.path.join(out_dir,os.path.basename(result['specular'])),
            'cloud_tex': os.path.join(out_dir,os.path.basename(cloud_url)) if cloud_url else None,
            'output_glb':glb_path,'output_png':png_path,
            'atmo_color':ATMO.get(ptype,[0.4,0.55,1.0]),
            'has_rings':'enormous planetary rings' in extreme,
            'is_glowing':bool(glow) or 'glowing' in light.lower(),
        }
        try:
            proc=subprocess.run(
                [blender_exe,'--background','--python',SCRIPT_PATH,'--',json.dumps(bp)],
                timeout=120,capture_output=True,text=True
            )
            if proc.returncode==0 and os.path.isfile(glb_path):
                result['glb']=f'/static/textures/{pfx}.glb'
                result['render']=f'/static/textures/{pfx}_render.png'
                result['blender_available']=True
                print('Blender: OK')
            else:
                print('Blender stderr:',proc.stderr[-800:])
        except subprocess.TimeoutExpired:
            print('Blender: timed out')
        except Exception as e:
            print(f'Blender: {e}')

    return {'textures':result,'seed':seed}
