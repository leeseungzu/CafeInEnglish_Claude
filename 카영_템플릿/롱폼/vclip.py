import json,subprocess,numpy as np
D='/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/hy/'
OFFS={'ga':0,'ces':100,'wh':260}; X=0.08; SR=8000
def rd(p,ss,t):
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-ss',f'{ss:.3f}','-t',f'{t:.3f}','-i',p,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout,dtype=np.float32)
for nm,src in [('00_hook','ces'),('1A_raw','ces'),('1B_raw','ces'),('1C_raw','wh'),('1D_raw','ga'),('1E_raw','ga'),('4A_sub','ces'),('4D_sub','ga'),('4E_sub','ga')]:
    j=json.load(open(D+'r/'+nm+'.json')); S=0; res=[]
    for i,(s,e) in enumerate(j['pieces']):
        d=e-s; w=min(2.0,d-0.4); ts=S+(d-w)/2 if i else (d-w)/2
        o=rd(D+'r/'+nm+'.mp4',ts,w); ref=rd(D+src+'.mp4',s-OFFS[src]+(ts-S)-0.3,w+0.6)
        c=np.correlate(ref,o,'valid'); lag=(np.argmax(c)/SR)-0.3
        res.append(round(lag*1000))
        S+=d-X
    print(nm,'lag ms per piece',res)
print('--- detail')
for nm,src in [('1D_raw','ga'),('1C_raw','wh')]:
    j=json.load(open(D+'r/'+nm+'.json')); P=j['pieces']; S=sum(e-s-X for s,e in P[:-1]); s,e=P[-1]
    for off in (0.1,0.5,0.9):
        w=1.2; o=rd(D+'r/'+nm+'.mp4',S+off,w); ref=rd(D+src+'.mp4',s-OFFS[src]+off-0.3,w+0.6)
        c=np.correlate(ref,o,'valid'); print(nm,off,round((np.argmax(c)/SR-0.3)*1000), round(c.max()/np.sqrt((o*o).sum()*(ref*ref).sum()+1e-9),3))
