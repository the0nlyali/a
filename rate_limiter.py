"""
Rate limiter module for controlling request rates to Instagram.
This helps avoid hitting Instagram's rate limits and prevents bans.
"""

import time
import random
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for rate limiting
DEFAULT_MAX_REQUESTS_PER_DAY = 200
DEFAULT_MAX_REQUESTS_PER_HOUR = 50
DEFAULT_MIN_DELAY = 2.0  # Minimum delay between requests in seconds
DEFAULT_MAX_DELAY = 5.0  # Maximum delay between requests
DEFAULT_BURST_SIZE = 5   # Number of requests allowed in a burst
DEFAULT_BURST_DELAY = 60 # Seconds to wait after a burst


class RateLimiter:
    """
    Rate limiter for Instagram API requests to prevent hitting limits and bans.
    Uses token bucket algorithm with variable delays and jitter.
    """
    
    def __init__(self, 
                 max_requests_per_day: int = DEFAULT_MAX_REQUESTS_PER_DAY,
                 max_requests_per_hour: int = DEFAULT_MAX_REQUESTS_PER_HOUR,
                 min_delay: float = DEFAULT_MIN_DELAY,
                 max_delay: float = DEFAULT_MAX_DELAY):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests_per_day: Maximum requests allowed per day
            max_requests_per_hour: Maximum requests allowed per hour
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.max_requests_per_day = max_requests_per_day
        self.max_requests_per_hour = max_requests_per_hour
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        # Request tracking
        self.daily_requests = 0
        self.hourly_requests = 0
        self.last_request_time = datetime.now()
        self.day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Token bucket for rate limiting
        self.tokens = DEFAULT_BURST_SIZE
        self.last_token_refill = datetime.now()
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Status
        self.active = True
        
        logger.info(f"Rate limiter initialized: {max_requests_per_day}/day, {max_requests_per_hour}/hour")
    
    def _update_request_counters(self) -> None:
        """Update the daily and hourly request counters."""
        now = datetime.now()
        
        # Check if we've moved to a new day
        if now.date() > self.day_start.date():
            logger.info(f"New day started, resetting daily request counter from {self.daily_requests}")
            self.daily_requests = 0
            self.day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if we've moved to a new hour
        if now.replace(minute=0, second=0, microsecond=0) > self.hour_start:
            logger.info(f"New hour started, resetting hourly request counter from {self.hourly_requests}")
            self.hourly_requests = 0
            self.hour_start = now.replace(minute=0, second=0, microsecond=0)
    
    def _refill_tokens(self) -> None:
        """Refill the token bucket based on time elapsed."""
        now = datetime.now()
        elapsed = (now - self.last_token_refill).total_seconds()
        
        # Refill at rate of 1 token per refill_rate seconds
        refill_rate = 5.0  # 1 token per 5 seconds
        new_tokens = int(elapsed / refill_rate)
        
        if new_tokens > 0:
            self.tokens = min(DEFAULT_BURST_SIZE, self.tokens + new_tokens)
            self.last_token_refill = now
    
    def _calculate_delay(self) -> float:
        """Calculate delay for the next request with jitter."""
        # Base delay with jitter
        base_delay = random.uniform(self.min_delay, self.max_delay)
        
        # Add additional delay if approaching hourly limit
        hour_limit_factor = self.hourly_requests / self.max_requests_per_hour
        if hour_limit_factor > 0.7:  # At 70% of hourly limit, start adding delay
            hour_delay = base_delay * (hour_limit_factor * 1.5)
            base_delay += hour_delay
            
        # Add additional delay if approaching daily limit
        day_limit_factor = self.daily_requests / self.max_requests_per_day
        if day_limit_factor > 0.8:  # At 80% of daily limit, start adding delay
            day_delay = base_delay * (day_limit_factor * 2)
            base_delay += day_delay
        
        # Add human-like randomness (sometimes people pause longer)
        if random.random() < 0.1:  # 10% chance of longer pause
            base_delay *= random.uniform(2.0, 4.0)
        
        return base_delay
    
    def wait(self) -> float:
        """
        Wait for the appropriate time before sending the next request.
        Returns the actual delay in seconds.
        """
        with self.lock:
            # Update counters
            self._update_request_counters()
            
            # Check if we're over the limits
            if self.daily_requests >= self.max_requests_per_day:
                logger.warning(f"Daily request limit reached ({self.max_requests_per_day}), delaying until tomorrow")
                
                # Calculate time until next day
                tomorrow = self.day_start + timedelta(days=1)
                seconds_until_tomorrow = (tomorrow - datetime.now()).total_seconds()
                
                # Add some jitter
                delay = seconds_until_tomorrow + random.uniform(60, 300)
                time.sleep(delay)
                
                # Reset counters and try again
                self._update_request_counters()
                return delay
            
            if self.hourly_requests >= self.max_requests_per_hour:
                logger.warning(f"Hourly request limit reached ({self.max_requests_per_hour}), delaying until next hour")
                
                # Calculate time until next hour
                next_hour = self.hour_start + timedelta(hours=1)
                seconds_until_next_hour = (next_hour - datetime.now()).total_seconds()
                
                # Add some jitter
                delay = seconds_until_next_hour + random.uniform(10, 60)
                time.sleep(delay)
                
                # Reset counters and try again
                self._update_request_counters()
                return delay
            
            # Refill tokens
            self._refill_tokens()
            
            # Determine if we need to wait for a token
            if self.tokens < 1:
                # No tokens available, need to wait
                time_to_next_token = 5.0  # Seconds until next token
                logger.debug(f"No tokens available, waiting {time_to_next_token}s for next token")
                time.sleep(time_to_next_token)
                self._refill_tokens()
            
            # Calculate delay for this request
            delay = self._calculate_delay()
            
            # Calculate time since last request
            now = datetime.now()
            time_since_last = (now - self.last_request_time).total_seconds()
            
            # If we need more delay, wait
            if time_since_last < delay:
                actual_delay = delay - time_since_last
                logger.debug(f"Rate limiting: waiting {actual_delay:.2f}s")
                time.sleep(actual_delay)
            else:
                actual_delay = 0
            
            # Update last request time and counters
            self.last_request_time = datetime.now()
            self.daily_requests += 1
            self.hourly_requests += 1
            self.tokens -= 1
            
            logger.debug(f"Request allowed: daily={self.daily_requests}/{self.max_requests_per_day}, "
                       f"hourly={self.hourly_requests}/{self.max_requests_per_hour}, "
                       f"tokens={self.tokens}/{DEFAULT_BURST_SIZE}")
            
            return actual_delay
    
    def limit(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function while respecting rate limits.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function
        """
        self.wait()
        return func(*args, **kwargs)


class RateLimitedClient:
    """A wrapper that adds rate limiting to an Instagram client."""
    
    def __init__(self, client, rate_limiter=None):
        """
        Initialize a rate-limited Instagram client.
        
        Args:
            client: The Instagram client to wrap
            rate_limiter: Optional rate limiter instance to use
        """
        self.client = client
        self.rate_limiter = rate_limiter or RateLimiter()
        
    def __getattr__(self, name):
        """
        Handle method calls by passing them to the client with rate limiting.
        
        This allows any method from the underlying client to be called
        with automatic rate limiting applied.
        """
        attr = getattr(self.client, name)
        
        if callable(attr):
            # If it's a method, return a rate-limited version
            def rate_limited_method(*args, **kwargs):
                return self.rate_limiter.limit(attr, *args, **kwargs)
            
            return rate_limited_method
        else:
            # If it's not a callable, just return the attribute
            return attr