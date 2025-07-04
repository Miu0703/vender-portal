from typing import List, Dict, Optional
import pandas as pd
import os
from .models import PackingListRow, PriceValidationError

_price_cache: Optional[Dict[str, float]] = None

def _load_price_list() -> Dict[str, float]:
    """Load price list from backend-maintained file (cache results)"""
    global _price_cache
    if _price_cache is None:
        try:
            # Try backend-maintained price list first
            price_file = "data/price_list.xlsx"
            if os.path.exists(price_file):
                df = pd.read_excel(price_file)
                # Map actual column names to expected format
                _price_cache = df.set_index("Item Number")["Vendor Purchase Price"].to_dict()
            else:
                # Fallback to original file if backend file doesn't exist
                df = pd.read_excel("Item price column G.xlsx")
                _price_cache = df.set_index("Item Number")["Vendor Purchase Price"].to_dict()
        except FileNotFoundError:
            # Return empty dict if no price list file found
            _price_cache = {}
        except Exception as e:
            print(f"Warning: Could not load price list: {e}")
            _price_cache = {}
    return _price_cache

def validate_prices(rows: List[PackingListRow]) -> List[PriceValidationError]:
    """Validate prices in packing list against backend price list"""
    errors = []
    
    for row in rows:
        # Skip validation if item has no prices to compare
        if not row.has_packing_list_price or row.system_price is None or row.packing_list_price is None:
            continue
            
        # Check for price mismatch (with tolerance)
        if abs(row.packing_list_price - row.system_price) > 0.01:
            errors.append(PriceValidationError(
                item_no=row.item_no,
                expected=row.system_price,
                found=row.packing_list_price,
                message=f"Price mismatch for {row.item_no}: Packing List ${row.packing_list_price:.2f} vs System ${row.system_price:.2f}"
            ))
    
    return errors

def get_item_price(item_no: str) -> Optional[float]:
    """Get price for a specific item from backend price list"""
    price_map = _load_price_list()
    return price_map.get(item_no)

def enrich_with_prices(rows: List[PackingListRow]) -> List[PackingListRow]:
    """Enrich packing list rows with prices from backend price list"""
    price_map = _load_price_list()
    enriched_rows = []
    
    for row in rows:
        # Get system price from price list
        system_price = price_map.get(row.item_no)
        
        # Create enriched row with both prices
        enriched_row = PackingListRow(
            item_no=row.item_no,
            description=row.description,
            qty=row.qty,
            packing_list_price=row.packing_list_price,
            system_price=system_price
        )
        enriched_rows.append(enriched_row)
    
    return enriched_rows
