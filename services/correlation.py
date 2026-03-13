import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import grangercausalitytests
from typing import List, Dict

class CorrelationAnalyzer:
    @staticmethod
    def pearson(x: List[float], y: List[float]) -> Dict[str, float]:
        if len(x) < 2 or len(y) < 2:
            return {'corr': 0, 'p_value': 1.0}
        mask = ~(np.isnan(x) | np.isnan(y))
        x = np.array(x)[mask]
        y = np.array(y)[mask]
        if len(x) < 2:
            return {'corr': 0, 'p_value': 1.0}
        corr, p = stats.pearsonr(x, y)
        return {'corr': corr, 'p_value': p}

    @staticmethod
    def cross_correlation(sentiment: List[float], price: List[float], max_lag: int = 10) -> Dict[int, float]:
        if len(sentiment) < max_lag + 1 or len(price) < max_lag + 1:
            return {}
        s = np.array(sentiment)
        p = np.array(price)
        result = {}
        for lag in range(1, max_lag + 1):
            if len(s[:-lag]) == len(p[lag:]):
                corr = np.corrcoef(s[:-lag], p[lag:])[0, 1]
                result[lag] = corr if not np.isnan(corr) else 0
        return result

    @staticmethod
    def granger_causality(sentiment: List[float], price: List[float], max_lag: int = 5) -> Dict[int, float]:
        data = np.column_stack([price, sentiment])
        try:
            gc = grangercausalitytests(data, maxlag=max_lag, verbose=False)
            return {lag: round(gc[lag][0]['ssr_ftest'][1], 4) for lag in range(1, max_lag + 1)}
        except:
            return {}
