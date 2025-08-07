#!/usr/bin/env python3
"""
Nasdaq Stock Analyzer - Main Script

This script fetches all NASDAQ stock tickers, analyzes them using OpenAI's API,
and stores the results in a database. Designed for cost-effective operation with
comprehensive error handling and optimization features.

Author: AI Assistant
Date: 2025
"""

import logging
import sys
import time
from typing import List, Dict
import argparse
from datetime import datetime

from config import Config
from stock_fetcher import StockFetcher, get_nasdaq_symbols, get_company_name
from openai_analyzer import OpenAIAnalyzer
from database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class StockAnalysisOrchestrator:
    """Main orchestrator for the stock analysis process"""
    
    def __init__(self, test_mode: bool = False, max_stocks: int = None):
        self.test_mode = test_mode
        self.max_stocks = max_stocks
        
        # Validate configuration
        Config.validate_config()
        
        # Initialize components
        self.stock_fetcher = StockFetcher()
        self.ai_analyzer = OpenAIAnalyzer()
        self.db_manager = db_manager
        
        # Initialize database
        self.db_manager.initialize_database()
        
        # Performance tracking
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_stocks': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'skipped_analyses': 0,
            'total_cost': 0.0,
            'errors': []
        }
    
    def get_stock_tickers(self) -> List[str]:
        """Get list of stock tickers to analyze"""
        logger.info("Fetching stock tickers...")
        
        if self.test_mode:
            # For testing, use S&P 500 (smaller, more stable list)
            sp500_data = self.stock_fetcher.get_sp500_tickers()
            tickers = [item.get('symbol') for item in sp500_data if item.get('symbol')]
            logger.info(f"Test mode: Using {len(tickers)} S&P 500 stocks")
        else:
            # Production: Get all NASDAQ stocks
            tickers = get_nasdaq_symbols()
            logger.info(f"Production mode: Retrieved {len(tickers)} NASDAQ stocks")
        
        # Limit number of stocks if specified
        if self.max_stocks and len(tickers) > self.max_stocks:
            tickers = tickers[:self.max_stocks]
            logger.info(f"Limited to {self.max_stocks} stocks for analysis")
        
        return tickers
    
    def should_skip_ticker(self, ticker: str) -> bool:
        """Check if we should skip analyzing this ticker"""
        # Check if we have recent analysis (within 30 days)
        recent_analysis = self.db_manager.get_recent_analysis(ticker, days=30)
        if recent_analysis:
            logger.debug(f"Skipping {ticker} - recent analysis exists")
            return True
        
        return False
    
    def analyze_single_stock(self, ticker: str, user_prompt: str = None) -> Dict:
        """Analyze a single stock and save to database"""
        result = {
            'ticker': ticker,
            'success': False,
            'cost': 0.0,
            'error': None
        }
        
        try:
            # Get company name
            company_name = get_company_name(ticker)
            
            # Perform AI analysis
            response, metadata = self.ai_analyzer.analyze_stock(ticker, user_prompt)
            
            if response:
                # Save successful analysis to database
                self.db_manager.save_analysis(
                    ticker=ticker,
                    company_name=company_name,
                    prompt_used=user_prompt or Config.YOUR_PROMPT,
                    gpt_response=response,
                    model_used=metadata.get('model'),
                    tokens_used=metadata.get('total_tokens'),
                    cost_estimate=metadata.get('actual_cost'),
                    error_message=None
                )
                
                result.update({
                    'success': True,
                    'cost': metadata.get('actual_cost', 0.0),
                    'tokens': metadata.get('total_tokens', 0),
                    'company_name': company_name
                })
                
                logger.info(f"✓ Successfully analyzed {ticker} ({company_name})")
                
            else:
                # Save failed analysis
                error_msg = metadata.get('error', 'Unknown error')
                self.db_manager.save_analysis(
                    ticker=ticker,
                    company_name=company_name,
                    prompt_used=user_prompt or Config.YOUR_PROMPT,
                    gpt_response=None,
                    model_used=metadata.get('model'),
                    error_message=error_msg
                )
                
                result['error'] = error_msg
                logger.warning(f"✗ Failed to analyze {ticker}: {error_msg}")
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            result['error'] = error_msg
            logger.error(f"✗ Error analyzing {ticker}: {e}")
            
            # Try to save error to database
            try:
                self.db_manager.save_analysis(
                    ticker=ticker,
                    company_name=ticker,
                    prompt_used=user_prompt or Config.YOUR_PROMPT,
                    gpt_response=None,
                    model_used=Config.OPENAI_MODEL,
                    error_message=error_msg
                )
            except Exception as db_error:
                logger.error(f"Failed to save error to database: {db_error}")
        
        return result
    
    def run_analysis(self, user_prompt: str = None, batch_size: int = None) -> Dict:
        """Run the complete stock analysis process"""
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info("=" * 50)
        logger.info("NASDAQ STOCK ANALYSIS STARTING")
        logger.info("=" * 50)
        logger.info(f"Model: {Config.OPENAI_MODEL}")
        logger.info(f"Test mode: {self.test_mode}")
        logger.info(f"Max stocks: {self.max_stocks or 'unlimited'}")
        
        try:
            # Get stock tickers
            tickers = self.get_stock_tickers()
            self.stats['total_stocks'] = len(tickers)
            
            if not tickers:
                logger.error("No stock tickers found!")
                return self.stats
            
            # Filter out tickers we should skip
            tickers_to_analyze = []
            for ticker in tickers:
                if not self.should_skip_ticker(ticker):
                    tickers_to_analyze.append(ticker)
                else:
                    self.stats['skipped_analyses'] += 1
            
            logger.info(f"Analyzing {len(tickers_to_analyze)} stocks (skipping {self.stats['skipped_analyses']} recent analyses)")
            
            # Process in batches for better resource management
            batch_size = batch_size or Config.BATCH_SIZE
            
            for i in range(0, len(tickers_to_analyze), batch_size):
                batch = tickers_to_analyze[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(tickers_to_analyze) + batch_size - 1) // batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)")
                
                # Process each stock in the batch
                for ticker in batch:
                    result = self.analyze_single_stock(ticker, user_prompt)
                    
                    # Update statistics
                    if result['success']:
                        self.stats['successful_analyses'] += 1
                        self.stats['total_cost'] += result['cost']
                    else:
                        self.stats['failed_analyses'] += 1
                        if result['error']:
                            self.stats['errors'].append(f"{ticker}: {result['error']}")
                    
                    # Progress update
                    completed = self.stats['successful_analyses'] + self.stats['failed_analyses']
                    logger.info(f"Progress: {completed}/{len(tickers_to_analyze)} ({completed/len(tickers_to_analyze)*100:.1f}%)")
                
                # Delay between batches to be respectful to APIs
                if i + batch_size < len(tickers_to_analyze):
                    logger.info(f"Waiting 2 seconds between batches...")
                    time.sleep(2)
        
        except KeyboardInterrupt:
            logger.warning("Analysis interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error during analysis: {e}")
            self.stats['errors'].append(f"Fatal error: {str(e)}")
        
        finally:
            # Finalize statistics
            self.stats['end_time'] = datetime.utcnow()
            self._print_final_summary()
        
        return self.stats
    
    def _print_final_summary(self):
        """Print final analysis summary"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("=" * 50)
        logger.info("ANALYSIS COMPLETE - SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Total stocks processed: {self.stats['successful_analyses'] + self.stats['failed_analyses']}")
        logger.info(f"Successful analyses: {self.stats['successful_analyses']}")
        logger.info(f"Failed analyses: {self.stats['failed_analyses']}")
        logger.info(f"Skipped (recent): {self.stats['skipped_analyses']}")
        logger.info(f"Total cost: ${self.stats['total_cost']:.6f}")
        
        if self.stats['successful_analyses'] > 0:
            avg_cost = self.stats['total_cost'] / self.stats['successful_analyses']
            logger.info(f"Average cost per analysis: ${avg_cost:.6f}")
        
        # Success rate
        total_attempted = self.stats['successful_analyses'] + self.stats['failed_analyses']
        if total_attempted > 0:
            success_rate = (self.stats['successful_analyses'] / total_attempted) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        
        # Show database summary
        db_summary = self.db_manager.get_analysis_summary()
        if db_summary:
            logger.info("=" * 30)
            logger.info("DATABASE SUMMARY")
            logger.info("=" * 30)
            logger.info(f"Total analyses in DB: {db_summary.get('total_analyses', 0)}")
            logger.info(f"Successful analyses in DB: {db_summary.get('successful_analyses', 0)}")
            logger.info(f"Total cost in DB: ${db_summary.get('total_cost', 0):.6f}")
            logger.info(f"Overall success rate: {db_summary.get('success_rate', 0):.1f}%")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analyze NASDAQ stocks using OpenAI')
    parser.add_argument('--test', action='store_true', help='Run in test mode (S&P 500 stocks only)')
    parser.add_argument('--max-stocks', type=int, help='Maximum number of stocks to analyze')
    parser.add_argument('--prompt', type=str, help='Custom analysis prompt')
    parser.add_argument('--batch-size', type=int, default=Config.BATCH_SIZE, help='Batch size for processing')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = StockAnalysisOrchestrator(
        test_mode=args.test,
        max_stocks=args.max_stocks
    )
    
    # Run analysis
    stats = orchestrator.run_analysis(
        user_prompt=args.prompt,
        batch_size=args.batch_size
    )
    
    # Exit with appropriate code
    if stats['successful_analyses'] > 0:
        logger.info("Analysis completed successfully!")
        sys.exit(0)
    else:
        logger.error("No successful analyses completed!")
        sys.exit(1)


if __name__ == "__main__":
    main()