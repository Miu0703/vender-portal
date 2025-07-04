from typing import List
import pandas as pd
import re
import os
from .models import PackingListRow

# Add PDF parsing support
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfplumber not installed. PDF parsing will be disabled.")

def parse_packing_list(filepath: str) -> List[PackingListRow]:
    """Parse packing list file - supports Excel (.xlsx, .xls) and PDF formats"""
    file_ext = os.path.splitext(filepath)[1].lower()
    
    if file_ext == '.pdf':
        if not PDF_SUPPORT:
            raise ValueError("PDF parsing not supported. Please install pdfplumber.")
        return parse_pdf_packing_list(filepath)
    elif file_ext in ['.xlsx', '.xls']:
        return parse_excel_packing_list(filepath)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

def parse_pdf_packing_list(filepath: str) -> List[PackingListRow]:
    """Parse PDF packing list file with improved text extraction and deduplication"""
    import re
    from collections import defaultdict
    
    rows = []
    
    with pdfplumber.open(filepath) as pdf:
        # Extract text from all pages and combine
        full_text = ""
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                full_text += f"\n--- PAGE {page_num + 1} ---\n" + page_text + "\n"
                print(f"Debug: Extracted {len(page_text)} characters from page {page_num + 1}")
    
    print(f"Debug: Total extracted text length: {len(full_text)}")
    
    # Split into lines and clean up
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    # Try to identify different sections (Packing List, Invoice)
    packing_section_lines = []
    invoice_section_lines = []
    
    current_section = None
    packing_table_start = None
    packing_table_end = None
    invoice_table_start = None
    invoice_table_end = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Detect section headers
        if 'packing list' in line_lower and not current_section:
            current_section = 'packing'
            print(f"Debug: Found Packing List section at line {i}")
        elif any(x in line_lower for x in ['commercial invoice', 'invoice']) and 'packing' not in line_lower:
            current_section = 'invoice'
            print(f"Debug: Found Invoice section at line {i}")
        
        if current_section == 'packing':
            if any(x in line_lower for x in ['packing no', 'description', 'quantity', 'container']) and 'unit price' not in line_lower:
                packing_table_start = i
                print(f"Debug: Found Packing List table header at line {i}: {line}")
            elif packing_table_start and any(x in line_lower for x in ['total:', 'subtotal']):
                packing_table_end = i
                print(f"Debug: Found Packing List table end at line {i}")
            
            if packing_table_start is not None:
                if packing_table_end is None or i <= packing_table_end:
                    packing_section_lines.append(line)
        
        elif current_section == 'invoice':
            # Look for invoice table headers with more flexible matching
            # Lines like "Container Quantity UNIT PRICE AMOUNT MEASUREM"
            # or "Packing No Item Description Remark INVOICE NO."
            # or "NO.&Seal NO. (PCS) (USD) (USD) ENT (CBM)"
            if ((any(x in line_lower for x in ['packing no', 'item', 'description', 'container']) and 
                 any(x in line_lower for x in ['unit price', 'amount', 'quantity'])) or
                (any(x in line_lower for x in ['pcs', 'usd']) and 
                 any(x in line_lower for x in ['seal', 'cbm', 'ent']))):
                invoice_table_start = i
                print(f"Debug: Found Invoice table header at line {i}: {line}")
            elif invoice_table_start and any(x in line_lower for x in ['total:', 'subtotal', 'fob', 'say total']):
                invoice_table_end = i
                print(f"Debug: Found Invoice table end at line {i}")
            
            if invoice_table_start is not None:
                if invoice_table_end is None or i <= invoice_table_end:
                    invoice_section_lines.append(line)
    
    print(f"Debug: Packing section lines: {len(packing_section_lines)}")
    print(f"Debug: Invoice section lines: {len(invoice_section_lines)}")
    
    # Parse items from packing list section
    items_from_packing = parse_pdf_packing_section(packing_section_lines)
    print(f"Debug: Found {len(items_from_packing)} items from packing section")
    
    # Parse prices from invoice section
    prices_from_invoice = parse_pdf_invoice_section(invoice_section_lines)
    print(f"Debug: Found {len(prices_from_invoice)} prices from invoice section")
    
    # Combine items with prices
    final_items = {}
    
    # Start with items from packing list
    for item in items_from_packing:
        final_items[item['item_no']] = item
    
    # Add prices from invoice
    for item_no, price in prices_from_invoice.items():
        if item_no in final_items:
            final_items[item_no]['price'] = price
        else:
            # Item found in invoice but not in packing list
            final_items[item_no] = {
                'item_no': item_no,
                'description': f"Item {item_no}",  # Fallback description
                'qty': 1,
                'price': price
            }
    
    # Convert to PackingListRow objects
    for item_data in final_items.values():
        if item_data['item_no']:
            rows.append(PackingListRow(
                item_no=item_data['item_no'],
                description=item_data['description'],
                qty=item_data['qty'],
                packing_list_price=item_data.get('price'),
                system_price=None  # Will be enriched later
            ))
    
    print(f"Debug: Final result: {len(rows)} items with combined packing list and invoice data")
    return rows

