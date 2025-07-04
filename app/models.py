from flask_login import UserMixin
from typing import List, Dict, Optional
from dataclasses import dataclass

class User(UserMixin):
    def __init__(self, username: str):
        self._id = username
        self._is_active = True

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_active(self) -> bool:
        return self._is_active

@dataclass
class PackingListRow:
    item_no: str
    description: str
    qty: int
    packing_list_price: Optional[float]  # Price from packing list (None if no price)
    system_price: Optional[float]  # Price from system database

    @property
    def has_packing_list_price(self) -> bool:
        """Check if packing list has a price for this item"""
        return self.packing_list_price is not None and self.packing_list_price > 0

    @property
    def price_comparison_status(self) -> str:
        """Get price comparison status"""
        if not self.has_packing_list_price:
            return "no_price"
        
        if self.system_price is None:
            return "no_system_price"
        
        # At this point, both prices are guaranteed to be not None
        assert self.packing_list_price is not None
        assert self.system_price is not None
        
        # Allow small tolerance for price comparison (0.01)
        if abs(self.packing_list_price - self.system_price) <= 0.01:
            return "match"
        else:
            return "mismatch"

    @property
    def status_display(self) -> str:
        """Get display text for price status"""
        status = self.price_comparison_status
        if status == "no_price":
            return "⚠️ Packing List does not contain price"
        elif status == "match":
            return "✅ Price Match"
        elif status == "mismatch":
            return "❌ Price Mismatch"
        else:
            return "⚠️ System price not found"

    @property
    def unit_price(self) -> float:
        """Backward compatibility - returns effective price"""
        if self.has_packing_list_price and self.packing_list_price is not None:
            return self.packing_list_price
        elif self.system_price is not None:
            return self.system_price
        else:
            return 0.0

    def to_dict(self) -> Dict:
        return {
            "sku": self.item_no,
            "item_no": self.item_no,  # Keep for backward compatibility
            "ItemNo": self.item_no,  # Keep for backward compatibility
            "description": self.description,
            "Description": self.description,  # Keep for backward compatibility
            "quantity": self.qty,
            "Qty": self.qty,  # Keep for backward compatibility
            "system_unit_price": self.system_price,
            "SystemPrice": self.system_price,  # Keep for backward compatibility
            "packing_list_unit_price": self.packing_list_price,
            "PackingListPrice": self.packing_list_price,  # Keep for backward compatibility
            "price_match": True if self.price_comparison_status == "match" else (False if self.price_comparison_status == "mismatch" else None),
            "note": self.status_display,
            "UnitPrice": self.unit_price,  # For backward compatibility
            "HasPackingListPrice": self.has_packing_list_price,
            "PriceComparisonStatus": self.price_comparison_status,
            "StatusDisplay": self.status_display
        }

@dataclass
class PriceValidationError:
    item_no: str
    expected: Optional[float]
    found: float
    message: Optional[str] = None

    @property
    def difference(self) -> Optional[float]:
        if self.expected is None:
            return None
        return self.found - self.expected

    def to_dict(self) -> Dict:
        return {
            "ItemNo": self.item_no,
            "expected": self.expected,
            "found": self.found,
            "difference": self.difference,
            "message": self.message
        }

class ProcessingResult:
    def __init__(
        self,
        rows: List[PackingListRow],
        validation_errors: Optional[List[PriceValidationError]] = None
    ):
        self.rows = rows
        self.validation_errors = validation_errors or []

    def to_dict(self) -> Dict:
        return {
            "status": "success",
            "data": {
                "rows": [row.to_dict() for row in self.rows],
                "total": len(self.rows)
            },
            "validation": {
                "price_mismatches": [error.to_dict() for error in self.validation_errors]
            }
        }
