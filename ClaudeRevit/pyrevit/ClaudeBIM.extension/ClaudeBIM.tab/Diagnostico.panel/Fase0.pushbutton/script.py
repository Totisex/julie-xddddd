# -*- coding: utf-8 -*-
"""
CLAUDE BIM - FASE 0 - DIAGNOSTICO DEL MODELO REVIT (SOLO LECTURA)
=================================================================

Que hace
    Lee el modelo abierto en Revit y escribe un JSON con la estructura real
    del proyecto y de sus instalaciones sanitarias: version de Revit/pyRevit,
    unidades, niveles, vistas, categorias, sistemas MEP, tuberias, accesorios,
    aparatos, vinculos, advertencias y parametros disponibles.

Que NO hace
    - NO abre ninguna Transaction. NO modifica el documento.
    - NO crea schedules, NO cambia parametros, NO elimina nada.
    - NO calcula metrados (eso es la Fase 5). Solo reporta que informacion
      existe en el modelo y con que cobertura.
    - NO ejecuta codigo recibido de fuera (sin eval/exec).
    - NO guarda el archivo RVT.

Como se usa
    1. Abre en Revit el archivo RVT (de preferencia una COPIA).
    2. Pulsa el boton "Diagnostico Fase 0" de la pestana ClaudeBIM
       (instalacion de la extension: ver ClaudeRevit/README.md).
    3. Envia el JSON generado (carpeta indicada al final de la ejecucion).

Compatibilidad (diseno; NO probado todavia contra un Revit real)
    Escrito para IronPython 2.7 y CPython 3. Detecta la API por version:
    unidades con ForgeTypeId si existe (si no, DisplayUnitType) y ElementId
    con .Value si existe (si no, .IntegerValue). Todo el texto es ASCII.
"""
from __future__ import print_function

__title__ = 'Diagnostico\nFase 0'
__author__ = 'CLAUDE BIM'

import sys
import os
import json
import time
import datetime
import platform

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
import System
from Autodesk.Revit import DB
from Autodesk.Revit import UI

try:
    from Autodesk.Revit.DB import Plumbing
except Exception:
    Plumbing = None

try:
    text_type = unicode  # IronPython 2.7
except NameError:
    text_type = str

SCRIPT_VERSION = '0.1.0-fase0'
ARCHIVO_ESPERADO = 'SANI COMPLETO JULIETTE100'
TOP_N = 60            # filas maximas por distribucion en el JSON
MAX_PARAM_SCAN = 2000  # tuberias maximas para inventariar parametros
MUESTRA_TUBERIAS = 15  # tuberias de muestra con detalle completo

CATEGORIAS_SANITARIAS = [
    'OST_PipeCurves', 'OST_FlexPipeCurves', 'OST_PlaceHolderPipes',
    'OST_PipeFitting', 'OST_PipeAccessory', 'OST_PlumbingFixtures',
    'OST_MechanicalEquipment', 'OST_PipeInsulations',
]

ERRORS = []


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def out(*args):
    try:
        print(*args)
    except Exception:
        try:
            print(repr(args))
        except Exception:
            pass


def u_(v):
    if v is None:
        return None
    if isinstance(v, text_type):
        return v
    try:
        return text_type(v)
    except Exception:
        return repr(v)


def log_error(ctx, ex):
    ERRORS.append({'contexto': ctx, 'error': u_(ex)})


def g(ctx, fn, default=None):
    """Ejecuta fn(); si falla registra el error y devuelve default."""
    try:
        return fn()
    except Exception as ex:
        log_error(ctx, ex)
        return default


def eid_int(eid):
    """Valor entero de un ElementId (Revit 2024+ usa .Value; antes .IntegerValue)."""
    if eid is None:
        return None
    v = getattr(eid, 'Value', None)
    if v is not None:
        return int(v)
    return int(eid.IntegerValue)


def el_name(e):
    if e is None:
        return None
    try:
        return u_(e.Name)
    except Exception:
        pass
    try:
        return u_(DB.Element.Name.GetValue(e))
    except Exception:
        return None


def blank(s):
    return s is None or u_(s).strip() == ''


def bip(name):
    return getattr(DB.BuiltInParameter, name, None)


def bip_param(el, name):
    b = bip(name)
    if b is None or el is None:
        return None
    try:
        return el.get_Parameter(b)
    except Exception:
        return None


