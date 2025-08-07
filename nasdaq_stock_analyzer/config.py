import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the stock analyzer"""
    
    # API Keys
    FMP_API_KEY = os.getenv('FMP_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///stock_analysis.db')
    
    # OpenAI Settings
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '500'))
    
    # Analysis Configuration
    YOUR_PROMPT = os.getenv('YOUR_PROMPT', 'Analyze this stock ticker for investment potential in 2025. Focus on fundamentals, recent performance, and growth prospects.')
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # API Endpoints
    FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'
    
    # Rate limiting
    REQUEST_DELAY = 0.1  # 100ms delay between requests to avoid rate limits
    BATCH_SIZE = 10  # Process stocks in batches
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        required_vars = [
            ('FMP_API_KEY', cls.FMP_API_KEY),
            ('OPENAI_API_KEY', cls.OPENAI_API_KEY),
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True