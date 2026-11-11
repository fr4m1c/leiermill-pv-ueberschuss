"""Isolierter YAML-Interpreter: keine Verbindung zu Home Assistant oder Geräten.
Start: python gesamttest.py (benötigt PyYAML und Jinja2).
Modelliert die verwendeten HA-Aktionen, Timer und Rückmeldungen, nicht HA selbst.
"""
import json, math, hashlib, traceback, ast
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'pv_waermepumpe.yaml'
DOC = yaml.safe_load(SOURCE.read_text())
P = 'sensor.beispiel_e3dc_'
GRID, PV, BAT, SOC = [P+x for x in ['netz_leistung','pv_leistung','batterie_leistung','ladezustand']]
V = 'beispiel_vicare_'
H, W = 'number.'+V+'normale_heiztemperatur', 'number.'+V+'ww_temperatur'
C, TEMP, MODE = 'climate.'+V+'heizung', 'sensor.'+V+'ww_speichertemperatur', 'select.'+V+'warmwasser_betriebsart'
AUTO, READY, WW = ['input_boolean.leiermill_pv_'+x for x in ['automatik','bereit','ww_freigabe']]
J, PAUSE = 'input_text.leiermill_pv_merker','input_datetime.leiermill_pv_pause_bis'

def seconds(v):
    if isinstance(v,(float,int)): return int(v)
    h,m,s=map(int,v.split(':')); return h*3600+m*60+s
def numeric(x):
    try: return math.isfinite(float(x))
    except (ValueError,TypeError): return False
def stamp(x, default=0):
    try:
        if isinstance(x,datetime): return x.timestamp()
        if numeric(x): return float(x)
        return datetime.fromisoformat(x).replace(tzinfo=timezone.utc).timestamp()
    except (ValueError,TypeError): return default
def from_json(x, default=None):
    try: return json.loads(x)
    except (ValueError,TypeError): return default
class Stop(Exception): pass
class States:
    def __init__(self,e): self.e=e
    def __call__(self,k): return self.e.s.get(k,'unknown')
    def __getitem__(self,k): return NS(state=self(k),last_reported=datetime.fromtimestamp(self.e.reported.get(k,0),timezone.utc))