def ptext(doc, p):
    """Texto de un Parameter segun su tipo de almacenamiento (None si vacio)."""
    if p is None:
        return None
    try:
        if not p.HasValue:
            return None
        st = p.StorageType
        if st == DB.StorageType.String:
            return u_(p.AsString())
        if st == DB.StorageType.ElementId:
            eid = p.AsElementId()
            if eid_int(eid) == -1:
                return None
            e = doc.GetElement(eid)
            return el_name(e) if e is not None else 'id:%s' % eid_int(eid)
        return u_(p.AsValueString())
    except Exception as ex:
        log_error('ptext', ex)
        return None


def pdouble_pos(p):
    """True si el parametro numerico existe y es > 0 (cobertura, no medicion)."""
    if p is None:
        return False
    try:
        return bool(p.HasValue) and p.StorageType == DB.StorageType.Double and p.AsDouble() > 0
    except Exception:
        return False


def tally_add(t, key):
    t[key] = t.get(key, 0) + 1


def tally_rows(t, label='valor', top=TOP_N):
    items = sorted(t.items(), key=lambda kv: (-kv[1], u_(kv[0]) or ''))
    rows = []
    for k, v in items[:top]:
        if isinstance(k, tuple):
            k = [u_(x) for x in k]
        else:
            k = u_(k)
        rows.append({label: k, 'cantidad': v})
    return {'distintos': len(items), 'mostrados': len(rows), 'filas': rows}


def of_class(doc, cls):
    try:
        return DB.FilteredElementCollector(doc).OfClass(cls)
    except Exception:
        return DB.FilteredElementCollector(doc).OfClass(clr.GetClrType(cls))


def collect_cat(doc, bic_name):
    bic = getattr(DB.BuiltInCategory, bic_name, None)
    if bic is None:
        return None
    return list(DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements())


def conv_len(x, unit):
    """Convierte longitud interna (pies) con la API de Revit. unit: 'm' o 'mm'."""
    if hasattr(DB, 'UnitTypeId'):
        uid = DB.UnitTypeId.Meters if unit == 'm' else DB.UnitTypeId.Millimeters
        return DB.UnitUtils.ConvertFromInternalUnits(x, uid)
    dut = DB.DisplayUnitType.DUT_METERS if unit == 'm' else DB.DisplayUnitType.DUT_MILLIMETERS
    return DB.UnitUtils.ConvertFromInternalUnits(x, dut)


def get_connectors(el):
    cm = getattr(el, 'ConnectorManager', None)
    if cm is None:
        mm = getattr(el, 'MEPModel', None)
        cm = getattr(mm, 'ConnectorManager', None) if mm is not None else None
    if cm is None:
        return []
    return [c for c in cm.Connectors]


def level_name(doc, el):
    try:
        lid = el.LevelId
        if lid is not None and eid_int(lid) != -1:
            return el_name(doc.GetElement(lid))
    except Exception:
        pass
    for b in ('RBS_START_LEVEL_PARAM', 'FAMILY_LEVEL_PARAM', 'SCHEDULE_LEVEL_PARAM', 'LEVEL_PARAM'):
        t = ptext(doc, bip_param(el, b))
        if not blank(t):
            return t
    return None


def family_and_type(doc, el):
    try:
        sym = getattr(el, 'Symbol', None)
        if sym is not None:
            fam = getattr(sym, 'Family', None)
            return u_('%s : %s' % (el_name(fam), el_name(sym)))
    except Exception:
        pass
    t = doc.GetElement(el.GetTypeId())
    cat = el.Category.Name if el.Category is not None else '?'
    return u_('%s : %s' % (cat, el_name(t)))


def dump_params(doc, el):
    res = {}
    for p in el.Parameters:
        try:
            nm = u_(p.Definition.Name)
            val = ptext(doc, p)
            if not blank(val):
                res[nm] = val
        except Exception as ex:
            log_error('dump_params', ex)
    return res


