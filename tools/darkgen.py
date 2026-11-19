"""다크 모드 CSS 자동 생성 (2026-11-19)
style.css의 색을 속성별(글자·배경·선)로 토스 다크 톤에 맞춰 바꾼 규칙을 html.dark 아래에 만들어요.
build.py가 불러 쓰고, 손으로 맞출 부분은 assets/dark-fix.css 에 적어요."""
import re, colorsys
def hx(c):
    c=c.lstrip('#'); c=''.join(ch*2 for ch in c) if len(c)==3 else c
    return tuple(int(c[i:i+2],16) for i in (0,2,4))
def lum(rgb): r,g,b=[x/255 for x in rgb]; return 0.2126*r+0.7152*g+0.0722*b
def h(rgb): return '#%02X%02X%02X'%tuple(max(0,min(255,round(x))) for x in rgb)
BG={'FFFFFF':'#1C1C21','F2F4F6':'#26262D','F7F8FA':'#26262D','F9FAFB':'#222228','FAF8F5':'#101012','F4EEE4':'#16161A','FBF7F2':'#1C1C21',
    'EEF0F2':'#2A2A31','E5E8EB':'#2A2A31','191F28':'#2C2C34','2A1A12':'#4A3226','2B1D14':'#4A3226','000000':'#000000','191919':'#2C2C34','333D4B':'#3A3A42'}
TX={'191F28':'#ECECEF','2A1A12':'#ECECEF','2B1D14':'#ECECEF','333D4B':'#D6D9DE','111111':'#ECECEF','000000':'#ECECEF','191919':'#ECECEF','333333':'#D6D9DE',
    '4E5968':'#B0B8C1','6B7684':'#9AA1AB','8B95A1':'#7E8590','B0B8C1':'#5F6570','FFFFFF':'#FFFFFF','555555':'#B0B8C1','6E5E54':'#A99C93'}
LN={'2A1A12':'#5A5A63','191F28':'#5A5A63','2B1D14':'#5A5A63','E5E8EB':'#2C2C33','EEF0F2':'#2C2C33','ECE6DD':'#2C2C33','F2F4F6':'#26262C','C9CFD6':'#3A3A42','EFE6DA':'#2C2C33','D9CFC2':'#3A3A42','FFFFFF':'#1C1C21'}
def gen_bg(rgb):
    L=lum(rgb)
    if colorsys.rgb_to_hls(*[x/255 for x in rgb])[1]>0.86:
        hh,ll,ss=colorsys.rgb_to_hls(*[x/255 for x in rgb]); r,g,b=colorsys.hls_to_rgb(hh,0.14,min(ss,0.35)); return h((r*255,g*255,b*255))
    return None
def gen_tx(rgb):
    if lum(rgb)<0.25:
        hh,ll,ss=colorsys.rgb_to_hls(*[x/255 for x in rgb]); r,g,b=colorsys.hls_to_rgb(hh,0.88,min(ss,0.4)); return h((r*255,g*255,b*255))
    return None
def mapcol(c,kind):
    k=h(hx(c))[1:]; M={'bg':BG,'tx':TX,'ln':LN}[kind]
    if k in M: return M[k]
    return {'bg':gen_bg,'tx':gen_tx,'ln':gen_bg}[kind](hx(c))
def maprgba(m,kind):
    r,g,b=int(m.group(1)),int(m.group(2)),int(m.group(3)); a=m.group(4)
    if kind!='tx' and lum((r,g,b))>0.85: return f'rgba(28,28,33,{a})' if a else '#1C1C21'
    if kind=='tx' and lum((r,g,b))<0.25: return f'rgba(236,236,239,{a})' if a else '#ECECEF'
    return None
def kind_of(p):
    p=p.strip().lower()
    if p in('color','fill','stroke','caret-color','-webkit-text-fill-color','text-decoration-color'): return 'tx'
    if p.startswith('border') or p.startswith('outline') or p=='column-rule': return 'ln'
    if p.startswith('background'): return 'bg'
    if p in('--bg','--card'): return 'bg'
    if p in('--text','--muted','--accent'): return 'tx'
    if p in('--line','--accent-soft'): return 'ln'
    if p.startswith('--'): return 'var'
    return None
def bright_bg(body):
    if re.search(r'background(?:-color)?\s*:\s*var\(--lime\)',body): return True
    for m in re.finditer(r'background(?:-color)?\s*:\s*([^;]+)',body):
        for c in re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b',m.group(1)):
            hh,ll,ss=colorsys.rgb_to_hls(*[x/255 for x in hx(c)])
            if ss>0.45 and 0.45<ll<0.86: return True
    return False
def solid_light(body):
    if re.search(r'background(?:-color)?\s*:\s*var\(--lime\)\s*(!important)?\s*(;|$)',body): return True
    m=re.search(r'background(?:-color)?\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\s*(!important)?\s*(;|$)',body)
    if not m: return False
    hh,ll,ss=colorsys.rgb_to_hls(*[x/255 for x in hx(m.group(1))])
    return ss>0.45 and lum(hx(m.group(1)))>0.6