class Engine:
    def __init__(self,h=18,w=48):
        self.t=1794225600; self.origin=self.t
        self.s={GRID:'-4000',PV:'8000',BAT:'0',SOC:'100',H:str(h),W:str(w),C:'auto',TEMP:'46',MODE:'efficient_with_min_comfort',AUTO:'on',READY:'on',WW:'on',J:'{}',PAUSE:'2000-01-01 00:00:00'}
        self.attrs={C:{'active_vicare_program':'normalHeating'}}
        self.attrs.update({k:{'unit_of_measurement':'%' if k==SOC else 'W'} for k in [GRID,PV,BAT,SOC]})
        self.reported={k:self.t for k in [GRID,PV,BAT,SOC]}
        self.frozen=set(); self.pending=[]; self.write_delay=0; self.reject=set()
        self.logs=[]; self.timers={}; self.busy=False; self.cache={}
        self.env=Environment(undefined=StrictUndefined)
        self.env.filters.update(from_json=from_json,to_json=lambda x:json.dumps(x,separators=(',',':')))
        self.env.globals.update(states=States(self),is_number=numeric,now=lambda:datetime.fromtimestamp(self.t,timezone.utc),as_timestamp=stamp,is_state=lambda k,v:self.s.get(k)==v,state_attr=lambda k,a:self.attrs.get(k,{}).get(a))
        self.sensors()
    def render(self,x,ctx):
        if isinstance(x,dict): return {k:self.render(v,ctx) for k,v in x.items()}
        if isinstance(x,list): return [self.render(v,ctx) for v in x]
        if not isinstance(x,str) or ('{{' not in x and '{%' not in x): return x
        if x not in self.cache: self.cache[x]=self.env.from_string(x)
        value=self.cache[x].render(**ctx).strip()
        if value in ('True','False'): return value=='True'
        if numeric(value): return float(value) if '.' in value else int(value)
        if value.startswith(('{','[')):
            try: return json.loads(value)
            except ValueError:
                try: return ast.literal_eval(value)
                except (ValueError,SyntaxError): pass
        return value
    def log(self,action,data): self.logs.append({'sekunde':self.t-self.origin,'aktion':action,'daten':data})
    def set(self,k,v): self.s[k]=str(v); self.sensors()
    def journal(self): return from_json(self.s[J],{})
    def sensors(self):
        for item in DOC['template'][0]['binary_sensor']:
            key='binary_sensor.'+item['unique_id']; truth=bool(self.render(item['state'],{}))
            if truth:
                self.timers.setdefault(key,self.t)
                truth=self.t-self.timers[key]>=seconds(item.get('delay_on',0))
            else: self.timers.pop(key,None)
            self.s[key]='on' if truth else 'off'
    def advance(self,n,controller=True):
        end=self.t+n
        while self.t<end:
            self.t+=1
            for k in self.reported:
                if k not in self.frozen: self.reported[k]=self.t
            for event in self.pending[:]:
                when,k,v=event
                if when<=self.t:
                    self.s[k]=str(v); self.pending.remove(event); self.log('Rückmeldung',{'entity':k,'value':v})
            self.sensors()
            if controller and not self.busy and self.t%15==0: self.tick()
    def condition(self,x,ctx):
        if isinstance(x,list): return all(self.condition(v,ctx) for v in x)
        if isinstance(x,dict):
            assert x['condition']=='template',x
            return bool(self.render(x['value_template'],ctx))
        return bool(self.render(x,ctx))
    def run(self,sequence,ctx):
        for step in sequence:
            if 'variables' in step:
                for k,v in step['variables'].items(): ctx[k]=self.render(v,ctx)
            elif 'condition' in step:
                if not self.condition(step,ctx): raise Stop()
            elif 'choose' in step:
                for branch in step['choose']:
                    if self.condition(branch['conditions'],ctx):
                        self.run(branch['sequence'],ctx); break
            elif 'if' in step:
                self.run(step.get('then' if self.condition(step['if'],ctx) else 'else',[]),ctx)
            elif 'repeat' in step:
                old=ctx.get('repeat')
                for i,item in enumerate(self.render(step['repeat']['for_each'],ctx),1):
                    ctx['repeat']=NS(item=NS(**item),index=i)
                    self.run(step['repeat']['sequence'],ctx)
                ctx['repeat']=old
            elif 'delay' in step: self.advance(seconds(step['delay']),False)
            elif 'wait_template' in step:
                end=self.t+seconds(step['timeout'])
                while not self.render(step['wait_template'],ctx) and self.t<end: self.advance(1,False)
                ctx['wait']=NS(completed=bool(self.render(step['wait_template'],ctx)))
            elif 'stop' in step: raise Stop()
            elif 'action' in step:
                action=step['action']; target=self.render(step.get('target',{}),ctx); data=self.render(step.get('data',{}),ctx)
                self.log(action,{'target':target,'data':data})
                k=target.get('entity_id')
                if action=='input_text.set_value': self.s[k]=json.dumps(data['value'],separators=(',',':')) if isinstance(data['value'],dict) else str(data['value'])
                elif action=='input_datetime.set_datetime': self.s[k]=datetime.fromtimestamp(data['timestamp'],timezone.utc).isoformat()
                elif action.startswith('input_boolean.'): self.s[k]='on' if action.endswith('turn_on') else 'off'
                elif action=='number.set_value':
                    assert k in (H,W), 'Unzulässiges Schreibziel'
                    if k not in self.reject:
                        if self.write_delay: self.pending.append((self.t+self.write_delay,k,data['value']))
                        else: self.s[k]=str(data['value'])
                elif action.startswith('script.'):
                    try: self.run(DOC['script'][action.split('.',1)[1]]['sequence'],dict(data))
                    except Stop: pass
                elif action.startswith('persistent_notification.'): pass # Nur Protokoll; keine realen Meldungen.
                else: raise ValueError('Nicht modellierte Aktion: '+action)
                self.sensors()
            else: raise ValueError(step)
    def tick(self,trigger='tick'):
        self.busy=True
        try: self.run(DOC['automation'][0]['actions'],{'trigger':NS(id=trigger)})
        except Stop: pass
        finally: self.busy=False
    def active(self): self.advance(600); assert self.journal().get('s')=='heizen20'; return self