def parse_pdf_packing_section(lines: List[str]) -> List[dict]:
    """Parse items and quantities from packing list section"""
    items = []
    seen_items = set()
    
    for line in lines:
        print(f"Debug: Processing packing line: '{line}'")
        
        # Look for item numbers
        item_matches = re.findall(r'#([A-Z0-9]+)', line)
        
        for item_no in item_matches:
            if item_no in seen_items:
                continue
                
            print(f"Debug: Found item {item_no} in packing section")
            
            # Extract description - stop before large numbers
            desc_pattern = f'#{item_no}\\s+(.+?)(?=\\s+\\d{{3,}}|\\s+\\$|$)'
            desc_match = re.search(desc_pattern, line)
            description = ""
            
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                item_pos = line.find(f'#{item_no}')
                if item_pos != -1:
                    remaining = line[item_pos + len(item_no) + 1:].strip()
                    desc_end_pattern = r'(\s+\d{3,}|\s+\$\d+|\s+GP\d+)'
                    desc_end_match = re.search(desc_end_pattern, remaining)
                    if desc_end_match:
                        description = remaining[:desc_end_match.start()].strip()
                    else:
                        description = remaining
            
            # Clean description
            description = re.sub(r'\s*(MARKS?\s*&\s*NOS?:?|MARK\s*&\s*NO:?).*$', '', description, re.IGNORECASE)
            description = re.sub(r'\s*-\s*$', '', description)
            description = re.sub(r'\s+\d{1,3}\s*$', '', description)
            description = description.strip()
            
            seen_items.add(item_no)
            items.append({
                'item_no': item_no,
                'description': description,
                'qty': 1,  # Will be updated by looking at following lines
                'price': None
            })
    
    # Now look for quantity information in lines that follow the item declarations
    # The PDF has patterns like:
    # "#FB50F77B HYBRID SI 3-IN-1"
    # "COMBINATION BOOSTER CAR SEAT"  
    # "1-6840 640 4,160.00 5,120.00 64.69 GP21402"
    
    for i, item in enumerate(items):
        item_no = item['item_no']
        print(f"Debug: Looking for quantity for {item_no}")
        
        # Find the line with the item declaration
        item_line_idx = None
        for j, line in enumerate(lines):
            if f'#{item_no}' in line:
                item_line_idx = j
                break
        
        if item_line_idx is not None:
            # Look in the next few lines for quantity patterns
            # Pattern: "1-6840 640 4,160.00 5,120.00 64.69 GP21402"
            # The second number (640) is usually the quantity
            for k in range(item_line_idx + 1, min(item_line_idx + 5, len(lines))):
                if k < len(lines):
                    line = lines[k]
                    print(f"Debug: Checking line for {item_no} qty: '{line}'")
                    
                    # Look for pattern like "1-6840 640 4,160.00 5,120.00 64.69"
                    # where 640 is the quantity
                    qty_pattern = r'(\d+[-]\d+)\s+(\d+)\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s+\d+\.\d{2}'
                    qty_match = re.search(qty_pattern, line)
                    
                    if qty_match:
                        try:
                            qty = int(qty_match.group(2))
                            item['qty'] = qty
                            print(f"Debug: Found quantity {qty} for {item_no}")
                            break
                        except ValueError:
                            continue
                    
                    # Fallback: look for standalone numbers that could be quantities
                    numbers = re.findall(r'\b(\d{1,4})\b', line)
                    for num_str in numbers:
                        try:
                            num = int(num_str)
                            if 10 <= num <= 10000:  # Reasonable quantity range
                                item['qty'] = num
                                print(f"Debug: Found fallback quantity {num} for {item_no}")
                                break
                        except ValueError:
                            continue
                    
                    if item['qty'] > 1:  # Found a quantity, stop looking
                        break
    
    return items

