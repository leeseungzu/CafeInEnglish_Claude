import subprocess,re,sys,json
D='/tmp/claude-0/-home-claude/867aec65-8c7b-57fa-a377-537e93906e02/scratchpad/hy/'
fs=re.findall(r"file '(.+)'",open(D+'list.txt').read())
def vd(p): return float(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=duration','-of','csv=p=0',p]))
inp=[];fl='';cat='';off=[];t=0
for i,f in enumerate(fs):
    d=vd(f); inp+=['-i',f]; off.append((f.split('/')[-1],round(t,3),round(d,3))); t+=d
    fl+=f'[{i}:v]fps=30,format=yuv420p,setsar=1[v{i}];[{i}:a]aresample=48000,apad,atrim=0:{d:.3f}[a{i}];'; cat+=f'[v{i}][a{i}]'
fl+=cat+f'concat=n={len(fs)}:v=1:a=1[v][a]'
json.dump(off,open(D+'offsets.json','w'))
subprocess.run(['ffmpeg','-v','error','-y']+inp+['-filter_complex',fl,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k','-movflags','+faststart',D+'full.mp4'],check=True)
print('total',round(t,2))