RESULTS=[]
def test(name,fn):
    e=Engine()
    try: fn(e); status='BESTANDEN'; error=''
    except Exception: status='FEHLER'; error=traceback.format_exc()
    RESULTS.append({'test':name,'ergebnis':status,'fehler':error,'protokoll':e.logs})
    print(status,name,error)
def eq(e,k,v): assert str(e.s[k])==str(v),(k,e.s[k],v)
def val(e,k,v): assert float(e.s[k])==v,(k,e.s[k],v)
def restored(e): val(e,H,18); val(e,W,48); assert e.journal()=={}

def stages(e):
    e.advance(599); val(e,H,18)
    e.advance(1); val(e,H,20)
    e.advance(1799); val(e,W,48)
    e.advance(1); val(e,W,55)
    e.set(TEMP,54.9); e.advance(15); val(e,H,20)
    e.set(TEMP,55); e.advance(15); val(e,H,22); val(e,W,48)
    e.set(AUTO,'off'); e.tick(); restored(e)
test('98 % / 10 min Freigabe; 20 °C → WW 55 °C → 22 °C → Ausgangswerte',stages)

def battery_first(e):
    e.set(SOC,97); e.advance(1200); val(e,H,18)
    e.set(SOC,98); e.advance(599); val(e,H,18); e.advance(1); val(e,H,20)
test('Batterie zuerst; Startgrenze 98 %',battery_first)
def self_consumption(e):
    e.active(); e.set(GRID,0); e.advance(1800); val(e,H,20); val(e,W,48)
test('Eigenverbrauch der WP beendet Anhebung nicht; ohne Reserve keine nächste Stufe',self_consumption)
def clouds(e):
    e.active(); e.set(GRID,1500); e.advance(120); val(e,H,20)
    e.set(GRID,0); e.advance(60); val(e,H,20)
    e.set(GRID,1500); e.advance(179); val(e,H,20); e.advance(1); restored(e)
test('Kurze Wolke bleibt toleriert; Zusatzverbrauch ab 3 min nimmt Anhebung zurück',clouds)
def discharge(e):
    e.active(); e.set(GRID,0); e.set(BAT,-701); e.advance(180); restored(e)
test('Batterieentladung über 700 W für 3 min',discharge)
def reserve(e):
    e.active(); e.set(SOC,94); e.set(GRID,0); e.advance(299); val(e,H,20); e.advance(1); restored(e)
test('SoC unter 95 % für 5 min',reserve)
def cooldown(e):
    e.active(); e.set(AUTO,'off'); e.tick(); restored(e)
    e.set(AUTO,'on'); e.advance(599); val(e,H,18); e.advance(1); val(e,H,20)
test('Pause und neue Startprüfung jeweils 10 min',cooldown)
def manual(e):
    e.active(); e.advance(1800); val(e,W,55)
    e.set(H,21); e.tick(); val(e,H,21); val(e,W,48); eq(e,AUTO,'off'); assert not e.journal()
test('Manuelle 21 °C bleiben erhalten; eigene WW-Anhebung wird zurückgesetzt',manual)
def schedule(e):
    e.active(); e.attrs[C]['active_vicare_program']='reducedHeating'; e.tick(); restored(e)
test('Wechsel in reduzierte Zeitphase',schedule)
def restart(e):
    e.active(); e.advance(1800); e.timers.clear(); e.tick('start'); restored(e); eq(e,READY,'on')
test('Neustart mit gespeichertem Wiederherstellungsjournal',restart)
def invalid(e):
    e.active(); e.set(GRID,'unavailable'); e.tick(); restored(e)