def parse_pdf_invoice_section(lines: List[str]) -> dict:
    """Parse unit prices from invoice section"""
    prices = {}
    
    for line in lines:
        print(f"Debug: Processing invoice line: '{line}'")
        
        # Look for lines with item codes and prices in a specific table format
        # Expected format: "1-6840 FB50F77B DESCRIPTION... 640 58.05 37,152.00 64.69 GP21402"
        
        # First check if line contains an item code pattern
        item_matches = re.findall(r'([A-Z0-9]{8})', line)  # Look for 8-character item codes like FB50F77B
        
        if not item_matches:
            # Also try 6+ character codes
            item_matches = re.findall(r'([A-Z0-9]{6,})', line)
        
        for item_no in item_matches:
            # Skip obvious non-item patterns
            if item_no in ['COMBINATION', 'PROTECTION', 'SMCU1249', 'SMC815', 'GP21402', 'GP22018']:
                continue
                
            print(f"Debug: Found potential item {item_no} in invoice line")
            
            # Look for price pattern in this line: quantity, unit_price, total_price, cbm
            # Pattern like: "640 58.05 37,152.00 64.69" or "36 68.15 2,453.40 3.66"
            
            # Find all decimal numbers in the line
            decimal_numbers = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', line)
            # Also find integers that could be quantities
            integers = re.findall(r'\b(\d{1,4})\b', line)
            
            print(f"Debug: Found decimal numbers: {decimal_numbers}")
            print(f"Debug: Found integers: {integers}")
            
            # Try to identify unit price (usually the smaller decimal value, not comma-separated)
            potential_unit_prices = []
            for num_str in decimal_numbers:
                if ',' not in num_str:  # Unit prices shouldn't have commas
                    try:
                        price = float(num_str)
                        if 1.0 <= price <= 500:  # Reasonable unit price range
                            potential_unit_prices.append(price)
                    except ValueError:
                        continue
            
            # Also look for direct dollar patterns
            dollar_matches = re.findall(r'\$?(\d+\.\d{2})', line)
            for price_str in dollar_matches:
                try:
                    price = float(price_str)
                    if 1.0 <= price <= 500 and price not in potential_unit_prices:
                        potential_unit_prices.append(price)
                except ValueError:
                    continue
            
            if potential_unit_prices:
                # Choose the most reasonable unit price
                # Filter out known CBM values and very small prices
                filtered_prices = [p for p in potential_unit_prices if p not in [3.66, 64.69] and p > 10.0]
                
                if filtered_prices:
                    unit_price = min(filtered_prices)  # Usually the smallest reasonable price is the unit price
                else:
                    unit_price = min(potential_unit_prices)  # Fallback to any price
                
                # Validate by checking if it makes sense with quantity and total
                for qty_str in integers:
                    try:
                        qty = int(qty_str)
                        if 1 <= qty <= 10000:
                            # Check if unit_price * qty approximates any of the larger decimal numbers
                            expected_total = unit_price * qty
                            for total_str in decimal_numbers:
                                if ',' in total_str:  # Total prices usually have commas
                                    try:
                                        actual_total = float(total_str.replace(',', ''))
                                        if abs(expected_total - actual_total) < 1.0:  # Close match
                                            prices[item_no] = unit_price
                                            print(f"Debug: Confirmed price ${unit_price} for {item_no} (qty={qty}, total=${actual_total})")
                                            break
                                    except ValueError:
                                        continue
                            if item_no in prices:
                                break
                    except ValueError:
                        continue
                
                # If no validation worked, but we found a reasonable unit price, use it
                if item_no not in prices and filtered_prices:
                    prices[item_no] = filtered_prices[0]
                    print(f"Debug: Using filtered unit price ${filtered_prices[0]} for {item_no} (no validation)")
                elif item_no not in prices and potential_unit_prices:
                    # Only use unfiltered prices as last resort and if they're reasonable
                    reasonable_prices = [p for p in potential_unit_prices if p >= 20.0]
                    if reasonable_prices:
                        prices[item_no] = min(reasonable_prices)
                        print(f"Debug: Using reasonable unit price ${min(reasonable_prices)} for {item_no} (last resort)")
    
    return prices

