import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import structural_beam_analysis, slab_analysis, column_analysis, foundation_analysis

def test_beam_analysis_positive():
    """اختبار تحليل كمرة بقيم صحيحة"""
    result = structural_beam_analysis(5.0, 2.0)
    assert result["success"] is True
    assert len(result["scenarios"]) == 3
    # التحقق من أن السيناريو الأول له تكلفة موجبة
    assert result["scenarios"][0]["cost_egp"] > 0

def test_beam_analysis_zero_load():
    """اختبار تحليل كمرة بحمل صفري"""
    result = structural_beam_analysis(5.0, 0.0)
    assert result["success"] is True
    # حتى مع الحمل الصفري، يجب أن ينتج تصميماً
    assert result["scenarios"][0]["cost_egp"] >= 0

def test_slab_analysis():
    """اختبار تحليل بلاطة"""
    result = slab_analysis(4.0, 6.0)
    assert result["success"] is True
    assert "بلاطة" in result["results"]["explanation"]

def test_column_analysis():
    """اختبار تحليل عمود"""
    result = column_analysis(100.0, 3.0)
    assert result["success"] is True
    assert "عمود" in result["results"]["explanation"]

def test_foundation_analysis():
    """اختبار تحليل أساس"""
    result = foundation_analysis(200.0, 150.0)
    assert result["success"] is True
    assert "قاعدة" in result["results"]["explanation"]