# ----------------------------------------------------------------------------
# Secciones del diagnostico
# ----------------------------------------------------------------------------
def collect_environment(uiapp):
    app = uiapp.Application
    env = {}
    env['revit'] = {
        'VersionNumber': g('VersionNumber', lambda: u_(app.VersionNumber)),
        'VersionName': g('VersionName', lambda: u_(app.VersionName)),
        'VersionBuild': g('VersionBuild', lambda: u_(app.VersionBuild)),
        'SubVersionNumber': g('SubVersionNumber', lambda: u_(app.SubVersionNumber)),
        'Language': g('Language', lambda: u_(app.Language)),
    }
    env['python'] = {
        'version': u_(sys.version),
        'implementacion': g('impl', lambda: u_(platform.python_implementation())),
        'plataforma': u_(sys.platform),
    }
    env['dotnet'] = {
        'Environment.Version': g('netver', lambda: u_(System.Environment.Version)),
        'FrameworkDescription': g('fwdesc', lambda: u_(
            System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription)),
        'OS': g('os', lambda: u_(System.Environment.OSVersion.VersionString)),
        'Proceso64bit': g('x64', lambda: bool(System.Environment.Is64BitProcess)),
    }

    pyr = {}
    try:
        from pyrevit import versionmgr
        pyr['version'] = u_(versionmgr.get_pyrevit_version().get_formatted())
    except Exception as ex:
        pyr['version'] = None
        log_error('pyrevit.versionmgr', ex)
    try:
        import pyrevit
        pyr['HOME_DIR'] = u_(getattr(pyrevit, 'HOME_DIR', None))
    except Exception as ex:
        log_error('pyrevit.HOME_DIR', ex)
    try:
        import pyrevit.routes  # noqa: F401
        pyr['modulo_routes_disponible'] = True
    except Exception as ex:
        pyr['modulo_routes_disponible'] = False
        pyr['modulo_routes_error'] = u_(ex)
    env['pyrevit'] = pyr

    # Sondas de comunicacion DENTRO del proceso de Revit (no abren nada permanente).
    com = {}
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', 0))
            com['puede_abrir_puerto_loopback'] = True
            com['puerto_efimero_probado'] = s.getsockname()[1]
        finally:
            s.close()
    except Exception as ex:
        com['puede_abrir_puerto_loopback'] = False
        com['error_socket'] = u_(ex)
    for modname in ('http.server', 'BaseHTTPServer', 'json', 'threading'):
        try:
            __import__(modname)
            com['import_' + modname] = True
        except Exception:
            com['import_' + modname] = False
    com['System.Net.HttpListener.IsSupported'] = g(
        'httplistener', lambda: bool(System.Net.HttpListener.IsSupported))
    com['UI.ExternalEvent'] = hasattr(UI, 'ExternalEvent')
    com['UI.IExternalEventHandler'] = hasattr(UI, 'IExternalEventHandler')
    env['comunicacion_en_proceso'] = com
    return env


def collect_document(uiapp, doc):
    d = {}
    d['titulo'] = u_(doc.Title)
    d['ruta'] = u_(doc.PathName)
    d['coincide_con_archivo_esperado'] = (
        ARCHIVO_ESPERADO.lower() in (u_(doc.Title) + u_(doc.PathName)).lower())
    d['IsFamilyDocument'] = doc.IsFamilyDocument
    d['IsLinked'] = doc.IsLinked
    d['IsReadOnly'] = doc.IsReadOnly
    d['IsWorkshared'] = doc.IsWorkshared
    d['IsDetached'] = g('IsDetached', lambda: doc.IsDetached)
    av = uiapp.ActiveUIDocument.ActiveView
    d['vista_activa'] = {'nombre': el_name(av), 'tipo': u_(av.ViewType)}
    pi = doc.ProjectInformation
    d['informacion_proyecto'] = {
        'nombre': ptext(doc, bip_param(pi, 'PROJECT_NAME')),
        'numero': ptext(doc, bip_param(pi, 'PROJECT_NUMBER')),
        'estado': ptext(doc, bip_param(pi, 'PROJECT_STATUS')),
    }
    d['fases'] = g('fases', lambda: [el_name(p) for p in doc.Phases])
    d['opciones_de_diseno'] = g('designopt', lambda: [
        el_name(o) for o in of_class(doc, DB.DesignOption)])
    if doc.IsWorkshared:
        def _ws():
            col = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
            return [{'nombre': u_(w.Name), 'abierto': w.IsOpen} for w in col]
        d['worksets'] = g('worksets', _ws)
    return d


def collect_units(doc):
    res = {}
    units = doc.GetUnits()
    if hasattr(DB, 'SpecTypeId'):
        res['api'] = 'ForgeTypeId (Revit 2022+)'
        res['longitud_proyecto'] = g('u_long', lambda: u_(
            units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId().TypeId))
        res['tamano_tuberia_proyecto'] = g('u_pipesize', lambda: u_(
            units.GetFormatOptions(DB.SpecTypeId.PipeSize).GetUnitTypeId().TypeId))
    else:
        res['api'] = 'DisplayUnitType (Revit <= 2021)'
        res['longitud_proyecto'] = g('u_long', lambda: u_(
            units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits))
    # Prueba de la ruta de conversion que usaran los metrados (no es un metrado).
    res['prueba_1_pie_interno_a_m'] = g('conv_m', lambda: conv_len(1.0, 'm'))
    res['prueba_1_pie_interno_a_mm'] = g('conv_mm', lambda: conv_len(1.0, 'mm'))
    return res


