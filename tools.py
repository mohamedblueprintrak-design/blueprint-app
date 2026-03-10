import logging
import math
import base64
import io
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

logger = logging.getLogger("tools")

UNIT_PRICES = {"concrete_m3": 1000, "steel_ton": 35000}

# ---------- تحديث أسعار المواد من قاعدة البيانات ----------
def update_unit_prices_from_db(project_id):
    from database import SessionLocal, ProjectSettings
    db = SessionLocal()
    try:
        settings = db.query(ProjectSettings).filter(ProjectSettings.project_id == project_id).first()
        if settings:
            global UNIT_PRICES
            UNIT_PRICES["concrete_m3"] = settings.concrete_price
            UNIT_PRICES["steel_ton"] = settings.steel_price
    except:
        pass
    finally:
        db.close()

# --- دوال التصميم الإنشائي ---
def structural_beam_analysis(length, load):
    try:
        L = length
        w = load * 10
        M = (w * L**2) / 8
        scenarios = [
            _calc_beam(L, M, 250, int((L/12.0)*1000), "💰 Economic"),
            _calc_beam(L, M, 250, int((L/18.0)*1000), "🪶 Lightweight"),
            _calc_beam(L, M, 300, int((L/10.0)*1000), "🛡️ Safe")
        ]
        return {"success": True, "scenarios": scenarios}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _calc_beam(L, M, w, d, label):
    d_eff = d - 40
    if d_eff <= 0:
        d_eff = 100
    As_req = (M * 1e6) / (0.87 * 360 * d_eff)
    bars = math.ceil(As_req / 201)
    
    vol = (w/1000) * (d/1000) * L
    steel_w = (201 * bars * L * 7.85) / 1000000
    cost = (vol * UNIT_PRICES['concrete_m3']) + (steel_w * UNIT_PRICES['steel_ton'])
    
    return {
        "label": label,
        "width_mm": w,
        "depth_mm": d,
        "steel_bars": f"{bars} T16",
        "cost_egp": round(cost),
        "raw_values": {
            "type": "beam",
            "depth_mm": d,
            "length_m": L,
            "steel_ratio_percent": round((As_req/(w*d_eff))*100, 2)
        }
    }

def slab_analysis(length_short, length_long, thickness=0):
    try:
        ratio = length_long / length_short
        type_str = "Two-Way" if ratio < 2 else "One-Way"
        t = thickness if thickness > 0 else (length_short * 1000 / 30)
        load = 15.0
        M = (load * length_short**2) / 8
        As_req = (M * 1e6) / (0.87 * 360 * (t-20))
        return {
            "success": True,
            "results": {
                "explanation": f"🔲 **بلاطة {type_str}**: السمك المطلوب {t:.0f} مم، الحديد التقريبي {As_req/201:.2f} قضيب/متر",
                "raw_values": {"type": "slab", "thickness_mm": t}
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def column_analysis(axial_load, height):
    try:
        Pu = axial_load * 1.5 * 10
        Ag = Pu / (0.4 * 30)
        side = math.sqrt(Ag) * 1000
        return {
            "success": True,
            "results": {
                "explanation": f"🏗️ **عمود**: المقاس المقترح {side:.0f}x{side:.0f} مم للحمل {axial_load} ك.ن",
                "raw_values": {"type": "column"}
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def foundation_analysis(load, soil_capacity):
    try:
        area = (load * 1.5) / (soil_capacity * 10)
        side = math.sqrt(area)
        thickness = side * 0.5
        return {
            "success": True,
            "results": {
                "explanation": f"🧱 **قاعدة**: الأبعاد {side:.2f}x{side:.2f} متر، سمك {thickness*100:.0f} سم",
                "raw_values": {"type": "foundation"}
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def retaining_wall_analysis(height, soil_load):
    try:
        base_thickness = 0.1 * height + 0.3
        base_width = 0.5 * height
        steel_main = f"16mm كل 200 مم"
        return {
            "success": True,
            "results": {
                "explanation": f"🧱 **جدار استنادي**: ارتفاع {height} م، عرض القاعدة {base_width:.2f} م، سمك القاعدة {base_thickness:.2f} م، تسليح رئيسي {steel_main}",
                "raw_values": {"type": "retaining_wall", "height": height, "base_width": base_width, "base_thickness": base_thickness}
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def stair_analysis(floor_height, riser=0.17, tread=0.30):
    try:
        number_of_risers = floor_height / riser
        number_of_treads = number_of_risers - 1
        flight_length = number_of_treads * tread
        thickness = flight_length * 0.03
        return {
            "success": True,
            "results": {
                "explanation": f"🪜 **سلم**: عدد القوائم {number_of_risers:.0f}، طول الباي {flight_length:.2f} م، السمك التقريبي {thickness*100:.0f} مم",
                "raw_values": {"type": "stair", "risers": number_of_risers, "flight_length": flight_length, "thickness_mm": thickness*1000}
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- دوال الحصر (BOQ) ---
def boq_steel_calculator(d, l, c):
    wt = (d**2 / 162.2 * l * c) / 1000
    cost = wt * UNIT_PRICES['steel_ton']
    return {"success": True, "item": {"description": f"Steel {d}mm", "unit": "Ton", "quantity": round(wt,3), "total_price": round(cost)}}

def boq_concrete_calculator(v):
    cost = v * UNIT_PRICES['concrete_m3']
    return {"success": True, "item": {"description": "Concrete", "unit": "M3", "quantity": v, "total_price": round(cost)}}

# --- الرسم و CAD ---
def generate_beam_dxf(w, d, bars):
    try:
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_lwpolyline([(0,0), (w,0), (w,d), (0,d)], close=True)
        for i in range(bars):
            x = 40 + (w - 80) / (bars + 1) * (i + 1)
            msp.add_circle((x, 50), 8)
        stream = io.BytesIO()
        doc.write(stream)
        stream.seek(0)
        return base64.b64encode(stream.read()).decode('utf-8')
    except:
        return None

def draw_beam_section(w, d, bars):
    try:
        fig, ax = plt.subplots(1, figsize=(6,4))
        ax.add_patch(patches.Rectangle((0,0), w, d, facecolor='#f0f0f0', edgecolor='black'))
        if bars > 0:
            sp = (w - 80) / (bars + 1)
            for i in range(bars):
                ax.add_patch(patches.Circle((40 + sp*(i+1), 50), 10, color='blue'))
        ax.set_aspect('equal')
        ax.set_xlim(0, w)
        ax.set_ylim(0, d)
        ax.set_title(f"Beam Section {w}x{d} mm")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        img = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        return img
    except:
        return None

def get_site_checklist(work_type):
    data = {
        "نجارة": ["مراجعة أبعاد", "رأسية الأعمدة"],
        "حدادة": ["أقطار الحديد", "التوشيك"],
        "صب": ["التربيط", "الدمك"],
        "عمود": ["الرأسية", "أماكن الوصلات"],
        "قاعدة": ["النظافة", "الغطاء الخرساني"]
    }
    items = data.get(work_type, ["عام"])
    text = f"📋 **تشك ليست {work_type}:**\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item}\n"
    return {"success": True, "items": items, "text": text}
