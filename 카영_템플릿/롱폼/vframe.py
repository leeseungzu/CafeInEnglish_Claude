import json,subprocess,numpy as np,sys
D='/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/hy/'
OFFS={'ga':0,'ces':100,'wh':260}; X=0.08
def fr(p,t,crop=''):
    b=subprocess.run(['ffmpeg','-v','error','-ss',f'{t:.3f}','-i',p,'-frames:v','1','-vf',crop+'scale=192:108','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True).stdout
    return np.frombuffer(b,dtype=np.uint8).astype(float).reshape(108,192)[:70]
for nm,src in [(a,b) for a,b in [x.split(':') for x in sys.argv[1:]]]:
    j=json.load(open(D+'r/'+nm+'.json')); S=0; res=[]
    crop='crop=1671:940:215:0,' if src=='ga' else ''
    for i,(s,e) in enumerate(j['pieces']):
        t=S+(e-s)/2; o=fr(D+'r/'+nm+'.mp4',t)
        errs=[(np.abs(fr(D+src+'.mp4',s-OFFS[src]+(t-S)+k/30,crop)-o).mean(),k) for k in range(-3,4)]
        res.append(min(errs)[1]); S+=e-s-X
    print(nm,'best frame offset per piece',res)