def collect_levels(doc):
    rows = []
    for lv in of_class(doc, DB.Level):
        rows.append({
            'id': eid_int(lv.Id),
            'nombre': el_name(lv),
            'elevacion_m': g('lvl_elev', lambda: round(conv_len(lv.Elevation, 'm'), 4)),
        })
    rows.sort(key=lambda r: (r['elevacion_m'] is None, r['elevacion_m']))
    return rows


def collect_views_and_schedules(doc):
    res = {}
    by_type = {}
    templates = 0
    for v in of_class(doc, DB.View):
        try:
            if v.IsTemplate:
                templates += 1
                continue
            tally_add(by_type, u_(v.ViewType))
        except Exception as ex:
            log_error('views', ex)
    res['vistas_por_tipo'] = tally_rows(by_type, 'tipo')
    res['plantillas_de_vista'] = templates

    schedules = []
    fields_by_cat = {}
    targets = {}
    for nm in ('OST_PipeCurves', 'OST_PipeFitting', 'OST_PipeAccessory', 'OST_PlumbingFixtures'):
        b = getattr(DB.BuiltInCategory, nm, None)
        if b is not None:
            targets[eid_int(DB.ElementId(b))] = nm
    for vs in of_class(doc, DB.ViewSchedule):
        try:
            if vs.IsTitleblockRevisionSchedule:
                continue
            d = vs.Definition
            cid = eid_int(d.CategoryId)
            cat = g('schedule_categoria', lambda d=d: DB.Category.GetCategory(doc, d.CategoryId))
            row = {
                'id': eid_int(vs.Id), 'nombre': el_name(vs),
                'categoria': el_name(cat) if cat is not None else None,
                'campos': d.GetFieldCount(), 'filtros': d.GetFilterCount(),
                'itemizado': d.IsItemized,
                'prefijo_SAN': (el_name(vs) or '').upper().startswith('SAN'),
            }
            schedules.append(row)
            if cid in targets and targets[cid] not in fields_by_cat:
                fl = []
                for sf in d.GetSchedulableFields():
                    fl.append({'nombre': u_(sf.GetName(doc)), 'tipo': u_(sf.FieldType)})
                fields_by_cat[targets[cid]] = {'desde_schedule': el_name(vs), 'campos_programables': fl}
        except Exception as ex:
            log_error('schedules', ex)
    res['schedules_existentes'] = schedules
    res['campos_programables_observados'] = fields_by_cat
    res['nota_campos'] = (
        'Los campos programables por categoria solo se pueden leer sin modificar el modelo '
        'si ya existe un schedule de esa categoria. Si falta alguna categoria aqui, se '
        'verificara en la Fase 8 (con autorizacion).')
    return res


def collect_categories(doc):
    res = {}
    rows = []
    for cat in doc.Settings.Categories:
        try:
            if cat.CategoryType != DB.CategoryType.Model:
                continue
            n = DB.FilteredElementCollector(doc).OfCategoryId(cat.Id).WhereElementIsNotElementType().GetElementCount()
            if n > 0:
                rows.append({'categoria': u_(cat.Name), 'elementos': n})
        except Exception as ex:
            log_error('categorias', ex)
    rows.sort(key=lambda r: -r['elementos'])
    res['categorias_de_modelo_con_elementos'] = rows
    res['categorias_sanitarias'] = {}
    for nm in CATEGORIAS_SANITARIAS:
        els = g('cat_' + nm, lambda nm=nm: collect_cat(doc, nm))
        res['categorias_sanitarias'][nm] = None if els is None else len(els)
    return res


