import requests
import random
import string
from enum import Enum
from typing import List, Dict, Optional, Callable

# ✅ In-memory cache
shortened_urls_cache = {}

class ShortenerMode(Enum):
    SEQUENTIAL = "sequential"  # Try services in order until one works
    RANDOM = "random"          # Randomly select from available services
    PRIORITY = "priority"      # Use priority-based selection
    FALLBACK = "fallback"      # Use primary, fallback to others if fails
    ALL = "all"                # Return multiple shortened URLs

class ShortenerSettings:
    def __init__(self, 
                 mode: ShortenerMode = ShortenerMode.SEQUENTIAL,
                 primary_service: str = None,
                 enabled_services: List[str] = None,
                 timeout: int = 10,
                 max_retries: int = 2,
                 cache_enabled: bool = True,
                 prefer_fastest: bool = False,
                 custom_alias_length: int = 8):
        
        self.mode = mode
        self.primary_service = primary_service
        self.enabled_services = enabled_services or [
            'tinyurl', 'dagd', 'isgd', 'cuttly', 'shortio', 'custom'
        ]
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled
        self.prefer_fastest = prefer_fastest
        self.custom_alias_length = custom_alias_length

def generate_random_alphanumeric(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

class URLShortener:
    def __init__(self, client=None, settings: ShortenerSettings = None):
        self.client = client
        self.settings = settings or ShortenerSettings()
        self.service_stats = {}  # Track service performance
        
    def get_short(self, url, settings_override: ShortenerSettings = None) -> str:
        """Main method to get shortened URL based on settings"""
        settings = settings_override or self.settings
        
        # Check cache if enabled
        if settings.cache_enabled and url in shortened_urls_cache:
            return shortened_urls_cache[url]
        
        result = None
        
        if settings.mode == ShortenerMode.SEQUENTIAL:
            result = self._sequential_shorten(url, settings)
        elif settings.mode == ShortenerMode.RANDOM:
            result = self._random_shorten(url, settings)
        elif settings.mode == ShortenerMode.PRIORITY:
            result = self._priority_shorten(url, settings)
        elif settings.mode == ShortenerMode.FALLBACK:
            result = self._fallback_shorten(url, settings)
        elif settings.mode == ShortenerMode.ALL:
            return self._get_all_shortened(url, settings)
        
        # Cache result if successful
        if result and result != url and settings.cache_enabled:
            shortened_urls_cache[url] = result
            
        return result or url
    
    def _sequential_shorten(self, url: str, settings: ShortenerSettings) -> str:
        """Try services in order until one works"""
        services = self._get_available_services(settings)
        
        for service_name in services:
            try:
                short_url = self._call_service(service_name, url, settings)
                if short_url and short_url != url:
                    self._update_stats(service_name, success=True)
                    return short_url
            except Exception as e:
                self._update_stats(service_name, success=False)
                print(f"[{service_name} Error] {e}")
                continue
                
        return url
    
    def _random_shorten(self, url: str, settings: ShortenerSettings) -> str:
        """Randomly select from available services"""
        services = self._get_available_services(settings)
        if not services:
            return url
            
        random.shuffle(services)
        
        for service_name in services:
            try:
                short_url = self._call_service(service_name, url, settings)
                if short_url and short_url != url:
                    self._update_stats(service_name, success=True)
                    return short_url
            except Exception as e:
                self._update_stats(service_name, success=False)
                print(f"[{service_name} Error] {e}")
                continue
                
        return url
    
    def _priority_shorten(self, url: str, settings: ShortenerSettings) -> str:
        """Use priority-based selection (fastest/most reliable first)"""
        services = self._get_available_services(settings)
        
        # Sort by success rate if we have stats
        if self.service_stats and settings.prefer_fastest:
            services.sort(key=lambda s: self.service_stats.get(s, {}).get('success_rate', 0), reverse=True)
        
        # If primary service is specified, try it first
        if settings.primary_service and settings.primary_service in services:
            services.remove(settings.primary_service)
            services.insert(0, settings.primary_service)
        
        for service_name in services:
            try:
                short_url = self._call_service(service_name, url, settings)
                if short_url and short_url != url:
                    self._update_stats(service_name, success=True)
                    return short_url
            except Exception as e:
                self._update_stats(service_name, success=False)
                print(f"[{service_name} Error] {e}")
                continue
                
        return url
    
    def _fallback_shorten(self, url: str, settings: ShortenerSettings) -> str:
        """Use primary service, fallback to others if fails"""
        services = self._get_available_services(settings)
        
        primary = settings.primary_service
        if not primary or primary not in services:
            primary = services[0] if services else None
        
        if primary:
            # Try primary service first
            try:
                short_url = self._call_service(primary, url, settings)
                if short_url and short_url != url:
                    self._update_stats(primary, success=True)
                    return short_url
            except Exception as e:
                self._update_stats(primary, success=False)
                print(f"[Primary {primary} Error] {e}")
        
        # Fallback to other services
        fallback_services = [s for s in services if s != primary]
        for service_name in fallback_services:
            try:
                short_url = self._call_service(service_name, url, settings)
                if short_url and short_url != url:
                    self._update_stats(service_name, success=True)
                    return short_url
            except Exception as e:
                self._update_stats(service_name, success=False)
                print(f"[Fallback {service_name} Error] {e}")
                continue
                
        return url
    
    def _get_all_shortened(self, url: str, settings: ShortenerSettings) -> Dict[str, str]:
        """Get shortened URLs from all available services"""
        services = self._get_available_services(settings)
        results = {}
        
        for service_name in services:
            try:
                short_url = self._call_service(service_name, url, settings)
                if short_url and short_url != url:
                    results[service_name] = short_url
                    self._update_stats(service_name, success=True)
                else:
                    results[service_name] = url
                    self._update_stats(service_name, success=False)
            except Exception as e:
                results[service_name] = url
                self._update_stats(service_name, success=False)
                print(f"[{service_name} Error] {e}")
        
        return results
    
    def _get_available_services(self, settings: ShortenerSettings) -> List[str]:
        """Get list of available services based on configuration and client setup"""
        available = []
        
        for service in settings.enabled_services:
            if self._is_service_available(service):
                available.append(service)
                
        return available
    
    def _is_service_available(self, service_name: str) -> bool:
        """Check if a service is available (has required API keys, etc.)"""
        if service_name in ['tinyurl', 'dagd', 'isgd']:
            return True  # No API key required
            
        elif service_name == 'cuttly':
            return hasattr(self.client, 'cuttly_api_key') and self.client.cuttly_api_key != "YOUR_CUTTLY_API_KEY"
            
        elif service_name == 'shortio':
            return (hasattr(self.client, 'shortio_api_key') and 
                   self.client.shortio_api_key != "YOUR_SHORTIO_API_KEY" and
                   hasattr(self.client, 'shortio_domain'))
            
        elif service_name == 'custom':
            return (hasattr(self.client, 'short_url') and 
                   hasattr(self.client, 'short_api'))
                   
        return False
    
    def _call_service(self, service_name: str, url: str, settings: ShortenerSettings) -> str:
        """Call specific shortening service"""
        service_methods = {
            'tinyurl': self._try_tinyurl,
            'dagd': self._try_dagd,
            'isgd': self._try_isgd,
            'cuttly': self._try_cuttly,
            'shortio': self._try_shortio,
            'custom': self._try_custom_shortener
        }
        
        if service_name in service_methods:
            return service_methods[service_name](url, settings)
        
        return url
    
    def _update_stats(self, service_name: str, success: bool):
        """Update service performance statistics"""
        if service_name not in self.service_stats:
            self.service_stats[service_name] = {'total': 0, 'success': 0}
        
        self.service_stats[service_name]['total'] += 1
        if success:
            self.service_stats[service_name]['success'] += 1
        
        # Calculate success rate
        stats = self.service_stats[service_name]
        stats['success_rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 0
    
    def get_service_stats(self) -> Dict:
        """Get performance statistics for all services"""
        return self.service_stats
    
    def clear_cache(self):
        """Clear the URL cache"""
        shortened_urls_cache.clear()
    
    # Service implementations
    def _try_tinyurl(self, url: str, settings: ShortenerSettings) -> str:
        """Try TinyURL service"""
        try:
            api_url = f"http://tinyurl.com/api-create.php?url={url}"
            response = requests.get(api_url, timeout=settings.timeout)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text
        except Exception as e:
            print(f"[TinyURL Error] {e}")
        return url
    
    def _try_dagd(self, url: str, settings: ShortenerSettings) -> str:
        """Try da.gd service"""
        try:
            api_url = f"https://da.gd/s?url={url}"
            response = requests.get(api_url, timeout=settings.timeout)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            print(f"[da.gd Error] {e}")
        return url
    
    def _try_isgd(self, url: str, settings: ShortenerSettings) -> str:
        """Try is.gd service"""
        try:
            api_url = f"https://is.gd/create.php?format=simple&url={url}"
            response = requests.get(api_url, timeout=settings.timeout)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            print(f"[is.gd Error] {e}")
        return url
    
    def _try_cuttly(self, url: str, settings: ShortenerSettings) -> str:
        """Try Cutt.ly service"""
        try:
            api_key = getattr(self.client, 'cuttly_api_key', None)
            if not api_key or api_key == "YOUR_CUTTLY_API_KEY":
                return url
                
            api_url = f"https://cutt.ly/api/api.php?key={api_key}&short={url}"
            response = requests.get(api_url, timeout=settings.timeout)
            rjson = response.json()
            
            if rjson.get("url", {}).get("status") == 7:  # Success status
                return rjson["url"]["shortLink"]
        except Exception as e:
            print(f"[Cuttly Error] {e}")
        return url
    
    def _try_shortio(self, url: str, settings: ShortenerSettings) -> str:
        """Try Short.io service"""
        try:
            api_key = getattr(self.client, 'shortio_api_key', None)
            domain = getattr(self.client, 'shortio_domain', 'go.askyourpdf.com')
            
            if not api_key or api_key == "YOUR_SHORTIO_API_KEY":
                return url
                
            api_url = "https://api.short.io/links"
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            data = {
                'domain': domain,
                'originalURL': url
            }
            
            response = requests.post(api_url, json=data, headers=headers, timeout=settings.timeout)
            rjson = response.json()
            
            if response.status_code == 200:
                return rjson.get("shortURL", url)
        except Exception as e:
            print(f"[Short.io Error] {e}")
        return url
    
    def _try_custom_shortener(self, url: str, settings: ShortenerSettings) -> str:
        """Try custom shortener service"""
        try:
            alias = generate_random_alphanumeric(settings.custom_alias_length)
            api_url = f"https://{self.client.short_url}/api?api={self.client.short_api}&url={url}&alias={alias}"
            response = requests.get(api_url, timeout=settings.timeout)
            rjson = response.json()

            if rjson.get("status") == "success" and response.status_code == 200:
                return rjson.get("shortenedUrl", url)
        except Exception as e:
            print(f"[Custom Shortener Error] {e}")
        return url

# Legacy function for backward compatibility
def get_short(url, client, mode: str = "sequential", primary_service: str = None):
    """Legacy function for backward compatibility"""
    settings = ShortenerSettings(
        mode=ShortenerMode(mode),
        primary_service=primary_service
    )
    shortener = URLShortener(client, settings)
    return shortener.get_short(url)
