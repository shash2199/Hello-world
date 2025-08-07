import json
import logging
import os
from datetime import datetime

# Set up logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda handler for the stock analysis task
    
    This function is designed to run monthly and analyze stocks in batches
    to stay within Lambda's 15-minute timeout limit.
    """
    
    try:
        # Import modules (done inside handler to reduce cold start time)
        from main import StockAnalysisOrchestrator
        
        # Get configuration from environment or event
        test_mode = event.get('test_mode', False)
        max_stocks = event.get('max_stocks', 50)  # Limit for Lambda execution
        batch_size = event.get('batch_size', 5)   # Smaller batches for Lambda
        user_prompt = event.get('user_prompt')
        
        logger.info(f"Lambda execution started - Test mode: {test_mode}, Max stocks: {max_stocks}")
        
        # Create orchestrator with Lambda-optimized settings
        orchestrator = StockAnalysisOrchestrator(
            test_mode=test_mode,
            max_stocks=max_stocks
        )
        
        # Run analysis
        stats = orchestrator.run_analysis(
            user_prompt=user_prompt,
            batch_size=batch_size
        )
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'message': 'Stock analysis completed',
                'stats': {
                    'successful_analyses': stats['successful_analyses'],
                    'failed_analyses': stats['failed_analyses'],
                    'skipped_analyses': stats['skipped_analyses'],
                    'total_cost': stats['total_cost'],
                    'duration_seconds': (stats['end_time'] - stats['start_time']).total_seconds() if stats['end_time'] and stats['start_time'] else 0
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
        logger.info(f"Lambda execution completed successfully: {stats['successful_analyses']} analyses, ${stats['total_cost']:.6f} cost")
        
        return response
        
    except Exception as e:
        error_msg = f"Lambda execution failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

# For testing locally
if __name__ == "__main__":
    # Test event
    test_event = {
        'test_mode': True,
        'max_stocks': 5,
        'user_prompt': 'Analyze this stock for 2025 investment potential'
    }
    
    # Test context (minimal)
    class TestContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.function_version = '1'
            self.memory_limit_in_mb = 512
    
    result = lambda_handler(test_event, TestContext())
    print(json.dumps(result, indent=2))