def parse_excel_packing_list(filepath: str) -> List[PackingListRow]:
    """Parse Excel packing list file - supports multiple formats"""
    
    # Get just the filename for checking (remove path)
    filename = os.path.basename(filepath).lower()
    
    # Check if this is a price list file (Item price column G.xlsx format)
    # Look for specific indicators of price files
    is_price_file = (
        'item_price' in filename or 
        'item price' in filename or
        filename.startswith('item') and 'price' in filename
    )
    
    if is_price_file:
        return parse_item_price_file(filepath)
    else:
        # Check if file has multiple sheets (PL + Invoice format)
        try:
            xl_file = pd.ExcelFile(filepath)
            sheet_names = [name.upper() for name in xl_file.sheet_names]
            
            has_packing_list = any('PL' in name or 'PACKING' in name for name in sheet_names)
            has_invoice = any('INVOICE' in name or 'INV' in name for name in sheet_names)
            
            if has_packing_list and has_invoice:
                print(f"Debug: Found multi-sheet file with sheets: {xl_file.sheet_names}")
                return parse_multi_sheet_file(filepath)
            else:
                # Single sheet packing list
                return parse_packing_list_file(filepath)
        except Exception as e:
            print(f"Debug: Error checking sheets, falling back to single sheet: {e}")
            return parse_packing_list_file(filepath)

def parse_multi_sheet_file(filepath: str) -> List[PackingListRow]:
    """Parse Excel file with separate Packing List and Invoice sheets"""
    with pd.ExcelFile(filepath) as xl_file:
        # Find the sheet names
        packing_sheet = None
        invoice_sheet = None
        
        for sheet_name in xl_file.sheet_names:
            sheet_upper = sheet_name.upper()
            if 'PL' in sheet_upper or 'PACKING' in sheet_upper:
                packing_sheet = sheet_name
            elif 'INVOICE' in sheet_upper or 'INV' in sheet_upper:
                invoice_sheet = sheet_name
        
        print(f"Debug: Using packing sheet: {packing_sheet}, invoice sheet: {invoice_sheet}")
        
        # Parse items from packing list sheet
        items_from_packing = []
        if packing_sheet:
            # Use existing packing list parsing logic but read specific sheet
            df_packing = pd.read_excel(xl_file, sheet_name=packing_sheet, header=None)
            items_from_packing = parse_packing_list_sheet_data(df_packing)
            print(f"Debug: Found {len(items_from_packing)} items in packing list sheet")
        
        # Parse prices from invoice sheet  
        invoice_prices = {}
        if invoice_sheet:
            invoice_prices = parse_invoice_sheet_prices_from_xl(xl_file, invoice_sheet)
            print(f"Debug: Found {len(invoice_prices)} prices in invoice sheet")
        
        # Combine items with prices
        final_rows = []
        for item in items_from_packing:
            unit_price = invoice_prices.get(item.item_no)
            final_rows.append(PackingListRow(
                item_no=item.item_no,
                description=item.description,
                qty=item.qty,
                packing_list_price=unit_price,  # Price from invoice
                system_price=None  # Will be enriched later
            ))
        
        return final_rows

