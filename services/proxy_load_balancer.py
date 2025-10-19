"""
Load balancing strategies for proxy selection.

This module provides various algorithms for selecting proxies from the pool.
"""
import random
import logging
import sys
import os
from typing import List, Optional, Callable
from enum import Enum
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.models import ProxyPool

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_RECENTLY_USED = "lru"
    WEIGHTED_RANDOM = "weighted_random"
    BEST_REPUTATION = "best_reputation"
    FASTEST_RESPONSE = "fastest_response"
    RANDOM = "random"


class ProxyLoadBalancer:
    """Manages proxy selection using various load balancing strategies."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED_RANDOM):
        self.strategy = strategy
        self._round_robin_index = 0
        
    def select_proxy(self, available_proxies: List[ProxyPool], country_code: Optional[str] = None) -> Optional[ProxyPool]:
        """
        Select a proxy from the available list using the configured strategy.
        
        Args:
            available_proxies: List of available proxy records
            country_code: Optional country filter
            
        Returns:
            Selected proxy or None if no proxies available
        """
        if not available_proxies:
            return None
        
        # Filter by country if specified
        if country_code:
            filtered = [p for p in available_proxies if p.country_code == country_code]
            if filtered:
                available_proxies = filtered
            else:
                logger.warning(f"No proxies found for country {country_code}, using all available")
        
        # Apply strategy
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(available_proxies)
        elif self.strategy == LoadBalancingStrategy.LEAST_RECENTLY_USED:
            return self._least_recently_used(available_proxies)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
            return self._weighted_random(available_proxies)
        elif self.strategy == LoadBalancingStrategy.BEST_REPUTATION:
            return self._best_reputation(available_proxies)
        elif self.strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
            return self._fastest_response(available_proxies)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random(available_proxies)
        else:
            logger.warning(f"Unknown strategy {self.strategy}, falling back to random")
            return self._random(available_proxies)
    
    def _round_robin(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Round-robin selection."""
        proxy = proxies[self._round_robin_index % len(proxies)]
        self._round_robin_index += 1
        logger.debug(f"Round-robin selected: {proxy.ip_address}:{proxy.port}")
        return proxy
    
    def _least_recently_used(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Select least recently used proxy (LRU)."""
        # Sort by last_used_at (None first, then oldest)
        sorted_proxies = sorted(
            proxies,
            key=lambda p: p.last_used_at.replace(tzinfo=None) if p.last_used_at else datetime.min
        )
        proxy = sorted_proxies[0]
        logger.debug(f"LRU selected: {proxy.ip_address}:{proxy.port} (last used: {proxy.last_used_at})")
        return proxy
    
    def _weighted_random(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Weighted random selection based on reputation score."""
        # Calculate weights based on reputation (higher reputation = higher weight)
        weights = [max(p.reputation_score or 50, 1) for p in proxies]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return random.choice(proxies)
        
        # Weighted random selection
        rand_val = random.uniform(0, total_weight)
        cumsum = 0
        
        for proxy, weight in zip(proxies, weights):
            cumsum += weight
            if rand_val <= cumsum:
                logger.debug(f"Weighted random selected: {proxy.ip_address}:{proxy.port} (rep: {proxy.reputation_score})")
                return proxy
        
        # Fallback (shouldn't reach here)
        return proxies[-1]
    
    def _best_reputation(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Select proxy with best reputation score."""
        best_proxy = max(proxies, key=lambda p: p.reputation_score or 0)
        logger.debug(f"Best reputation selected: {best_proxy.ip_address}:{best_proxy.port} (rep: {best_proxy.reputation_score})")
        return best_proxy
    
    def _fastest_response(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Select proxy with fastest average response time."""
        # Filter proxies with response time data
        proxies_with_time = [p for p in proxies if p.response_time_avg is not None]
        
        if not proxies_with_time:
            # Fallback to random if no response time data
            return random.choice(proxies)
        
        fastest = min(proxies_with_time, key=lambda p: p.response_time_avg)
        logger.debug(f"Fastest response selected: {fastest.ip_address}:{fastest.port} ({fastest.response_time_avg:.1f}ms)")
        return fastest
    
    def _random(self, proxies: List[ProxyPool]) -> ProxyPool:
        """Completely random selection."""
        proxy = random.choice(proxies)
        logger.debug(f"Random selected: {proxy.ip_address}:{proxy.port}")
        return proxy
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Change the load balancing strategy."""
        old_strategy = self.strategy
        self.strategy = strategy
        logger.info(f"Load balancing strategy changed: {old_strategy.value} → {strategy.value}")
    
    def get_strategy_info(self) -> dict:
        """Get information about the current strategy."""
        return {
            'current_strategy': self.strategy.value,
            'available_strategies': [s.value for s in LoadBalancingStrategy],
            'strategy_descriptions': {
                'round_robin': 'Cycles through proxies in order',
                'lru': 'Uses least recently used proxy first',
                'weighted_random': 'Random selection weighted by reputation score',
                'best_reputation': 'Always selects proxy with highest reputation',
                'fastest_response': 'Selects proxy with fastest average response time',
                'random': 'Completely random selection'
            }
        }


# Global instance
proxy_load_balancer = ProxyLoadBalancer(strategy=LoadBalancingStrategy.WEIGHTED_RANDOM)


if __name__ == "__main__":
    # Test load balancing strategies
    from datetime import datetime, timezone
    
    print("🧪 Testing Load Balancing Strategies")
    print("=" * 60)
    
    # Create mock proxies
    class MockProxy:
        def __init__(self, id, ip, port, reputation, response_time, last_used_at):
            self.id = id
            self.ip_address = ip
            self.port = port
            self.reputation_score = reputation
            self.response_time_avg = response_time
            self.last_used_at = last_used_at
            self.country_code = "US"
    
    now = datetime.now(timezone.utc)
    
    proxies = [
        MockProxy(1, "1.1.1.1", 8080, 90, 200.0, now),
        MockProxy(2, "2.2.2.2", 8080, 75, 350.0, None),
        MockProxy(3, "3.3.3.3", 8080, 60, 500.0, now - timedelta(hours=2)),
        MockProxy(4, "4.4.4.4", 8080, 45, 800.0, now - timedelta(hours=5)),
        MockProxy(5, "5.5.5.5", 8080, 30, 1200.0, now - timedelta(days=1)),
    ]
    
    # Test each strategy
    for strategy in LoadBalancingStrategy:
        print(f"\n📊 Testing {strategy.value}:")
        balancer = ProxyLoadBalancer(strategy)
        
        selections = []
        for i in range(10):
            proxy = balancer.select_proxy(proxies)
            selections.append(proxy.ip_address)
        
        # Count selections
        from collections import Counter
        counts = Counter(selections)
        
        for ip, count in counts.most_common():
            bar = "█" * count
            print(f"  {ip}: {bar} ({count}/10)")
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