def conv_decls(body):
    out=[];bb=bright_bg(body);any_ch=False;keep=[]
    for d in re.split(r';(?![^(]*\))',body):
        if ':' not in d: continue
        p,v=d.split(':',1); kd=kind_of(p)
        if not kd: continue
        if kd=='var':
            cs=re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b',v)
            if not cs: continue
            kd='tx' if lum(hx(cs[0]))<0.5 else 'bg'
        if kd=='tx' and bb: keep.append(f"{p.strip()}:{v.strip().replace('var(--text)','#2A1A12')}"); continue
        imp='!important' if '!important' in v else ''; v0=v.replace('!important','')
        ch=[False]
        def rh(m):
            r=mapcol(m.group(0),kd)
            if r and r.upper()!=h(hx(m.group(0))): ch[0]=True; return r
            return m.group(0)
        def rr(m):
            r=maprgba(m,kd)
            if r: ch[0]=True; return r
            return m.group(0)
        if kd=='bg' and 'gradient' in v0 and 'transparent' in v0 and re.search(r'CDEB5B|var\(--lime\)',v0,re.I):
            nv = re.sub(r'#CDEB5B|var\(--lime\)', 'rgba(205,235,91,.42)', v0, flags=re.I).strip(); out.append(p.strip() + ':' + nv + imp); any_ch=True; continue
        if kd=='bg' and re.search(r'var\(--(text|accent)\)',v0):
            out.append(p.strip() + ':' + re.sub(r'var\(--(text|accent)\)','#3A3A43',v0).strip() + imp); any_ch=True; continue
        if kd=='tx' and re.search(r'var\(--(bg|card)\)',v0):
            out.append(p.strip() + ':' + re.sub(r'var\(--(bg|card)\)','#ECECEF',v0).strip() + imp); any_ch=True; continue
        v1=re.sub(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b',rh,v0)
        v1=re.sub(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)',rr,v1)
        if v1.strip()=='#fff' or v1.strip().lower() in('white',):
            pass
        if re.fullmatch(r'\s*white\s*',v0,re.I) and kd=='bg': v1='#1C1C21'; ch[0]=True
        if re.fullmatch(r'\s*white\s*',v0,re.I) and kd=='ln': v1='#1C1C21'; ch[0]=True
        if ch[0]: out.append(f'{p.strip()}:{v1.strip()}{imp}'); any_ch=True
        elif re.search(r'#|rgb|var\(|white|black|transparent|none',v0,re.I): keep.append(f'{p.strip()}:{v1.strip()}{imp}')
    if solid_light(body) and not re.search(r'(^|;)\s*color\s*:',body): out.append('color:#191F28')
    return ';'.join(out+keep)
def pref(sel):
    parts=[]
    def sp(x):
        out=[];d=0;cur=''
        for ch in x:
            if ch in '([':d+=1
            elif ch in ')]':d-=1
            if ch==',' and d==0: out.append(cur);cur=''
            else: cur+=ch
        out.append(cur);return out
    for s in sp(sel):
        s=s.strip()
        if not s: continue
        if s.startswith(':root'): parts.append('html.dark'); continue
        if s.startswith('html.'): parts.append('html.dark'+s[4:]); continue
        if s.startswith('html') and (len(s)==4 or s[4] in ' >:[.'): parts.append('html.dark'+s[4:]); continue
        if s.startswith('body'): parts.append('html.dark '+s); continue
        parts.append('html.dark '+s)
    return ','.join(parts)
def walk(css):
    out=[];i=0;n=len(css)
    while i<n:
        j=css.find('{',i)
        if j<0: break
        head=css[i:j].strip()
        if head.startswith('@media') or head.startswith('@supports'):
            depth=1;k=j+1
            while depth:
                if css[k]=='{':depth+=1
                elif css[k]=='}':depth-=1
                k+=1
            inner=walk(css[j+1:k-1])
            if inner and 'print' not in head: out.append(head+'{'+inner+'}')
            i=k;continue
        if head.startswith('@'):
            depth=1;k=j+1
            while depth:
                if css[k]=='{':depth+=1
                elif css[k]=='}':depth-=1
                k+=1
            i=k;continue
        k=css.find('}',j); body=css[j+1:k]
        cd=conv_decls(body)
        if cd and re.search(r'seg|tab|toggle|switch',head) and re.search(r'\.on|\[aria-selected|\.active|checked',head):
            cd=re.sub(r'(background(?:-color)?:)#1C1C21',r'\1#3A3A43',cd)
        if cd and head: out.append(pref(head)+'{'+cd+'}')
        i=k+1
    return ''.join(out)


def make_dark(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return ('html.dark{color-scheme:dark}html.dark body{background:#101012;color:#ECECEF}' + walk(css))