def collect_mep_systems(doc):
    res = {'tipos_de_sistema': [], 'sistemas': [], 'tipos_de_tuberia': [], 'segmentos': []}
    if Plumbing is None:
        res['error'] = 'Namespace Autodesk.Revit.DB.Plumbing no disponible'
        return res
    if hasattr(Plumbing, 'PipingSystemType'):
        for t in of_class(doc, Plumbing.PipingSystemType):
            res['tipos_de_sistema'].append({
                'id': eid_int(t.Id), 'nombre': el_name(t),
                'abreviatura': ptext(doc, bip_param(t, 'RBS_SYSTEM_ABBREVIATION_PARAM')),
                'clasificacion_propiedad': g('syscls', lambda t=t: u_(t.SystemClassification)),
                'clasificacion_parametro': ptext(doc, bip_param(t, 'RBS_SYSTEM_CLASSIFICATION_PARAM')),
                'parametros_con_valor': g('syspar', lambda t=t: dump_params(doc, t)),
            })
    if hasattr(Plumbing, 'PipingSystem'):
        for s in of_class(doc, Plumbing.PipingSystem):
            tipo = g('systype', lambda s=s: el_name(doc.GetElement(s.GetTypeId())))
            res['sistemas'].append({
                'id': eid_int(s.Id), 'nombre': g('sysname', lambda s=s: u_(s.Name)),
                'tipo_de_sistema': tipo,
                'PipeSystemType': g('pst', lambda s=s: u_(s.SystemType)),
                'elementos_en_red': g('net', lambda s=s: s.PipingNetwork.Size),
            })
    if hasattr(Plumbing, 'PipeType'):
        for t in of_class(doc, Plumbing.PipeType):
            res['tipos_de_tuberia'].append({'id': eid_int(t.Id), 'nombre': el_name(t)})
    if hasattr(Plumbing, 'PipeSegment'):
        for sg in of_class(doc, Plumbing.PipeSegment):
            mat = g('segmat', lambda sg=sg: el_name(doc.GetElement(sg.MaterialId)))
            res['segmentos'].append({'id': eid_int(sg.Id), 'nombre': el_name(sg), 'material': mat})
    return res


