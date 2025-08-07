import openai
import time
import logging
import tiktoken
from typing import Optional, Dict, Tuple
from config import Config

logger = logging.getLogger(__name__)

class OpenAIAnalyzer:
    """Handles OpenAI API interactions for stock analysis"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.OPENAI_MODEL
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize OpenAI client
        openai.api_key = self.api_key
        
        # Initialize tokenizer for cost calculation
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Cost per token (in USD) - Updated for 2025 pricing
        self.cost_per_token = self._get_model_costs()
    
    def _get_model_costs(self) -> Dict[str, float]:
        """Get current model pricing per token"""
        costs = {
            'gpt-4o': {
                'input': 0.000005,   # $5.00 per million tokens
                'output': 0.000015   # $15.00 per million tokens
            },
            'gpt-4o-mini': {
                'input': 0.00000015, # $0.15 per million tokens  
                'output': 0.0000006  # $0.60 per million tokens
            },
            'gpt-4-turbo': {
                'input': 0.00001,    # $10.00 per million tokens
                'output': 0.00003    # $30.00 per million tokens
            },
            'gpt-4': {
                'input': 0.00003,    # $30.00 per million tokens
                'output': 0.00006    # $60.00 per million tokens
            }
        }
        
        # Return costs for current model, default to gpt-4o-mini pricing
        return costs.get(self.model, costs['gpt-4o-mini'])
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            # Rough estimate: 1 token ≈ 0.75 words
            return int(len(text.split()) * 1.33)
    
    def estimate_cost(self, prompt: str, expected_response_tokens: int = None) -> float:
        """Estimate cost for API call"""
        input_tokens = self.count_tokens(prompt)
        output_tokens = expected_response_tokens or Config.MAX_TOKENS
        
        input_cost = input_tokens * self.cost_per_token['input']
        output_cost = output_tokens * self.cost_per_token['output']
        
        return input_cost + output_cost
    
    def analyze_stock(self, ticker: str, user_prompt: str = None) -> Tuple[Optional[str], Dict]:
        """
        Analyze a stock using OpenAI API
        
        Returns:
            Tuple of (response_text, metadata)
        """
        prompt = user_prompt or Config.YOUR_PROMPT
        
        # Create the full prompt with 2025 context
        full_prompt = f"""
        {prompt}
        
        Stock Ticker: {ticker}
        
        Please provide a comprehensive analysis using the most recent 2025 data available. Focus on:
        1. Current market position and recent performance
        2. Financial health and key metrics
        3. Growth prospects and competitive advantages
        4. Risk factors and challenges
        5. Investment recommendation with rationale
        
        Keep the analysis concise but informative, around 300-400 words.
        """
        
        # Estimate cost before making the call
        estimated_cost = self.estimate_cost(full_prompt)
        
        metadata = {
            'model': self.model,
            'estimated_cost': estimated_cost,
            'input_tokens': self.count_tokens(full_prompt),
            'timestamp': time.time()
        }
        
        try:
            logger.info(f"Analyzing {ticker} with OpenAI (estimated cost: ${estimated_cost:.6f})")
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial analyst with expertise in stock analysis. Provide accurate, data-driven insights based on the most current information available. Always use 2025 data when possible."
                    },
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ],
                max_tokens=Config.MAX_TOKENS,
                temperature=0.1,  # Low temperature for more consistent, factual responses
                top_p=0.9
            )
            
            # Extract response data
            response_text = response.choices[0].message.content.strip()
            
            # Update metadata with actual usage
            usage = response.get('usage', {})
            metadata.update({
                'actual_input_tokens': usage.get('prompt_tokens', metadata['input_tokens']),
                'actual_output_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            })
            
            # Calculate actual cost
            actual_cost = (
                metadata['actual_input_tokens'] * self.cost_per_token['input'] +
                metadata['actual_output_tokens'] * self.cost_per_token['output']
            )
            metadata['actual_cost'] = actual_cost
            
            logger.info(f"Analysis completed for {ticker} (actual cost: ${actual_cost:.6f})")
            
            return response_text, metadata
            
        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit hit for {ticker}: {e}")
            metadata['error'] = f"Rate limit: {str(e)}"
            return None, metadata
            
        except openai.error.InvalidRequestError as e:
            logger.error(f"Invalid request for {ticker}: {e}")
            metadata['error'] = f"Invalid request: {str(e)}"
            return None, metadata
            
        except openai.error.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            metadata['error'] = f"Authentication error: {str(e)}"
            return None, metadata
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing {ticker}: {e}")
            metadata['error'] = f"Unexpected error: {str(e)}"
            return None, metadata
    
    def batch_analyze(self, tickers: list, user_prompt: str = None, 
                     delay_between_calls: float = 1.0) -> Dict[str, Dict]:
        """
        Analyze multiple stocks with rate limiting
        
        Args:
            tickers: List of stock tickers
            user_prompt: Custom prompt (optional)
            delay_between_calls: Delay in seconds between API calls
        
        Returns:
            Dictionary with ticker as key and analysis result as value
        """
        results = {}
        total_cost = 0.0
        
        logger.info(f"Starting batch analysis of {len(tickers)} stocks")
        
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"Analyzing {ticker} ({i}/{len(tickers)})")
            
            try:
                response, metadata = self.analyze_stock(ticker, user_prompt)
                
                results[ticker] = {
                    'response': response,
                    'metadata': metadata,
                    'success': response is not None
                }
                
                if metadata.get('actual_cost'):
                    total_cost += metadata['actual_cost']
                
                # Rate limiting delay
                if i < len(tickers):  # Don't delay after the last request
                    time.sleep(delay_between_calls)
                    
            except Exception as e:
                logger.error(f"Failed to analyze {ticker}: {e}")
                results[ticker] = {
                    'response': None,
                    'metadata': {'error': str(e)},
                    'success': False
                }
        
        logger.info(f"Batch analysis completed. Total cost: ${total_cost:.6f}")
        
        return results