import json,re
W=[w for w in json.load(open('words.json'))['words'] if w.get('type')=='word']
off=json.load(open('tx_off.json'))
SRC={'a1':'ga','a2':'ces','a3':'wh'}
WS={'ga':[],'ces':[],'wh':[]}
for w in W:
    for n,a,b,o in off:
        if o<=w['start']<o+(b-a)+1:
            WS[SRC[n]].append((a+w['start']-o,a+w['end']-o,re.sub(r"[^a-z0-9$']","",w['text'].lower())))
FILL={'uh','um','mm','mmhmm','hmm'}
def toks(s): return [t for t in (re.sub(r"[^a-z0-9$']","",x.lower()) for x in s.split()) if t]
def find(src,t0,en):
    ws=[w for w in WS[src] if w[0]>=t0-1.5 and w[2] not in FILL]
    tk=toks(en); a=tk[:2]; z=tk[-2:]
    for i in range(len(ws)-1):
        if [ws[i][2],ws[i+1][2]]==a:
            for j in range(i,len(ws)-1):
                if [ws[j][2],ws[j+1][2]]==z: return round(ws[i][0],2),round(ws[j+1][1],2)
    raise Exception(f'nomatch {src} {t0} {en}')
def find2(src,t0,en,first=None,last=None):
    ws=[w for w in WS[src] if w[0]>=t0-1.5 and w[2] not in FILL]
    tk=toks(en); a=first or tk[:2]; z=last or tk[-2:]
    for i in range(len(ws)-1):
        if [ws[i][2],ws[i+1][2]]==a:
            for j in range(i,len(ws)-1):
                if [ws[j][2],ws[j+1][2]]==z: return round(ws[i][0],2),round(ws[j+1][1],2)
    raise Exception(f'nomatch {src} {t0} {en}')
SPEC={
'A':('ces',[(187,"Robots are the legend of childhood dreams.","로봇은 어린 시절 꿈의 전설이에요."),
 (192,"They are our heroes, the hero bots from another world.","우리의 영웅, 다른 세상에서 온 히어로 로봇이죠."),
 (199,"They fill comic books with adventure.","만화책을 모험으로 가득 채우고,"),
 (204,"They protect us from Martians and villains.","화성인과 악당으로부터 우리를 지켜 줘요."),
 (209,"Who can ever forget C-3PO and R2-D2 in Star Wars?","스타워즈의 C-3PO와 R2-D2를 누가 잊을 수 있겠어요?",None,["star","wars"]),
 (215,"They are true companions who accompany us into worlds unknown.","미지의 세계로 함께 떠나는 진정한 동반자예요."),
 (221,"I loved them as a kid, and as a kid at heart, I love them today.","어릴 때도 좋아했고, 마음은 여전히 아이라서 지금도 좋아해요."),
 (230,"But let there be no doubt, robotics is no longer the stuff of dreams.","하지만 분명히 말씀드리면, 로봇은 더 이상 꿈속 이야기가 아니에요."),
 (237,"Robotics is now.","로봇은 바로 지금이에요.")]),
'B':('ces',[(598,"At Hyundai, we have a thought that guides us every day.","현대에는 매일 우리를 이끄는 생각이 하나 있어요."),
 (605,"We don't limit our challenges.","우리는 도전에 한계를 두지 않아요."),
 (608,"We challenge our limits.","우리의 한계에 도전하죠.",["we","ch"],None)]),
'C':('wh',[(306,"So Hyundai Motor entered the US in 1986.","현대차는 1986년 미국에 진출했어요.",None,["us","1986"]),
 (310,"Since then, we have invested over $20 billion, and now support more than 570,000 American jobs across all 50 states.","그 뒤로 200억 달러 넘게 투자했고, 지금은 50개 주에서 미국 일자리 57만 개 이상을 뒷받침하고 있어요.",None,["nation","states"]),
 (322,"Today, I'm pleased to announce an additional $21 billion in new investment over the next four years, our largest US investment ever.","오늘, 앞으로 4년간 210억 달러를 추가로 투자한다고 발표하게 되어 기뻐요. 미국 투자로는 사상 최대 규모예요.",None,["invest","ever"])]),
'D':('ga',[(160,"At Hyundai, we don't just invest in technologies and automobiles.","현대는 기술과 자동차에만 투자하지 않아요."),
 (165.5,"We invest first and foremost in relationships.","무엇보다 먼저, 관계에 투자해요."),
 (171,"In the people we work with, our partners, our neighborhoods, our communities.","함께 일하는 사람들, 파트너, 이웃, 그리고 지역 사회에요."),
 (177,"We don't just come to build a plant.","우리는 공장만 지으러 오지 않아요."),
 (181,"We come to put down roots.","뿌리를 내리러 와요."),
 (208,"We believe that collaboration makes us not just a company operating here, but a member of the Savannah and Georgia community, like family.","이런 협력이 우리를 이곳의 회사가 아니라, 서배너와 조지아 지역 사회의 가족 같은 일원으로 만들어 준다고 믿어요.",["we","believe"],None),
 (221,"We come to stay, to invest, and to grow together.","우리는 머물고, 투자하고, 함께 성장하러 와요."),
 (227,"That is why we are here in Savannah.","그래서 우리가 여기 서배너에 있는 거예요.")]),
'E':('ga',[(434.5,"Every vehicle that leaves this plant will bear your imprint in safety and in comfort.","이 공장을 떠나는 모든 차에는, 안전과 편안함 속에 여러분의 손길이 담길 거예요."),
 (444,"They will carry children to school and parents to work,","그 차들은 아이들을 학교로, 부모를 직장으로 데려다주고,",None,["to","work"]),
 (449,"and they will take families and friends on new adventures.","가족과 친구를 새로운 모험으로 이끌 거예요."),
 (455.5,"For everyone who works at this facility, I hope that fact gives you the same pride that it gives me and indeed all of us.","이곳에서 일하는 모든 분이, 저와 우리 모두가 느끼는 것과 같은 자부심을 느끼길 바라요.",None,["of","us"]),
 (468.5,"You are contributing to something that is, like every vehicle, greater than the sum of its parts.","여러분은 모든 차가 그렇듯, 부분의 합보다 더 큰 무언가에 기여하고 있어요."),
 (477.5,"You are Hyundai, and we are all grateful for that.","여러분이 바로 현대예요. 우리 모두 그 점에 감사해요."),
 (481.5,"Thank you very much.","정말 감사합니다.")]),
}
def build():
    out={}
    for k,(src,lst) in SPEC.items():
        cs=[]
        for it in lst:
            t0,en,ko=it[:3]; f=it[3] if len(it)>3 else None; l=it[4] if len(it)>4 else None
            a,b=find2(src,t0,en,f,l); cs.append((a,b,en,ko))
        out[k]=(src,cs)
    return out
if __name__=='__main__':
    o=build(); json.dump(o,open('cues.json','w'),ensure_ascii=False)
    for k,(s,cs) in o.items():
        print(k,s); [print('  %.2f-%.2f %s'%(a,b,e[:60])) for a,b,e,_ in cs]
