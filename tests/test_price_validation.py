import pytest
from app.price_validation import validate_prices
from app.models import PackingListRow, PriceValidationError

@pytest.fixture
def mock_price_list(monkeypatch):
    """模拟价格清单数据"""
    price_map = {
        "A001": 10.50,
        "B002": 20.75,
        "C003": 30.00
    }
    
    def mock_load_price_list():
        return price_map
    
    monkeypatch.setattr("app.price_validation._load_price_list", mock_load_price_list)
    return price_map

def test_validate_matching_prices(mock_price_list):
    """测试价格匹配的情况"""
    rows = [
        PackingListRow("A001", "Item A", 100, 10.50),
        PackingListRow("B002", "Item B", 200, 20.75)
    ]
    
    errors = validate_prices(rows)
    assert len(errors) == 0

def test_validate_mismatched_prices(mock_price_list):
    """测试价格不匹配的情况"""
    rows = [
        PackingListRow("A001", "Item A", 100, 11.00),  # 价格不匹配
        PackingListRow("B002", "Item B", 200, 20.75)   # 价格匹配
    ]
    
    errors = validate_prices(rows)
    assert len(errors) == 1
    assert isinstance(errors[0], PriceValidationError)
    assert errors[0].item_no == "A001"
    assert errors[0].expected == 10.50
    assert errors[0].found == 11.00
    assert errors[0].difference == 0.50

def test_validate_unknown_item(mock_price_list):
    """测试未知物料编号的情况"""
    rows = [
        PackingListRow("X999", "Unknown Item", 100, 10.00)
    ]
    
    errors = validate_prices(rows)
    assert len(errors) == 1
    assert errors[0].item_no == "X999"
    assert errors[0].expected is None

def test_validate_empty_list():
    """测试空列表的情况"""
    errors = validate_prices([])
    assert len(errors) == 0
