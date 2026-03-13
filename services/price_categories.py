import numpy as np
from typing import List, Dict

class PriceCategorizer:
    @staticmethod
    def get_thresholds(price_changes: List[float]) -> Dict[str, float]:
        if len(price_changes) < 4:
            return {}
        changes = np.array(price_changes)
        q1 = np.percentile(changes, 25)
        q2 = np.percentile(changes, 50)
        q3 = np.percentile(changes, 75)
        return {
            'extreme_bearish': float(np.min(changes[changes <= q1])) if any(changes <= q1) else float(np.min(changes)),
            'bearish': float(q1),
            'bullish': float(q3),
            'extreme_bullish': float(np.max(changes[changes >= q3])) if any(changes >= q3) else float(np.max(changes))
        }

    @staticmethod
    def get_category(price_change: float, thresholds: Dict[str, float]) -> str:
        if not thresholds:
            return 'bullish' if price_change > 0 else 'bearish'
        if price_change <= thresholds['extreme_bearish']:
            return 'extreme_bearish'
        if price_change <= thresholds['bearish']:
            return 'bearish'
        if price_change <= thresholds['bullish']:
            return 'bullish'
        return 'extreme_bullish'
