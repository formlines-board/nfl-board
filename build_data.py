"""Builds data.js for the NFL 2026 consensus app.
Run from the folder containing nfl_2026_almanac_summary.md and betql_lines.json.
Requires: pip install pandas pyarrow markdown

Stat definitions
- Sample filter ("filtered" stats): pre-snap win probability between 10% and 90%; kneels/spikes excluded.
- Turnovers (interceptions, lost fumbles) are removed from EPA by default; 'f_to'/'r_to' keep them in. Success rate always includes them.
- Dropback EPA: plays with qb_dropback = 1 (passes, sacks, scrambles). Rush EPA: designed runs only.
- Explosive rate: passes of 15+ yards or runs of 10+ yards, as a share of plays.
- Pace: seconds per offensive snap = drive possession time / drive plays.
- Neutral pace: seconds elapsed between consecutive offensive snaps in the same drive, counted only when the
  earlier snap had win probability 35-65%. Gaps over 60s (timeouts, breaks) are dropped.
Raw (unfiltered) versions are also produced so the app can toggle.
"""
import pandas as pd, numpy as np, re, json, urllib.request, os, datetime
PBP="https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet"
SCH="https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
for url,fn in [(PBP,'pbp2026.parquet'),(SCH,'games.csv')]:
    try: urllib.request.urlretrieve(url,fn)
    except Exception as e: print("download failed",fn,e)
d=pd.read_parquet('pbp2026.parquet'); g=pd.read_csv('games.csv'); g=g[g.season==2026]
bq=json.load(open('betql_lines.json')) if os.path.exists('betql_lines.json') else {}
base=d[((d['pass']==1)|(d['rush']==1))&d.epa.notna()&d.success.notna()&(d.qb_kneel!=1)&(d.qb_spike!=1)].copy()
base['to']=((base.interception==1)|(base.fumble_lost==1)).astype(int)
base['explosive']=(((base['pass']==1)&(base.yards_gained>=15))|((base.rush==1)&(base.qb_dropback!=1)&(base.yards_gained>=10))).astype(int)
def stats(off,de,no_to=True):
    o=off[off.to==0] if no_to else off; dd=de[de.to==0] if no_to else de
    ob=o[o.qb_dropback==1]; orr=o[(o.rush==1)&(o.qb_dropback!=1)]
    db=dd[dd.qb_dropback==1]; dr=dd[(dd.rush==1)&(dd.qb_dropback!=1)]
    m=lambda s: float(s.mean()) if len(s) else None
    return dict(plays=len(off),sr=m(off.success),opp_sr=m(de.success),epa=m(o.epa),opp_epa=m(dd.epa),
        db_epa=m(ob.epa),rush_epa=m(orr.epa),opp_db_epa=m(db.epa),opp_rush_epa=m(dr.epa),
        expl=m(off.explosive),opp_expl=m(de.explosive))
def neutral_pace(gp,team):
    t=gp[(gp.posteam==team)].sort_values('play_id')
    secs=[]
    for drive,dp in t.groupby('drive'):
        dp=dp.sort_values('play_id')
        for a,b in zip(dp.itertuples(),dp.iloc[1:].itertuples()):
            if pd.notna(a.wp) and 0.35<=a.wp<=0.65:
                gap=a.game_seconds_remaining-b.game_seconds_remaining
                if 0<gap<=60: secs.append(gap)
    return float(np.mean(secs)) if secs else None
rows=[]
for gid,gp in base.groupby('game_id'):
    home,away=gp.home_team.iloc[0],gp.away_team.iloc[0]
    filt=gp[(gp.wp>=0.10)&(gp.wp<=0.90)]
    for team in (home,away):
        rec=dict(game_id=gid,team=team)
        fo,fd=filt[filt.posteam==team],filt[filt.defteam==team]; ro,rd=gp[gp.posteam==team],gp[gp.defteam==team]
        rec['f']=stats(fo,fd,True); rec['r']=stats(ro,rd,True)      # turnovers removed from EPA
        rec['f_to']=stats(fo,fd,False); rec['r_to']=stats(ro,rd,False) # turnovers included
        dr=d[(d.game_id==gid)&(d.posteam==team)].drop_duplicates('drive')[['drive_time_of_possession','drive_play_count']].dropna()
        secs=sum(int(t.split(':')[0])*60+int(t.split(':')[1]) for t in dr.drive_time_of_possession)
        rec['pace']=secs/dr.drive_play_count.sum() if dr.drive_play_count.sum() else None
        rec['npace']=neutral_pace(gp,team)
        rows.append(rec)