def parse_packing_list_sheet_data(df_packing: pd.DataFrame) -> List[PackingListRow]:
    """Parse data from packing list sheet (items and quantities only)"""
    # This is similar to existing parse_packing_list_file but focuses on items/qty
    
    # Find header row
    header_row_idx = None
    for i in range(min(30, len(df_packing))):
        row = df_packing.iloc[i]
        row_str = [str(cell).lower() for cell in row.values if isinstance(cell, str)]
        row_text = ' '.join(row_str)
        
        header_indicators = ['packing no', 'description', 'quantity', 'container', 'ctns', 'weight', 'measurement']
        matching_indicators = sum(1 for indicator in header_indicators if indicator in row_text)
        if matching_indicators >= 3:
            header_row_idx = i
            break
    
    if header_row_idx is not None:
        try:
            df = pd.read_excel(df_packing.index.name, sheet_name=0, header=header_row_idx) if hasattr(df_packing.index, 'name') else df_packing.iloc[header_row_idx+1:]
            df.columns = df_packing.iloc[header_row_idx].values
        except:
            df = df_packing
    else:
        df = df_packing
    
    # Extract items (without prices)
    items = []
    seen_items = set()
    
    for idx, row in df.iterrows():
        if pd.isna(row).all():
            continue
            
        # Look for item number
        item_no = None
        description = ""
        for val in row.values:
            if pd.notna(val) and isinstance(val, str) and '#' in val:
                item_match = re.search(r'#([A-Z0-9]+)', val)
                if item_match:
                    item_no = item_match.group(1)
                    desc_match = re.search(r'#[A-Z0-9]+\s+(.+)', val)
                    if desc_match:
                        full_desc = desc_match.group(1).strip()
                        description = re.sub(r'\s+\d+\s*$', '', full_desc)
                        description = re.sub(r'\s+GP\d+\s*$', '', description)
                        description = description.strip()
                    break
        
        if not item_no or item_no in seen_items:
            continue
            
        # Extract quantity
        qty = 1
        numeric_values = []
        for val in row.values:
            if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                if val < 10000 and val == int(val):
                    numeric_values.append(int(val))
        if numeric_values:
            reasonable_qtys = [q for q in numeric_values if 1 <= q <= 10000]
            if reasonable_qtys:
                qty = min(reasonable_qtys)
        
        seen_items.add(item_no)
        items.append(PackingListRow(
            item_no=item_no,
            description=description,
            qty=qty,
            packing_list_price=None,  # No price from packing list
            system_price=None
        ))
    
    return items

def parse_invoice_sheet_prices(filepath: str, invoice_sheet: str) -> dict:
    """Parse unit prices from invoice sheet"""
    with pd.ExcelFile(filepath) as xl_file:
        return parse_invoice_sheet_prices_from_xl(xl_file, invoice_sheet)

