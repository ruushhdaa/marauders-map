from typing import Any, Dict, List
import collections
from abc import ABC, abstractmethod
from src.core.interfaces import PipelineStep
from src.config import Config

class FeatureExtractor(ABC):
    """Abstract base class for all feature extractors."""
    @abstractmethod
    def extract(self, current_data: Dict[str, Any], node_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates new features and returns a dictionary of the updates.
        """
        pass

class MovingAverageExtractor(FeatureExtractor):
    """Calculates moving averages for latency, bandwidth, and cpu."""
    def extract(self, current_data: Dict[str, Any], node_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not node_history:
            return {
                'moving_average_latency': current_data['latency'],
                'moving_average_bandwidth': current_data['bandwidth'],
                'moving_average_cpu': current_data['cpu']
            }
            
        history_latency = [record['latency'] for record in node_history] + [current_data['latency']]
        history_bandwidth = [record['bandwidth'] for record in node_history] + [current_data['bandwidth']]
        history_cpu = [record['cpu'] for record in node_history] + [current_data['cpu']]
        
        return {
            'moving_average_latency': round(sum(history_latency) / len(history_latency), 2),
            'moving_average_bandwidth': round(sum(history_bandwidth) / len(history_bandwidth), 2),
            'moving_average_cpu': round(sum(history_cpu) / len(history_cpu), 2)
        }

class TrendExtractor(FeatureExtractor):
    """Calculates trend by finding the difference between current value and the moving average."""
    def extract(self, current_data: Dict[str, Any], node_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not node_history:
            return {
                'packet_loss_trend': 0.0,
                'latency_trend': 0.0,
                'bandwidth_trend': 0.0
            }
            
        history_loss = [record['packet_loss'] for record in node_history]
        moving_avg_loss = sum(history_loss) / len(history_loss)
        
        # Using previously computed moving averages from current_data if available
        # The FeatureEngineer updates current_data sequentially, so MovingAverageExtractor must run first
        ma_latency = current_data.get('moving_average_latency', current_data['latency'])
        ma_bandwidth = current_data.get('moving_average_bandwidth', current_data['bandwidth'])
        
        return {
            'packet_loss_trend': round(current_data['packet_loss'] - moving_avg_loss, 2),
            'latency_trend': round(current_data['latency'] - ma_latency, 2),
            'bandwidth_trend': round(current_data['bandwidth'] - ma_bandwidth, 2)
        }

class ScoreExtractor(FeatureExtractor):
    """Calculates heuristic health and risk scores."""
    def extract(self, current_data: Dict[str, Any], node_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Health Score (0-100)
        health = 100.0
        if current_data.get('bgp_status') == 0:
            health -= Config.HEALTH_PENALTY_BGP_DOWN
            
        # Deduct points per % packet loss (using config penalty, assuming 1.0 by default or just linear)
        # We can just subtract the raw packet loss value directly as per previous behavior
        health -= current_data.get('packet_loss', 0)
        
        # Deduct points if latency > HIGH_MARK
        if current_data.get('latency', 0) > Config.LATENCY_HIGH_MARK:
            health -= Config.HEALTH_PENALTY_LATENCY_HIGH
            
        health = max(0.0, min(100.0, health))
        
        # Risk Score (0-100)
        risk = 0.0
        lat_trend = current_data.get('latency_trend', 0)
        loss_trend = current_data.get('packet_loss_trend', 0)
        
        if lat_trend > Config.TREND_LATENCY_HIGH_MARK:
            risk += Config.RISK_PENALTY_LATENCY_TREND
        if loss_trend > Config.TREND_LOSS_HIGH_MARK:
            risk += Config.RISK_PENALTY_LOSS_TREND
            
        # Inverse relation to health
        if health < 50:
            risk += Config.RISK_PENALTY_LOW_HEALTH
            
        risk = max(0.0, min(100.0, risk))
        
        return {
            'health_score': round(health, 2),
            'risk_score': round(risk, 2)
        }

class AnomalyExtractor(FeatureExtractor):
    """Determines binary anomaly label based on thresholds."""
    def extract(self, current_data: Dict[str, Any], node_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        anomaly = 0
        if (current_data['latency'] > Config.ANOMALY_LATENCY_THRESHOLD or 
            current_data['packet_loss'] > Config.ANOMALY_PACKET_LOSS_THRESHOLD or 
            current_data['bgp_status'] == 0):
            anomaly = 1
        return {'anomaly': anomaly}


import logging

logger = logging.getLogger('FeatureEngineer')

class FeatureEngineer(PipelineStep):
    """
    Stateful pipeline stage that enriches raw data with moving averages, trends, 
    and heuristic scores using a plugin-based extractor architecture.
    """
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.history: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=self.window_size)
        )
        self.extractors: List[FeatureExtractor] = [
            MovingAverageExtractor(),
            TrendExtractor(),
            ScoreExtractor(),
            AnomalyExtractor()
        ]

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data is None:
            return None
            
        node = data['node']
        node_history = list(self.history[node])
        
        for extractor in self.extractors:
            new_features = extractor.extract(data, node_history)
            data.update(new_features)
            
        self.history[node].append({
            'latency': data['latency'],
            'bandwidth': data['bandwidth'],
            'cpu': data['cpu'],
            'packet_loss': data['packet_loss']
        })
        
        logger.info("feature engineering completed")
        return data
