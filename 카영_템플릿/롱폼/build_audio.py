import json, subprocess, os, html
KEY=open('/mnt/user-data/uploads/CafeInEnglish_Claude/CafeInEnglish_Claude/secrets/azure_tts.txt').read().split()[0]
def cora(text,out,rate='-6%'):
    if os.path.exists(out): return
    s=f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='en-US-CoraMultilingualNeural'><lang xml:lang='en-US'><prosody rate='{rate}'>{html.escape(text)}</prosody></lang></voice></speak>"
    subprocess.run(['curl','-sS','-m','60','-X','POST','https://koreacentral.tts.speech.microsoft.com/cognitiveservices/v1','-H',f'Ocp-Apim-Subscription-Key: {KEY}','-H','Content-Type: application/ssml+xml','-H','X-Microsoft-OutputFormat: audio-48khz-192kbitrate-mono-mp3','-H','User-Agent: cafein','--data-binary',s,'-o',out],check=True)
def norm(i,o): subprocess.run(['ffmpeg','-v','error','-y','-i',i,'-af','loudnorm=I=-16:TP=-1.5,aresample=48000','-ac','1',o],check=True)
if __name__=='__main__':
    os.makedirs('en',exist_ok=True); os.makedirs('nk',exist_ok=True); os.makedirs('N',exist_ok=True)
    chunks=json.load(open('chunks.json'))
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','0.35','sil.wav'],check=True)
    keys=[]
    for k,i,lang,t in chunks:
        if k not in keys: keys.append(k)
    for k in keys:
        parts=[]
        for kk,i,lang,t in chunks:
            if kk!=k: continue
            src=f'na/{k}_{i}.mp3' if lang=='ko' else f'en/{k}_{i}.mp3'
            if lang=='en': cora(t,src)
            w=f'nk/{k}_{i}.wav'; norm(src,w)
            if parts: parts.append('sil.wav')
            parts.append(w)
        open('l.txt','w').write(''.join(f"file '{p}'\n" for p in parts))
        subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','l.txt','-ac','1','-b:a','192k',f'N/{k}.mp3'],check=True)
        print(k, subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'N/{k}.mp3']).decode().strip())