r=pd.DataFrame(rows).merge(g[['game_id','week','home_team','away_team','home_score','away_score','spread_line','total_line','gameday']],on='game_id')
games=[]
for x in r.itertuples():
    home=x.team==x.home_team; opp=x.away_team if home else x.home_team; s=-1 if home else 1
    v=bq.get(str(int(x.week)),{}).get(f"{x.away_team}@{x.home_team}")
    if v: ol,cl,ot,ct=s*v[0],s*v[1],v[2],v[3]
    else: ol,cl,ot,ct=None,(-x.spread_line if home else x.spread_line),None,x.total_line
    pf,pa=(x.home_score,x.away_score) if home else (x.away_score,x.home_score)
    games.append(dict(team=x.team,week=int(x.week),opp=opp,home=bool(home),pf=int(pf),pa=int(pa),date=x.gameday,
        f=x.f,r=x.r,f_to=x.f_to,r_to=x.r_to,pace=x.pace,npace=x.npace,open_line=ol,close_line=cl,open_total=ot,close_total=ct))
# ---- document sections ----
try:
    import markdown; md=lambda t: markdown.markdown(t,extensions=['tables'])
except ImportError:
    md=lambda t: "<pre>"+t+"</pre>"
teams={"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers","LA":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"}
div={"BUF":"AFC East","MIA":"AFC East","NE":"AFC East","NYJ":"AFC East","BAL":"AFC North","CIN":"AFC North","CLE":"AFC North","PIT":"AFC North","HOU":"AFC South","IND":"AFC South","JAX":"AFC South","TEN":"AFC South","DEN":"AFC West","KC":"AFC West","LV":"AFC West","LAC":"AFC West","DAL":"NFC East","NYG":"NFC East","PHI":"NFC East","WAS":"NFC East","CHI":"NFC North","DET":"NFC North","GB":"NFC North","MIN":"NFC North","ATL":"NFC South","CAR":"NFC South","NO":"NFC South","TB":"NFC South","ARI":"NFC West","LA":"NFC West","SF":"NFC West","SEA":"NFC West"}
doc=open('nfl_2026_almanac_summary.md',encoding='utf-8').read()
parts=re.split(r'(?=^## |^# )',doc,flags=re.M)
tdata={}; extras=[]
for sec in parts:
    m=re.match(r'^## (.+)\n',sec)
    if m and m.group(1).strip() in teams.values():
        name=m.group(1).strip(); abbr=[k for k,v in teams.items() if v==name][0]
        body=sec[m.end():]
        body=re.sub(r'\*\*Formlines \(2026\)\*\*.*?(?=\n---\n|\Z)','',body,flags=re.S).strip().rstrip('-').strip()
        paras=[p for p in re.split(r'\n\n+',body) if p.strip()]
        header=paras[0] if paras and paras[0].startswith('**') and '|' in paras[0] else ''
        rest=paras[1:] if header else paras
        coaching=[p for p in rest if p.startswith('**Coaching:**')]
        diggs=[p for p in rest if p.startswith('**Diggs vs FTN')]
        bottom=[p for p in rest if p.startswith('**Bottom line')]
        main=[p for p in rest if p not in coaching+diggs+bottom]
        tdata[abbr]=dict(name=name,division=div[abbr],header=header.strip('*'),coaching=md('\n\n'.join(coaching)),
            summary=md('\n\n'.join(main)),bottom=md('\n\n'.join(bottom)),diggs=md('\n\n'.join(diggs)))
    elif sec.strip():
        h=re.match(r'^#+ (.+)\n',sec)
        extras.append(dict(title=h.group(1).strip() if h else 'Notes',html=md(sec[h.end():] if h else sec)))
weeks=sorted(set(x['week'] for x in games))
out=dict(updated=datetime.date.today().isoformat(),weeks=weeks,teams=tdata,games=games,extras=extras,upcoming={})
# upcoming lines for weeks not yet played (from betql json)
for wk,gm in bq.items():
    if int(wk) not in weeks: out['upcoming'][wk]=gm
open('data.js','w',encoding='utf-8').write('window.NFL_DATA='+json.dumps(out)+';')
print("data.js written — weeks",weeks,"—",len(games)//2,"games,",len(tdata),"teams")
