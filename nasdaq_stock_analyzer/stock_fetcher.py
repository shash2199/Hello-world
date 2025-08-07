import requests
import time
import logging
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class StockFetcher:
    """Fetches stock ticker data from Financial Modeling Prep API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.FMP_API_KEY
        self.base_url = Config.FMP_BASE_URL
        
        if not self.api_key:
            raise ValueError("FMP API key is required")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to FMP API with error handling"""
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key to parameters
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Add delay to respect rate limits
            time.sleep(Config.REQUEST_DELAY)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON decode error for {endpoint}: {e}")
            return None
    
    def get_nasdaq_tickers(self) -> List[Dict]:
        """Get all NASDAQ-listed stock tickers"""
        logger.info("Fetching NASDAQ ticker list...")
        
        # Get NASDAQ constituents
        nasdaq_data = self._make_request("nasdaq_constituent")
        if not nasdaq_data:
            logger.warning("Failed to fetch NASDAQ constituents, trying stock list...")
            return self.get_all_stocks(exchange="NASDAQ")
        
        logger.info(f"Retrieved {len(nasdaq_data)} NASDAQ tickers")
        return nasdaq_data
    
    def get_all_stocks(self, exchange: str = None) -> List[Dict]:
        """Get all available stock tickers, optionally filtered by exchange"""
        logger.info("Fetching complete stock list...")
        
        stock_list = self._make_request("stock/list")
        if not stock_list:
            logger.error("Failed to fetch stock list")
            return []
        
        # Filter by exchange if specified
        if exchange:
            filtered_stocks = [
                stock for stock in stock_list 
                if stock.get('exchangeShortName', '').upper() == exchange.upper()
            ]
            logger.info(f"Filtered to {len(filtered_stocks)} stocks from {exchange}")
            return filtered_stocks
        
        logger.info(f"Retrieved {len(stock_list)} total stocks")
        return stock_list
    
    def get_sp500_tickers(self) -> List[Dict]:
        """Get S&P 500 stock tickers (alternative to NASDAQ for testing)"""
        logger.info("Fetching S&P 500 ticker list...")
        
        sp500_data = self._make_request("sp500_constituent")
        if not sp500_data:
            logger.error("Failed to fetch S&P 500 constituents")
            return []
        
        logger.info(f"Retrieved {len(sp500_data)} S&P 500 tickers")
        return sp500_data
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """Get detailed information about a specific stock"""
        logger.debug(f"Fetching info for {ticker}")
        
        # Get company profile
        profile_data = self._make_request(f"profile/{ticker}")
        if profile_data and len(profile_data) > 0:
            return profile_data[0]
        
        return None
    
    def validate_tickers(self, tickers: List[str], max_validate: int = 100) -> List[str]:
        """Validate that tickers exist and are tradeable"""
        logger.info(f"Validating {min(len(tickers), max_validate)} tickers...")
        
        valid_tickers = []
        
        for i, ticker in enumerate(tickers[:max_validate]):
            if i > 0 and i % 10 == 0:
                logger.info(f"Validated {i} tickers so far...")
            
            stock_info = self.get_stock_info(ticker)
            if stock_info and stock_info.get('isActivelyTrading', True):
                valid_tickers.append(ticker)
            else:
                logger.debug(f"Ticker {ticker} is not actively trading or not found")
        
        logger.info(f"Validated {len(valid_tickers)} out of {min(len(tickers), max_validate)} tickers")
        return valid_tickers

def get_nasdaq_symbols() -> List[str]:
    """Convenience function to get just the ticker symbols"""
    fetcher = StockFetcher()
    nasdaq_data = fetcher.get_nasdaq_tickers()
    
    # Extract just the symbols
    symbols = []
    for item in nasdaq_data:
        symbol = item.get('symbol')
        if symbol:
            symbols.append(symbol)
    
    return symbols

def get_company_name(ticker: str) -> str:
    """Get company name for a ticker"""
    fetcher = StockFetcher()
    stock_info = fetcher.get_stock_info(ticker)
    
    if stock_info:
        return stock_info.get('companyName', ticker)
    
    return ticker