def parse_invoice_sheet_prices_from_xl(xl_file: pd.ExcelFile, invoice_sheet: str) -> dict:
    """Parse unit prices from invoice sheet using an existing ExcelFile object"""
    df_invoice = pd.read_excel(xl_file, sheet_name=invoice_sheet, header=None)
    
    print(f"Debug: Invoice sheet shape: {df_invoice.shape}")
    
    # Find invoice table header row
    header_row_idx = None
    for i in range(min(30, len(df_invoice))):
        row = df_invoice.iloc[i]
        row_str = [str(cell).lower() for cell in row.values if isinstance(cell, str)]
        row_text = ' '.join(row_str)
        
        # Look for invoice table headers
        if any(x in row_text for x in ['unit price', 'amount', 'quantity', 'item']) and 'usd' in row_text:
            header_row_idx = i
            print(f"Debug: Found invoice header at row {i}: {row_text}")
            break
    
    if header_row_idx is None:
        print("Debug: No invoice table header found")
        return {}
    
    # Read with proper headers
    try:
        df = pd.read_excel(xl_file, sheet_name=invoice_sheet, header=header_row_idx)
        print(f"Debug: Invoice columns: {list(df.columns)}")
    except:
        df = df_invoice.iloc[header_row_idx+1:]
        df.columns = df_invoice.iloc[header_row_idx].values
    
    # Find relevant columns
    item_col = None
    price_col = None
    
    for col in df.columns:
        if isinstance(col, str):
            col_lower = col.lower()
            if 'item' in col_lower:
                item_col = col
            elif 'unit price' in col_lower and 'usd' in col_lower:
                price_col = col
    
    print(f"Debug: Using item column: {item_col}, price column: {price_col}")
    
    # Extract prices
    prices = {}
    for idx, row in df.iterrows():
        if pd.isna(row).all():
            continue
        
        # Extract item number
        item_no = None
        if item_col and item_col in row.index:
            item_val = row.get(item_col)
            if pd.notna(item_val) and isinstance(item_val, str):
                item_no = item_val.strip()
        
        # If no item column, look for item in any column
        if not item_no:
            for val in row.values:
                if pd.notna(val) and isinstance(val, str):
                    item_match = re.search(r'([A-Z0-9]{6,})', val)  # Look for item codes
                    if item_match:
                        item_no = item_match.group(1)
                        break
        
        if not item_no:
            continue
        
        # Extract price
        unit_price = None
        if price_col and price_col in row.index:
            price_val = row.get(price_col)
            if pd.notna(price_val) and isinstance(price_val, (int, float)):
                unit_price = float(price_val)
        
        if unit_price:
            prices[item_no] = unit_price
            print(f"Debug: Found price for {item_no}: ${unit_price}")
    
    return prices

def parse_item_price_file(filepath: str) -> List[PackingListRow]:
    """Parse item price Excel file (Item price column G.xlsx format)"""
    df = pd.read_excel(filepath)
    
    rows = []
    for _, row in df.iterrows():
        # Extract item number from the Item Number column
        item_no = str(row.get("Item Number", "")).strip()
        if not item_no or pd.isna(item_no):
            continue
            
        # Use Display Name as description
        description = str(row.get("Display Name", "")).strip()
        if not description or pd.isna(description):
            description = str(row.get("Purchase Description", "")).strip()
        
        # For price file, we don't have quantity, so default to 1
        qty = 1
        
        # Get unit price from Vendor Purchase Price
        packing_list_price = None
        price_str = str(row.get("Vendor Purchase Price", ""))
        try:
            packing_list_price = float(price_str)
        except (ValueError, TypeError):
            packing_list_price = None
        
        if item_no and description:
            rows.append(PackingListRow(
                item_no=item_no,
                description=description,
                qty=qty,
                packing_list_price=packing_list_price,
                system_price=None  # Will be enriched later
            ))
    
    return rows