def analyze_pipes(doc, pipes):
    r = {'total_elementos_categoria': len(pipes)}
    clases, tipos, combos, diam, niveles, fases_c, fases_d = {}, {}, {}, {}, {}, {}, {}
    worksets, opciones, sin_sistema_ids = {}, {}, []
    cov = {
        'con_MEPSystem': 0, 'sin_MEPSystem': 0,
        'con_clasificacion_de_sistema': 0, 'con_tipo_de_sistema': 0,
        'con_nombre_de_sistema': 0, 'con_abreviatura_de_sistema': 0,
        'con_diametro_mayor_que_cero': 0, 'con_longitud_mayor_que_cero': 0,
        'con_material_BIP': 0, 'con_material_por_segmento': 0,
        'con_nivel': 0, 'sin_conectores': 0, 'con_algun_conector_libre': 0,
    }
    muestra = []
    pt_cache = {}
    for el in pipes:
        tally_add(clases, u_(el.GetType().Name))
        cls = ptext(doc, bip_param(el, 'RBS_SYSTEM_CLASSIFICATION_PARAM'))
        stype = ptext(doc, bip_param(el, 'RBS_PIPING_SYSTEM_TYPE_PARAM'))
        sname = ptext(doc, bip_param(el, 'RBS_SYSTEM_NAME_PARAM'))
        abbr = ptext(doc, bip_param(el, 'RBS_SYSTEM_ABBREVIATION_PARAM'))
        mep = g('MEPSystem', lambda el=el: el.MEPSystem)
        if mep is None:
            cov['sin_MEPSystem'] += 1
            if len(sin_sistema_ids) < 200:
                sin_sistema_ids.append(eid_int(el.Id))
        else:
            cov['con_MEPSystem'] += 1
        if not blank(cls):
            cov['con_clasificacion_de_sistema'] += 1
        if not blank(stype):
            cov['con_tipo_de_sistema'] += 1
        if not blank(sname):
            cov['con_nombre_de_sistema'] += 1
        if not blank(abbr):
            cov['con_abreviatura_de_sistema'] += 1
        tally_add(combos, (cls or '(vacio)', stype or '(vacio)', abbr or '(vacio)'))

        tid = el.GetTypeId()
        key = eid_int(tid)
        if key not in pt_cache:
            pt_cache[key] = el_name(doc.GetElement(tid))
        tally_add(tipos, pt_cache[key])

        pd = bip_param(el, 'RBS_PIPE_DIAMETER_PARAM')
        if pdouble_pos(pd):
            cov['con_diametro_mayor_que_cero'] += 1
        tally_add(diam, ptext(doc, pd) or '(sin diametro)')
        if pdouble_pos(bip_param(el, 'CURVE_ELEM_LENGTH')):
            cov['con_longitud_mayor_que_cero'] += 1

        mat_bip = ptext(doc, bip_param(el, 'MATERIAL_ID_PARAM'))
        if not blank(mat_bip):
            cov['con_material_BIP'] += 1
        seg = g('PipeSegment', lambda el=el: getattr(el, 'PipeSegment', None))
        mat_seg = None
        if seg is not None:
            mat_seg = g('seg.MaterialId', lambda seg=seg: el_name(doc.GetElement(seg.MaterialId)))
            if not blank(mat_seg):
                cov['con_material_por_segmento'] += 1

        lv = level_name(doc, el)
        if not blank(lv):
            cov['con_nivel'] += 1
        tally_add(niveles, lv or '(sin nivel)')

        tally_add(fases_c, ptext(doc, bip_param(el, 'PHASE_CREATED')) or '(sin fase)')
        dem = ptext(doc, bip_param(el, 'PHASE_DEMOLISHED'))
        if not blank(dem):
            tally_add(fases_d, dem)
        if doc.IsWorkshared:
            tally_add(worksets, g('workset', lambda el=el: u_(doc.GetWorksetTable().GetWorkset(el.WorksetId).Name)))
        do = g('designopt', lambda el=el: el.DesignOption)
        if do is not None:
            tally_add(opciones, el_name(do))

        conns = g('conectores', lambda el=el: get_connectors(el), [])
        if not conns:
            cov['sin_conectores'] += 1
        elif any(not g('isconn', lambda c=c: c.IsConnected, True) for c in conns):
            cov['con_algun_conector_libre'] += 1

        if len(muestra) < MUESTRA_TUBERIAS:
            muestra.append({
                'ElementId': eid_int(el.Id), 'UniqueId': u_(el.UniqueId),
                'clase': u_(el.GetType().Name), 'tipo': pt_cache[key],
                'clasificacion_sistema': cls, 'tipo_sistema': stype,
                'nombre_sistema': sname, 'abreviatura': abbr,
                'MEPSystem': g('mepname', lambda mep=mep: u_(mep.Name) if mep is not None else None),
                'diametro_texto': ptext(doc, pd),
                'longitud_texto': ptext(doc, bip_param(el, 'CURVE_ELEM_LENGTH')),
                'material_BIP': mat_bip, 'material_segmento': mat_seg, 'nivel': lv,
                'conectores': len(conns),
            })

    r['cobertura'] = cov
    r['por_clase_API'] = tally_rows(clases, 'clase')
    r['por_tipo_de_tuberia'] = tally_rows(tipos, 'tipo')
    r['por_clasificacion_tipo_abreviatura'] = tally_rows(combos, 'clasificacion_tipo_abreviatura')
    r['por_diametro_texto'] = tally_rows(diam, 'diametro')
    r['por_nivel'] = tally_rows(niveles, 'nivel')
    r['por_fase_creacion'] = tally_rows(fases_c, 'fase')
    r['por_fase_demolicion'] = tally_rows(fases_d, 'fase')
    if worksets:
        r['por_workset'] = tally_rows(worksets, 'workset')
    if opciones:
        r['por_opcion_de_diseno'] = tally_rows(opciones, 'opcion')
    r['ids_sin_MEPSystem_primeros_200'] = sin_sistema_ids
    r['muestra'] = muestra

    # Inventario de parametros reales (nombres localizados incluidos).
    stride = max(1, len(pipes) // MAX_PARAM_SCAN) if pipes else 1
    union = {}
    escaneadas = 0
    for el in pipes[::stride]:
        escaneadas += 1
        for p in el.Parameters:
            try:
                nm = u_(p.Definition.Name)
                row = union.get(nm)
                if row is None:
                    b = getattr(p.Definition, 'BuiltInParameter', None)
                    row = {'nombre': nm, 'almacenamiento': u_(p.StorageType),
                           'compartido': bool(p.IsShared),
                           'builtin': u_(b) if b is not None else None, 'con_valor': 0}
                    union[nm] = row
                if p.HasValue:
                    row['con_valor'] += 1
            except Exception as ex:
                log_error('param_union', ex)
    r['parametros_inventario'] = {
        'tuberias_escaneadas': escaneadas,
        'filas': sorted(union.values(), key=lambda x: x['nombre'].lower()),
        'candidatos_material': [n for n in union if 'material' in n.lower()],
        'candidatos_sistema': [n for n in union if 'sistema' in n.lower() or 'system' in n.lower()],
        'candidatos_nivel': [n for n in union if 'nivel' in n.lower() or 'level' in n.lower()],
    }
    return r


def analyze_family_category(doc, els):
    r = {'total_elementos_categoria': len(els)}
    fams, tamano, niveles, cls_param, cls_conn, mep_conn = {}, {}, {}, {}, {}, {}
    cov = {'con_clasificacion_parametro': 0, 'con_algun_conector_con_sistema': 0,
           'sin_conectores_de_tuberia': 0, 'con_tamano': 0, 'con_nivel': 0}
    muestra = []
    for el in els:
        tally_add(fams, family_and_type(doc, el))
        cls = ptext(doc, bip_param(el, 'RBS_SYSTEM_CLASSIFICATION_PARAM'))
        if not blank(cls):
            cov['con_clasificacion_parametro'] += 1
            tally_add(cls_param, cls)
        sz = ptext(doc, bip_param(el, 'RBS_CALCULATED_SIZE'))
        if not blank(sz):
            cov['con_tamano'] += 1
        tally_add(tamano, sz or '(sin tamano)')
        lv = level_name(doc, el)
        if not blank(lv):
            cov['con_nivel'] += 1
        tally_add(niveles, lv or '(sin nivel)')

        conns = g('conectores', lambda el=el: get_connectors(el), [])
        tipos = set()
        con_sis = False
        for c in conns:
            try:
                if c.Domain != DB.Domain.DomainPiping:
                    continue
                pst = g('c.PipeSystemType', lambda c=c: u_(c.PipeSystemType))
                if pst:
                    tipos.add(pst)
                ms = g('c.MEPSystem', lambda c=c: c.MEPSystem)
                if ms is not None:
                    con_sis = True
                    tally_add(mep_conn, g('msname', lambda ms=ms: u_(ms.Name)))
            except Exception as ex:
                log_error('conectores_cat', ex)
        if not tipos:
            cov['sin_conectores_de_tuberia'] += 1
        if con_sis:
            cov['con_algun_conector_con_sistema'] += 1
        tally_add(cls_conn, tuple(sorted(tipos)) if tipos else ('(sin conectores de tuberia)',))

        if len(muestra) < MUESTRA_TUBERIAS:
            muestra.append({
                'ElementId': eid_int(el.Id), 'UniqueId': u_(el.UniqueId),
                'familia_y_tipo': family_and_type(doc, el), 'tamano': sz, 'nivel': lv,
                'clasificacion_parametro': cls,
                'PipeSystemType_conectores': sorted(tipos),
            })
    r['cobertura'] = cov
    r['por_familia_y_tipo'] = tally_rows(fams, 'familia_y_tipo')
    r['por_tamano'] = tally_rows(tamano, 'tamano')
    r['por_nivel'] = tally_rows(niveles, 'nivel')
    r['por_clasificacion_parametro'] = tally_rows(cls_param, 'clasificacion')
    r['por_PipeSystemType_de_conectores'] = tally_rows(cls_conn, 'PipeSystemType')
    r['por_sistema_en_conectores'] = tally_rows(mep_conn, 'sistema')
    r['muestra'] = muestra
    return r


def collect_links(doc):
    rows = []
    for li in of_class(doc, DB.RevitLinkInstance):
        row = {'instancia': el_name(li), 'tipo': g('linktype', lambda li=li: el_name(doc.GetElement(li.GetTypeId())))}
        ld = g('linkdoc', lambda li=li: li.GetLinkDocument())
        if ld is None:
            row['cargado'] = False
        else:
            row['cargado'] = True
            row['titulo'] = u_(ld.Title)
            counts = {}
            for nm in CATEGORIAS_SANITARIAS:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    counts[nm] = g('lc_' + nm, lambda bic=bic, ld=ld: DB.FilteredElementCollector(ld).OfCategory(bic).WhereElementIsNotElementType().GetElementCount())
            row['elementos_sanitarios_en_vinculo'] = counts
        rows.append(row)
    return rows


def collect_warnings(doc):
    ws = doc.GetWarnings()
    t = {}
    for w in ws:
        tally_add(t, g('warn', lambda w=w: u_(w.GetDescriptionText())))
    return {'total': len(ws), 'por_descripcion': tally_rows(t, 'advertencia', 15)}


# ----------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------
def report_dir():
    base = os.environ.get('CLAUDE_BIM_REPORTS')
    if not base:
        docs = g('MyDocuments', lambda: u_(System.Environment.GetFolderPath(
            System.Environment.SpecialFolder.MyDocuments)))
        if blank(docs):
            docs = os.path.join(os.path.expanduser('~'), 'Documents')
        base = os.path.join(docs, 'ClaudeRevit', 'reports')
    try:
        if not os.path.isdir(base):
            os.makedirs(base)
        return base
    except Exception as ex:
        log_error('report_dir', ex)
        return System.IO.Path.GetTempPath()


def main(uiapp):
    t0 = time.time()
    uidoc = uiapp.ActiveUIDocument
    if uidoc is None:
        out('No hay ningun documento abierto en Revit. Abre el RVT y vuelve a ejecutar.')
        return None
    doc = uidoc.Document
    modificado_antes = doc.IsModified

    rep = {'meta': {
        'script': 'Diagnostico_Modelo_pyRevit.py', 'version_script': SCRIPT_VERSION,
        'fecha': datetime.datetime.now().isoformat(),
        'modo': 'SOLO LECTURA (sin Transaction)',
    }}

    def step(nombre, fn):
        out('  [%5.1fs] %s ...' % (time.time() - t0, nombre))
        rep[nombre] = g(nombre, fn)

    out('CLAUDE BIM - Fase 0 - Diagnostico del modelo (solo lectura)')
    step('entorno', lambda: collect_environment(uiapp))
    step('documento', lambda: collect_document(uiapp, doc))
    step('unidades', lambda: collect_units(doc))
    step('niveles', lambda: collect_levels(doc))
    step('vistas_y_schedules', lambda: collect_views_and_schedules(doc))
    step('categorias', lambda: collect_categories(doc))
    step('sistemas_mep', lambda: collect_mep_systems(doc))
    pipes = g('tuberias_collect', lambda: collect_cat(doc, 'OST_PipeCurves'), []) or []
    step('tuberias', lambda: analyze_pipes(doc, pipes))
    for key, bic in (('accesorios_de_tuberia', 'OST_PipeFitting'),
                     ('accesorios_valvulas_etc', 'OST_PipeAccessory'),
                     ('aparatos_sanitarios', 'OST_PlumbingFixtures'),
                     ('equipos_mecanicos', 'OST_MechanicalEquipment')):
        els = g('collect_' + key, lambda bic=bic: collect_cat(doc, bic), []) or []
        step(key, lambda els=els: analyze_family_category(doc, els))
    step('vinculos_rvt', lambda: collect_links(doc))
    step('advertencias_del_modelo', lambda: collect_warnings(doc))

    modificado_despues = doc.IsModified
    rep['verificacion_solo_lectura'] = {
        'IsModified_antes': modificado_antes, 'IsModified_despues': modificado_despues,
        'el_script_modifico_el_modelo': bool(modificado_despues and not modificado_antes),
    }
    rep['errores_del_script'] = ERRORS
    rep['meta']['segundos'] = round(time.time() - t0, 1)

    base = report_dir()
    nombre = 'diag_modelo_%s.json' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta = os.path.join(base, nombre)
    with open(ruta, 'w') as fh:
        fh.write(json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=True))

    imprimir_resumen(rep, ruta)
    return ruta


