import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

class RiskScorer:
    """Compute hotspot and trend analytics from incident point data."""

    def __init__(self):
        """Initialize reusable preprocessing utilities."""
        self.scaler = StandardScaler()
    
    def normalize_scores(self, scores):
        """Normalize score arrays to [0, 1]."""
        if scores is None or len(scores) == 0:
            return None
        return (scores - scores.min()) / (scores.max() - scores.min())
    
    def detect_hotspots(self, data, eps=None, min_samples=None):
        """Detect spatial incident clusters with DBSCAN and summarize density."""
        try:
            coords = data[['latitude', 'longitude']].copy()
            lat_scale = 111000
            lon_scale = 85000
            coords['x'] = coords['longitude'] * lon_scale
            coords['y'] = coords['latitude'] * lat_scale
            
            scaled_coords = self.scaler.fit_transform(coords[['x', 'y']])
            
            if eps is None:
                eps = 500 * np.sqrt(10000 / len(data))
                eps = max(200, min(1000, eps))
            
            if min_samples is None:
                min_samples = max(5, int(np.log10(len(data)) * 3))
            
            eps_scaled = eps / np.sqrt(lat_scale * lon_scale)
            dbscan = DBSCAN(eps=eps_scaled, min_samples=min_samples)
            clusters = dbscan.fit_predict(scaled_coords)
            
            n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
            if n_clusters == 0:
                return None
            
            data_with_clusters = data.copy()
            data_with_clusters['cluster'] = clusters
            
            cluster_stats = []
            for cluster_id in range(n_clusters):
                cluster_points = data_with_clusters[data_with_clusters['cluster'] == cluster_id]
                center_lat = cluster_points['latitude'].mean()
                center_lon = cluster_points['longitude'].mean()
                
                min_lat, max_lat = cluster_points['latitude'].min(), cluster_points['latitude'].max()
                min_lon, max_lon = cluster_points['longitude'].min(), cluster_points['longitude'].max()
                
                area_km2 = max(0.01, (max_lat - min_lat) * 111 * (max_lon - min_lon) * 85)
                count = len(cluster_points)
                density = min(10000, count / area_km2) if area_km2 > 0 else 0
                
                cluster_stats.append({
                    'cluster_id': cluster_id,
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'count': count,
                    'area_km2': area_km2,
                    'density': density
                })
            
            result = pd.DataFrame(cluster_stats)
            result['density'] = pd.to_numeric(result['density'], errors='coerce').fillna(0)
            result['area_km2'] = pd.to_numeric(result['area_km2'], errors='coerce').fillna(0.01)
            
            result = result[
                (result['density'] > 0) & 
                (result['density'] < float('inf')) & 
                (result['area_km2'] > 0)
            ]
            
            return result
            
        except Exception:
            return None
    
    def calculate_temporal_trend(self, data, date_column, window_days=7):
        """Compute rolling average trend for daily incident counts."""
        if data is None or len(data) == 0:
            return None
            
        daily_counts = data.groupby(data[date_column].dt.date).size()
        trend = daily_counts.rolling(window=window_days, min_periods=1).mean()
        return trend
    
    def identify_emerging_risks(self, data, date_column, threshold_percentile=90):
        """Identify recent locations above a configurable incident percentile."""
        if data is None or len(data) == 0:
            return None
            
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_data = data[data[date_column] >= recent_cutoff]
        
        location_counts = recent_data.groupby(['latitude', 'longitude']).size()
        threshold = np.percentile(location_counts, threshold_percentile)
        high_risk_locations = location_counts[location_counts >= threshold]
        
        return pd.DataFrame(high_risk_locations)
    
    def optimize_resource_allocation(self, hotspots, n_resources=10):
        """Allocate a fixed resource count proportionally across hotspots."""
        if hotspots is None or len(hotspots) == 0:
            return None
            
        total_incidents = hotspots['count'].sum()
        allocations = (hotspots['count'] / total_incidents * n_resources).round()
        
        hotspots_with_allocation = hotspots.copy()
        hotspots_with_allocation['resources_allocated'] = allocations
        
        return hotspots_with_allocation 