import logging
logger = logging.getLogger("rules_engine")

def check_structural_safety(results: dict):
    element_type = results.get("type", "beam")

    if element_type == "beam":
        return check_beam_safety(results)
    elif element_type == "slab":
        return check_slab_safety(results)

    return {"is_safe": True, "warnings": [], "suggestions": []}

def check_beam_safety(results: dict):
    warnings = []
    suggestions = []
    is_safe = True

    steel_ratio = results.get("steel_ratio_percent", 0)
    depth = results.get("depth_mm", 0)
    length = results.get("length_m", 0)

    if steel_ratio > 2.5:
        warnings.append(f"⚠️ تحذير: نسبة التسليح عالية جداً ({steel_ratio}%)، قد تحدث تشققات.")
        suggestions.append("💰 اقتراح: زيادة عمق الكمرة لتقليل نسبة الحديد.")
        is_safe = False
    elif steel_ratio < 0.2:
        warnings.append("⚠️ تحذير: نسبة التسليح منخفضة جداً.")
        suggestions.append("💡 اقتراح: مراجعة الحسابات أو إضافة حديد إضافي.")

    if length > 0 and depth > 0:
        depth_span_ratio = depth / (length * 1000)
        if depth_span_ratio < 1/15:
            warnings.append("⚠️ الكمرة نحيفة جداً (نسبة العمق/الطول صغيرة).")
            suggestions.append("📏 اقتراح: زيادة العمق لتحسين المقاومة.")
            is_safe = False

    return {"is_safe": is_safe, "warnings": warnings, "suggestions": suggestions}

def check_slab_safety(results: dict):
    return {"is_safe": True, "warnings": [], "suggestions": []}