test('Ungültiger E3/DC-Sensor während Anhebung',invalid)
def stale(e):
    e.active(); e.frozen.add(GRID); e.advance(195); restored(e)
test('E3/DC-Messwert älter als 180 Sekunden',stale)
def unit(e):
    e.attrs[GRID]['unit_of_measurement']='kW'; e.sensors(); e.advance(1200); val(e,H,18)
test('Falsche Leistungseinheit verhindert Freigabe',unit)
def ww_locked(e):
    e.set(WW,'off'); e.active(); e.advance(3600); val(e,W,48); val(e,H,20)
test('Ohne WW-Freigabe keine WW-Anhebung',ww_locked)
def delayed(e):
    e.write_delay=30; e.active(); e.set(AUTO,'off'); e.tick(); restored(e)
test('30 Sekunden verzögerte Viessmann-Rückmeldung',delayed)
def rejected(e):
    e.reject.add(H); e.advance(600); val(e,H,18); eq(e,AUTO,'off'); assert e.journal()['p']=='h'
test('Fehlgeschlagene Sollwertanhebung deaktiviert Automatik',rejected)
def retry(e):
    e.active(); e.reject.add(H); e.set(AUTO,'off'); e.tick()
    val(e,H,20); assert e.journal()['s']=='restore'
    e.reject.clear(); e.tick(); restored(e)
test('Fehlgeschlagene Rückstellung behält Journal; Wiederholung stellt zurück',retry)
def baseline(e):
    e.set(H,19); e.set(W,50); e.active(); e.advance(1800)
    e.set(AUTO,'off'); e.tick(); val(e,H,19); val(e,W,50); assert not e.journal()
test('Gespeicherte Ausgangswerte 19/50 statt fest verdrahteter 18/48',baseline)

def late_restore(e):
    e.active(); e.write_delay=70; e.set(AUTO,'off'); e.tick()
    assert e.journal()['s']=='restore'
    e.advance(90); restored(e)
test('Rückstellbestätigung erst nach 70 Sekunden; Journal bleibt bis Bestätigung',late_restore)
def late_start(e):
    e.write_delay=90; e.advance(600)
    eq(e,AUTO,'off'); e.advance(120)
    restored(e)
test('Anhebung wird erst 90 Sekunden nach Auftrag übernommen, nach Schreibtimeout',late_start)

report={'quelle_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'methode':'Lokale Ausführung der YAML-Templates und Aktionen mit modellierter HA-Laufzeit und virtueller Zeit. Keine Netzwerkverbindung, keine Gerätezugriffe. Nicht gleichzusetzen mit einem Test der echten HA-Laufzeit oder Viessmann-API.','nicht_geprueft':['Installierter HA-Dateistand (nur gespeicherte Version vorhanden)','Ampel und Forecast (deren aktueller YAML-Dateistand liegt nicht vor)','Reale Zeitplanwirkung, Heizstabfreigabe und physische Wärmeabgabe','Späte API-Schreibaufträge nach Timeout, parallele HA-Ereignisse und Neustart mitten in laufendem API-Auftrag'],'tests':RESULTS}
(ROOT/'Testprotokoll.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
lines=['# LEIERMILL – Simulationsprotokoll','',report['methode'],'','Quelle: `pv_waermepumpe.yaml`',f"SHA256: `{report['quelle_sha256']}`",'','| Prüffall | Ergebnis |','|---|---|']
lines += [f"| {r['test']} | {r['ergebnis']} |" for r in RESULTS]
lines += ['','## Grenzen','']+['- '+x for x in report['nicht_geprueft']]
lines += ['','## Wiederholen','','`python -m pip install PyYAML Jinja2`','', '`python gesamttest.py`','','Die YAML bleibt unverändert. Nicht in Home Assistant als Paket installieren. Das JSON-Protokoll enthält jeden simulierten Schreibaufruf mit virtueller Zeit.']
(ROOT/'Testprotokoll.md').write_text('\n'.join(lines)+'\n')
raise SystemExit(any(r['ergebnis']=='FEHLER' for r in RESULTS))
