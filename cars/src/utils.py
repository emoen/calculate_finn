import re


def extract_year(text):
    """Extract 4-digit year starting with 20 or 19 from text."""
    if not text:
        return None
    match = re.search(r'\b(20[0-2][0-9]|19[5-9][0-9])\b', str(text))
    if match:
        return int(match.group(1))
    return None


def extract_mileage(text):
    """Extract mileage in km from text."""
    if not text:
        return None
    # Matches patterns like "50 000 km", "50.000km", "50000 km"
    match = re.search(r'(\d+[\s\.]?\d*)\s*(?:km|kilometer)', str(text).lower())
    if match:
        try:
            # Clean string like "50 000" -> "50000"
            clean_num = match.group(1).replace(' ', '').replace('.', '')
            val = int(clean_num)
            # Sanity check: Car with > 1M km is unlikely or error
            if 0 < val < 1000000:
                return val
        except (ValueError, TypeError):
            pass
    return None


def normalize_brand(brand):
    """Normalize brand name for consistent lookup."""
    b = str(brand).strip().lower()
    if b == 'vw':
        b = 'volkswagen'
    return b