def imprimir_resumen(rep, ruta):
    def sec(k):
        return rep.get(k) or {}
    out('')
    out('=' * 70)
    rv = sec('entorno').get('revit', {})
    out('Revit      : %s (build %s)' % (rv.get('VersionName'), rv.get('VersionBuild')))
    out('pyRevit    : %s | motor: %s' % (sec('entorno').get('pyrevit', {}).get('version'),
                                         sec('entorno').get('python', {}).get('implementacion')))
    dc = sec('documento')
    out('Documento  : %s' % dc.get('titulo'))
    out('Ruta       : %s' % dc.get('ruta'))
    out('Coincide con "%s": %s' % (ARCHIVO_ESPERADO, dc.get('coincide_con_archivo_esperado')))
    out('Unidades   : %s' % sec('unidades').get('longitud_proyecto'))
    out('Categorias sanitarias (nro. de elementos):')
    for k, v in sorted((sec('categorias').get('categorias_sanitarias') or {}).items()):
        out('    %-26s %s' % (k, v))
    tub = sec('tuberias')
    out('Tuberias: %s | sin MEPSystem: %s' % (tub.get('total_elementos_categoria'),
                                              (tub.get('cobertura') or {}).get('sin_MEPSystem')))
    out('Clasificacion / tipo de sistema / abreviatura (tuberias):')
    for fila in (tub.get('por_clasificacion_tipo_abreviatura') or {}).get('filas', [])[:15]:
        out('    %5s  %s' % (fila['cantidad'], ' | '.join(fila['clasificacion_tipo_abreviatura'])))
    out('Vinculos RVT: %s' % len(rep.get('vinculos_rvt') or []))
    vr = rep.get('verificacion_solo_lectura') or {}
    out('El script modifico el modelo: %s' % vr.get('el_script_modifico_el_modelo'))
    out('Errores del script (no fatales): %s' % len(rep.get('errores_del_script') or []))
    out('JSON generado: %s' % ruta)
    out('=' * 70)


_uiapp = globals().get('__revit__')
if _uiapp is None:
    out('Este script debe ejecutarse DENTRO de Revit mediante pyRevit '
        '(la variable __revit__ no existe en este entorno).')
else:
    main(_uiapp)
