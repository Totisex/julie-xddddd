"""Smoke test con una API de Revit FALSA (Fase 0).

Valida el flujo, la agregacion y la serializacion JSON del script de diagnostico.
NO valida que los nombres/propiedades reales de la API de Revit sean correctos:
eso solo se comprueba ejecutando el script dentro de Revit.

Uso:  python3 -I tests/fake_revit_smoke.py [ruta/al/script.py]
"""
import sys, types, os, json, runpy, tempfile

# ---------- modulos falsos ----------
def mod(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m

mod('clr', AddReference=lambda n: None, GetClrType=lambda c: c)

class _Ver:
    def __str__(self): return '4.0.30319.42000'
class _Info: FrameworkDescription = '.NET Framework 4.8 (fake)'
System = mod('System')
System.Environment = types.SimpleNamespace(Version=_Ver(), OSVersion=types.SimpleNamespace(VersionString='Win fake'), Is64BitProcess=True)
System.IO = types.SimpleNamespace(Path=types.SimpleNamespace(GetTempPath=lambda: tempfile.gettempdir()))
System.Net = types.SimpleNamespace(HttpListener=types.SimpleNamespace(IsSupported=True))
System.Runtime = types.SimpleNamespace(InteropServices=types.SimpleNamespace(RuntimeInformation=_Info))

class Enum:
    def __init__(self, n): self.n = n
    def __repr__(self): return self.n
    def __eq__(self, o): return isinstance(o, Enum) and o.n == self.n
    def __hash__(self): return hash(self.n)
    __str__ = __repr__

def enumcls(*names):
    return type('E', (), {n: Enum(n) for n in names})

class FId:
    _n = 100
    def __init__(self, v=None):
        if v is None:
            FId._n += 1; v = FId._n
        self.IntegerValue = v

BIP = enumcls('RBS_SYSTEM_CLASSIFICATION_PARAM', 'RBS_PIPING_SYSTEM_TYPE_PARAM', 'RBS_SYSTEM_NAME_PARAM',
              'RBS_SYSTEM_ABBREVIATION_PARAM', 'RBS_PIPE_DIAMETER_PARAM', 'CURVE_ELEM_LENGTH', 'MATERIAL_ID_PARAM',
              'RBS_START_LEVEL_PARAM', 'PHASE_CREATED', 'PHASE_DEMOLISHED', 'RBS_CALCULATED_SIZE',
              'PROJECT_NAME', 'PROJECT_NUMBER', 'PROJECT_STATUS')
BIC = enumcls('OST_PipeCurves', 'OST_PipeFitting', 'OST_PipeAccessory', 'OST_PlumbingFixtures', 'OST_MechanicalEquipment')
ST = enumcls('String', 'Double', 'ElementId', 'Integer')

class Defn:
    def __init__(self, name, bip=None): self.Name = name; self.BuiltInParameter = bip

class Param:
    def __init__(self, name, st, val, bip=None, text=None):
        self.Definition = Defn(name, bip); self.StorageType = st; self._v = val; self._t = text
        self.HasValue = val is not None; self.IsShared = False
    def AsString(self): return self._v
    def AsDouble(self): return self._v
    def AsElementId(self): return self._v
    def AsValueString(self): return self._t

class Elem:
    def __init__(self, doc, cat=None, name='x', params=None, bip=None, **kw):
        self.Id = FId(); self.UniqueId = 'uid-%d' % self.Id.IntegerValue; self._name = name
        self.Parameters = params or []; self._bip = bip or {}; self.Category = cat
        self.LevelId = kw.get('level', FId(-1)); self.WorksetId = None; self.DesignOption = None
        self.MEPSystem = kw.get('mep'); self.ConnectorManager = kw.get('cm')
        self.Symbol = kw.get('symbol'); self.MEPModel = kw.get('mepmodel'); self._type = kw.get('typeid', FId(-1))
        self.IsTemplate = False; self.ViewType = 'FloorPlan'
        doc.elements.append(self)
    @property
    def Name(self): return self._name
    def get_Parameter(self, b): return self._bip.get(b)
    def GetTypeId(self): return self._type
    def GetType(self): return types.SimpleNamespace(Name=type(self).__name__)

class Pipe(Elem): pass
class FamilyInstance(Elem): pass
class Level(Elem):
    Elevation = 0.0
class View(Elem): pass
class ViewSchedule(Elem): pass
class DesignOption(Elem): pass
class RevitLinkInstance(Elem):
    def GetLinkDocument(self): return None
class PipingSystem(Elem):
    SystemType = Enum('Sanitary')
    class PipingNetwork: Size = 3
class PipingSystemType(Elem):
    SystemClassification = Enum('Sanitary')
class PipeType(Elem): pass
class PipeSegment(Elem): MaterialId = FId(-1)

class Conn:
    def __init__(self, dom, pst, ms, conn): self.Domain = dom; self.PipeSystemType = pst; self.MEPSystem = ms; self.IsConnected = conn
class CM:
    def __init__(self, cs): self.Connectors = cs

class Doc:
    Title = 'SANI COMPLETO JULIETTE100'; PathName = r'C:\x\TIP II\SANI COMPLETO JULIETTE100.rvt'
    IsFamilyDocument = False; IsLinked = False; IsReadOnly = False; IsWorkshared = False; IsDetached = False
    IsModified = False
    def __init__(self):
        self.elements = []; self.ProjectInformation = Elem(self, bip={BIP.PROJECT_NAME: Param('Project Name', ST.String, 'Proyecto \u00f1and\u00fa', BIP.PROJECT_NAME)})
        self.Phases = [types.SimpleNamespace(Name='Nueva construcci\u00f3n')]
        self.Settings = types.SimpleNamespace(Categories=[])
    def GetElement(self, eid):
        for e in self.elements:
            if e.Id.IntegerValue == eid.IntegerValue: return e
    def GetUnits(self):
        fo = types.SimpleNamespace(GetUnitTypeId=lambda: types.SimpleNamespace(TypeId='autodesk.unit.unit:millimeters-1.0.1'))
        return types.SimpleNamespace(GetFormatOptions=lambda spec: fo)
    def GetWarnings(self): return [types.SimpleNamespace(GetDescriptionText=lambda: 'Aviso fake')] * 2

class Collector:
    def __init__(self, doc): self.doc = doc; self.f = lambda e: True
    def OfClass(self, cls): self.f = (lambda e, c=cls: isinstance(e, c)); return self
    def OfCategory(self, bic): self.f = (lambda e, b=bic: e.Category == b); return self
    def OfCategoryId(self, cid): self.f = (lambda e: False); return self
    def WhereElementIsNotElementType(self): return self
    def ToElements(self): return [e for e in self.doc.elements if self.f(e)]
    def GetElementCount(self): return len(self.ToElements())
    def __iter__(self): return iter(self.ToElements())

DB = mod('Autodesk.Revit.DB',
    FilteredElementCollector=Collector, BuiltInParameter=BIP, BuiltInCategory=BIC, StorageType=ST,
    Domain=enumcls('DomainPiping', 'DomainHvac'), CategoryType=enumcls('Model'), ElementId=lambda x: FId(7),
    View=View, ViewSchedule=ViewSchedule, Level=Level, DesignOption=DesignOption, RevitLinkInstance=RevitLinkInstance,
    UnitUtils=types.SimpleNamespace(ConvertFromInternalUnits=lambda x, u: x * (0.3048 if u == 'm' else 304.8)),
    UnitTypeId=types.SimpleNamespace(Meters='m', Millimeters='mm'),
    SpecTypeId=types.SimpleNamespace(Length='L', PipeSize='P'),
    Category=types.SimpleNamespace(GetCategory=lambda d, i: None),
    Element=types.SimpleNamespace(Name=types.SimpleNamespace(GetValue=lambda e: e._name)),
    WorksetKind=enumcls('UserWorkset'))
Plumbing = mod('Autodesk.Revit.DB.Plumbing', Pipe=Pipe, PipingSystem=PipingSystem, PipingSystemType=PipingSystemType,
               PipeType=PipeType, PipeSegment=PipeSegment)
DB.Plumbing = Plumbing
UI = mod('Autodesk.Revit.UI', ExternalEvent=object, IExternalEventHandler=object)
Revit = mod('Autodesk.Revit', DB=DB, UI=UI)
mod('Autodesk', Revit=Revit)

# ---------- modelo falso ----------
doc = Doc()
lvl = Level(doc, name='NIVEL 1'); lvl.Elevation = 3.2808
ptype = PipeType(doc, name='PVC-SAL 110')
sysT = PipingSystemType(doc, name='Desague', bip={BIP.RBS_SYSTEM_ABBREVIATION_PARAM: Param('Abbreviation', ST.String, 'DES')})
sysI = PipingSystem(doc, name='Desague 1')
def mkpipe(cls_txt, with_sys=True, free=False):
    ps = [Param('Length', ST.Double, 4.32, BIP.CURVE_ELEM_LENGTH, '1.32 m'), Param('Diameter', ST.Double, 0.36, BIP.RBS_PIPE_DIAMETER_PARAM, '110 mm')]
    b = {BIP.CURVE_ELEM_LENGTH: ps[0], BIP.RBS_PIPE_DIAMETER_PARAM: ps[1]}
    if cls_txt:
        pc = Param('System Classification', ST.String, cls_txt, BIP.RBS_SYSTEM_CLASSIFICATION_PARAM); ps.append(pc); b[BIP.RBS_SYSTEM_CLASSIFICATION_PARAM] = pc
    cm = CM([Conn(DB.Domain.DomainPiping, Enum('Sanitary'), sysI if with_sys else None, not free)])
    return Pipe(doc, BIC.OST_PipeCurves, 'Pipe', ps, b, mep=sysI if with_sys else None, cm=cm, typeid=ptype.Id, level=lvl.Id)
mkpipe('Sanitary'); mkpipe('Sanitary'); mkpipe(None, with_sys=False, free=True)
fam = types.SimpleNamespace(Name='Codo PVC'); sym = types.SimpleNamespace(Family=fam, Name='110')
FamilyInstance(doc, BIC.OST_PipeFitting, 'Codo', symbol=sym, mepmodel=types.SimpleNamespace(ConnectorManager=CM([Conn(DB.Domain.DomainPiping, Enum('Sanitary'), sysI, True)])))
FamilyInstance(doc, BIC.OST_PlumbingFixtures, 'WC', symbol=types.SimpleNamespace(Family=types.SimpleNamespace(Name='Inodoro'), Name='Std'), mepmodel=None)
View(doc, name='Planta 1')
vs = ViewSchedule(doc, name='SAN - viejo')
vs.IsTitleblockRevisionSchedule = False
vs.Definition = types.SimpleNamespace(CategoryId=FId(5), GetFieldCount=lambda: 3, GetFilterCount=lambda: 0, IsItemized=True,
    GetSchedulableFields=lambda: [types.SimpleNamespace(GetName=lambda d: 'Length', FieldType='Instance')])
DB.ElementId = lambda x: FId(5)  # el id de categoria coincide con el del schedule falso

uiapp = types.SimpleNamespace(
    Application=types.SimpleNamespace(VersionNumber='2024', VersionName='Autodesk Revit 2024', VersionBuild='24.0.0', SubVersionNumber='24.0', Language='Spanish'),
    ActiveUIDocument=types.SimpleNamespace(Document=doc, ActiveView=View(doc, name='Planta 1')))

outdir = tempfile.mkdtemp(prefix='smoke_')
os.environ['CLAUDE_BIM_REPORTS'] = outdir
HERE = os.path.dirname(os.path.abspath(__file__))
script = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, '..', 'pyrevit', 'ClaudeBIM.extension', 'ClaudeBIM.tab', 'Diagnostico.panel', 'Fase0.pushbutton', 'script.py')
runpy.run_path(script, init_globals={'__revit__': uiapp}, run_name='__main__')
files = os.listdir(outdir)
assert len(files) == 1, files
data = json.load(open(os.path.join(outdir, files[0])))
print('\nJSON valido. Secciones:', sorted(data.keys()))
print('errores_del_script:', json.dumps(data['errores_del_script'], indent=1)[:1500])
print('tuberias.cobertura:', data['tuberias']['cobertura'])
print('accesorios:', data['accesorios_de_tuberia']['por_PipeSystemType_de_conectores'])