def parse_packing_list_file(filepath: str) -> List[PackingListRow]:
    """Parse packing list Excel file (Packing List.xlsx format) with auto header detection"""
    import pandas as pd
    import re

    # 1. Read entire file first to understand structure
    full_df = pd.read_excel(filepath, header=None)
    
    # 2. Look for header row with more specific patterns
    header_row_idx = None
    for i in range(min(30, len(full_df))):  # Check first 30 rows
        row = full_df.iloc[i]
        row_str = [str(cell).lower() for cell in row.values if isinstance(cell, str)]
        row_text = ' '.join(row_str)
        
        # Look for packing list table headers
        header_indicators = [
            'packing no', 'description', 'quantity', 'container', 
            'ctns', 'weight', 'measurement', 'unit price', 'total price'
        ]
        
        matching_indicators = sum(1 for indicator in header_indicators if indicator in row_text)
        if matching_indicators >= 3:  # Need at least 3 matching indicators
            header_row_idx = i
            print(f"Debug: Found header row at index {i}")
            print(f"Debug: Header row content: {row_text}")
            break
    
    if header_row_idx is not None:
        # Convert pandas index to int safely
        try:
            header_row_num = int(header_row_idx) if isinstance(header_row_idx, (int, float)) else None
            if header_row_num is not None:
                df = pd.read_excel(filepath, header=header_row_num)
            else:
                df = pd.read_excel(filepath)  # fallback if conversion fails
        except (ValueError, TypeError):
            df = pd.read_excel(filepath)  # fallback if conversion fails
    else:
        df = pd.read_excel(filepath)  # fallback

    print(f"Debug: DataFrame shape: {df.shape}")
    print(f"Debug: Column names: {list(df.columns)}")

    # Normalize column names for better matching
    original_columns = df.columns.tolist()
    normalized_columns = {}
    for col in original_columns:
        if isinstance(col, str):
            normalized = col.strip().lower().replace(' ', '').replace('_', '').replace('(', '').replace(')', '')
            normalized_columns[normalized] = col
    
    # Find relevant columns with more flexible matching
    unit_price_col = None
    total_price_col = None
    quantity_col = None
    net_weight_col = None
    gross_weight_col = None
    measurement_col = None
    
    for normalized, original in normalized_columns.items():
        if any(x in normalized for x in ['unitprice', 'unit', 'price']) and 'total' not in normalized:
            unit_price_col = original
        elif any(x in normalized for x in ['totalprice', 'total']) and 'price' in normalized:
            total_price_col = original
        elif any(x in normalized for x in ['quantity', 'qtys', 'ctns']):
            quantity_col = original
        elif 'netweight' in normalized or ('net' in normalized and 'weight' in normalized):
            net_weight_col = original
        elif 'grossweight' in normalized or ('gross' in normalized and 'weight' in normalized):
            gross_weight_col = original
        elif 'measurement' in normalized or 'cbm' in normalized:
            measurement_col = original

    print(f"Debug: Found columns - Unit Price: {unit_price_col}, Total Price: {total_price_col}")
    print(f"Debug: Other columns - Quantity: {quantity_col}, Net Weight: {net_weight_col}, Gross Weight: {gross_weight_col}, Measurement: {measurement_col}")

    rows = []
    seen_items = set()
    for idx, row in df.iterrows():
        # Skip empty rows
        if row.isna().all():
            continue
        
        # Look for item number in any column
        item_no = None
        description = ""
        for val in row.values:
            if pd.notna(val) and isinstance(val, str) and '#' in val:
                item_match = re.search(r'#([A-Z0-9]+)', val)
                if item_match:
                    item_no = item_match.group(1)
                    # Extract description after the item number
                    desc_match = re.search(r'#[A-Z0-9]+\s+(.+)', val)
                    if desc_match:
                        full_desc = desc_match.group(1).strip()
                        # Clean up description (remove trailing numbers that might be quantities)
                        description = re.sub(r'\s+\d+\s*$', '', full_desc)
                        description = re.sub(r'\s+GP\d+\s*$', '', description)
                        description = description.strip()
                    break
        
        if not item_no:
            continue
        
        print(f"Debug: Processing item {item_no}: {description}")
        
        # Extract quantity - try the quantity column first, then fallback to numeric values
        qty = 1
        if quantity_col and quantity_col in row.index:
            qty_val = row.get(quantity_col)
            if qty_val is not None and pd.notna(qty_val) and isinstance(qty_val, (int, float)):
                qty = int(qty_val)
                print(f"Debug: Found quantity {qty} in quantity column for {item_no}")
        
        # Fallback: look for reasonable quantity values
        if qty == 1:
            numeric_values = []
            for val in row.values:
                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                    if val < 10000 and val == int(val):
                        numeric_values.append(int(val))
            if numeric_values:
                reasonable_qtys = [q for q in numeric_values if 1 <= q <= 10000]
                if reasonable_qtys:
                    qty = min(reasonable_qtys)
                    print(f"Debug: Found fallback quantity {qty} for {item_no}")
        
        # Extract unit price - try multiple strategies
        packing_list_price = None
        
        # Strategy 1: Look in unit price column
        if unit_price_col and unit_price_col in row.index:
            cell_value = row.get(unit_price_col)
            if cell_value is not None and not pd.isna(cell_value):
                try:
                    packing_list_price = float(cell_value)
                    print(f"Debug: Found unit price {packing_list_price} in unit price column for {item_no}")
                except (ValueError, TypeError):
                    print(f"Debug: Could not parse unit price '{cell_value}' for {item_no}")
        
        # Strategy 2: Calculate from total price / quantity
        if packing_list_price is None and total_price_col and total_price_col in row.index:
            total_val = row.get(total_price_col)
            if total_val is not None and pd.notna(total_val) and isinstance(total_val, (int, float)) and qty > 0:
                try:
                    calculated_unit_price = float(total_val) / qty
                    if calculated_unit_price > 0 and calculated_unit_price < 1000:  # Reasonable unit price range
                        packing_list_price = calculated_unit_price
                        print(f"Debug: Calculated unit price {packing_list_price} from total price for {item_no}")
                except (ValueError, TypeError):
                    pass
        
        # Strategy 3: Look for decimal values that could be unit prices (but exclude measurements)
        if packing_list_price is None:
            decimal_candidates = []
            for col_name, val in zip(df.columns, row.values):
                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                    # Skip values that are clearly measurements or weights
                    col_name_lower = str(col_name).lower()
                    is_measurement = any(x in col_name_lower for x in ['cbm', 'measurement', 'weight', 'kg', 'volume'])
                    
                    if not is_measurement and 0.1 <= val <= 500 and val != int(val):  # Reasonable unit price range
                        decimal_candidates.append(float(val))
                        print(f"Debug: Found potential unit price {val} in column '{col_name}' for {item_no}")
            
            if decimal_candidates:
                # Prefer middle-range values as they're more likely to be unit prices
                decimal_candidates.sort()
                # Avoid very small values that might be measurements
                reasonable_prices = [p for p in decimal_candidates if p >= 1.0]
                if reasonable_prices:
                    packing_list_price = reasonable_prices[0]
                    print(f"Debug: Selected unit price {packing_list_price} from candidates {reasonable_prices} for {item_no}")
        
        # Strategy 4: Final fallback - but be more strict about what constitutes a price
        if packing_list_price is None:
            # Only consider values that are in reasonable price ranges and not in measurement columns
            price_candidates = []
            for col_name, val in zip(df.columns, row.values):
                if pd.notna(val) and isinstance(val, (int, float)):
                    col_name_lower = str(col_name).lower()
                    # Exclude measurement/weight/quantity columns completely
                    excluded_columns = ['cbm', 'measurement', 'weight', 'kg', 'volume', 'container', 'packing', 'quantity', 'ctns', 'qty']
                    if any(x in col_name_lower for x in excluded_columns):
                        continue
                    # Only consider values in typical unit price range and avoid integers that might be quantities
                    if 1.0 <= val <= 200 and val != int(val):  # Must be decimal to be a price
                        price_candidates.append(val)
            
            if price_candidates:
                price_candidates.sort()
                packing_list_price = price_candidates[0]
                print(f"Debug: Final fallback unit price {packing_list_price} for {item_no}")
            else:
                print(f"Debug: No unit price found in packing list for {item_no} - this appears to be a packing list without prices")
        
        # Extract total price for reference (not used in main logic)
        total_price = None
        if total_price_col and total_price_col in row.index:
            cell_value = row.get(total_price_col)
            if cell_value is not None and not pd.isna(cell_value):
                try:
                    total_price = float(cell_value)
                    print(f"Debug: Found total price {total_price} for {item_no}")
                except (ValueError, TypeError):
                    total_price = None
        
        # Validation: Check if total price matches unit price * quantity
        if packing_list_price and total_price and qty:
            calculated_total = packing_list_price * qty
            if abs(calculated_total - total_price) > 0.01:
                print(f"Warning: Total price mismatch for {item_no}: {total_price} vs calculated {calculated_total}")
        
        item_key = f"{item_no}"
        if item_no and description and item_key not in seen_items:
            seen_items.add(item_key)
            rows.append(PackingListRow(
                item_no=item_no,
                description=description,
                qty=qty,
                packing_list_price=packing_list_price,
                system_price=None
            ))
    
    print(f"Debug: Parsed {len(rows)} items from packing list")
    return rows
