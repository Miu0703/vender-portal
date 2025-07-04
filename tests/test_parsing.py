import os
import pytest
import pandas as pd
from app.parsing import parse_packing_list
from app.models import PackingListRow

@pytest.fixture
def sample_excel(tmp_path):
    """创建一个样例Excel文件用于测试"""
    data = {
        "ItemNo": ["A001", "B002"],
        "Description": ["Item A", "Item B"],
        "Qty": [100, 200],
        "UnitPrice": [10.5, 20.75]
    }
    df = pd.DataFrame(data)
    filepath = tmp_path / "sample.xlsx"
    df.to_excel(filepath, index=False)
    return str(filepath)

def test_parse_valid_excel(sample_excel):
    """测试解析有效的Excel文件"""
    rows = parse_packing_list(sample_excel)
    assert len(rows) == 2
    assert isinstance(rows[0], PackingListRow)
    assert rows[0].item_no == "A001"
    assert rows[0].description == "Item A"
    assert rows[0].qty == 100
    assert rows[0].unit_price == 10.5

def test_parse_missing_columns(tmp_path):
    """测试缺少必需列的情况"""
    data = {
        "ItemNo": ["A001"],
        "Description": ["Item A"]
        # 缺少 Qty 和 UnitPrice
    }
    df = pd.DataFrame(data)
    filepath = tmp_path / "invalid.xlsx"
    df.to_excel(filepath, index=False)
    
    with pytest.raises(ValueError) as exc_info:
        parse_packing_list(str(filepath))
    assert "Missing columns" in str(exc_info.value)

def test_parse_empty_excel(tmp_path):
    """测试空Excel文件"""
    df = pd.DataFrame(columns=["ItemNo", "Description", "Qty", "UnitPrice"])
    filepath = tmp_path / "empty.xlsx"
    df.to_excel(filepath, index=False)
    
    rows = parse_packing_list(str(filepath))
    assert len(rows) == 0

def test_parse_invalid_data_types(tmp_path):
    """测试数据类型无效的情况"""
    data = {
        "ItemNo": ["A001"],
        "Description": ["Item A"],
        "Qty": ["invalid"],  # 应该是数字
        "UnitPrice": [10.5]
    }
    df = pd.DataFrame(data)
    filepath = tmp_path / "invalid_types.xlsx"
    df.to_excel(filepath, index=False)
    
    with pytest.raises(ValueError) as exc_info:
        parse_packing_list(str(filepath))
    assert "Invalid data type" in str(exc_info.value)
