# NASDAQ Stock Analyzer

A cost-optimized, cloud-based system that automatically analyzes stock tickers using OpenAI's API and stores results in a database. Designed to run monthly on AWS Lambda with minimal cost while providing comprehensive stock analysis.

## 🚀 Features

- **Complete Stock Coverage**: Fetches all NASDAQ stock tickers using Financial Modeling Prep API
- **AI-Powered Analysis**: Uses OpenAI's GPT-4o-mini for cost-effective, high-quality analysis
- **Cloud-Native**: Runs on AWS Lambda with EventBridge scheduling
- **Cost-Optimized**: Designed to minimize costs while maximizing insights
- **Comprehensive Database**: Stores all analyses with cost tracking and metadata
- **Error Handling**: Robust error handling and retry mechanisms
- **Monitoring**: CloudWatch integration for logging and monitoring

## 💰 Cost Optimization

This system is designed for minimal cost:

### OpenAI API Costs
- **GPT-4o-mini**: $0.15/$0.60 per million input/output tokens
- **Estimated cost per stock**: ~$0.0002-0.0010 per analysis
- **Monthly cost for 500 stocks**: ~$0.10-0.50

### AWS Costs
- **Lambda**: ~$0.20/month (within free tier for moderate usage)
- **RDS t3.micro**: ~$13/month (free tier eligible for first year)
- **EventBridge**: Free for up to 14 million events/month
- **CloudWatch Logs**: ~$0.50/month for 1GB

### Financial Modeling Prep API
- **Free tier**: 250 requests/day
- **Premium**: Starting at $15/month for unlimited requests

**Total estimated monthly cost**: $14-30/month

## 📋 Prerequisites

- AWS Account with appropriate permissions
- Python 3.11+
- AWS CLI configured
- Terraform installed
- OpenAI API key
- Financial Modeling Prep API key

## 🛠️ Installation & Setup

### 1. Clone and Setup Environment

```bash
git clone <your-repo>
cd nasdaq_stock_analyzer

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Configure Environment Variables

```bash
# Required API Keys
export FMP_API_KEY="your_fmp_api_key"
export OPENAI_API_KEY="your_openai_api_key"

# Optional: Database password (will be generated if not provided)
export DB_PASSWORD="your_secure_password"

# Optional: AWS region (defaults to us-east-1)
export AWS_REGION="us-east-1"
```

### 3. Deploy to AWS

```bash
cd deploy
./deploy.sh
```

The deployment script will:
- Package the Lambda function
- Create AWS infrastructure using Terraform
- Set up monthly scheduling
- Test the deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   EventBridge   │───▶│   Lambda     │───▶│ PostgreSQL │
│  (Monthly)      │    │  Function    │    │ Database   │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │   OpenAI     │
                       │     API      │
                       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │    FMP       │
                       │    API       │
                       └──────────────┘
```

## 🔧 Configuration

### Lambda Function Settings
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 15 minutes
- **Schedule**: 1st of every month at 6 AM UTC

### Database Schema
```sql
-- Stock analyses table
CREATE TABLE stock_analyses (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt_used TEXT,
    gpt_response TEXT,
    model_used VARCHAR(50),
    tokens_used INTEGER,
    cost_estimate FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🎯 Usage

### Local Testing

```bash
# Test with a few stocks
python main.py --test --max-stocks 5

# Run with custom prompt
python main.py --test --max-stocks 10 --prompt "Analyze this stock for ESG investment potential"

# Production run (all NASDAQ stocks)
python main.py
```

### Lambda Testing

```bash
# Test deployed Lambda function
aws lambda invoke \
  --function-name nasdaq-stock-analyzer-function \
  --payload '{"test_mode": true, "max_stocks": 5}' \
  response.json
```

### Database Queries

```python
from database import db_manager

# Get analysis summary
summary = db_manager.get_analysis_summary()
print(f"Total analyses: {summary['total_analyses']}")
print(f"Success rate: {summary['success_rate']}%")
print(f"Total cost: ${summary['total_cost']:.6f}")

# Get recent analysis for a stock
analysis = db_manager.get_recent_analysis('AAPL', days=30)
if analysis:
    print(f"Recent analysis for AAPL: {analysis.gpt_response}")
```

## 📊 Monitoring

### CloudWatch Logs
Monitor function execution in CloudWatch:
```bash
aws logs tail /aws/lambda/nasdaq-stock-analyzer-function --follow
```

### Cost Monitoring
The system tracks costs automatically:
- Per-stock analysis costs
- Total monthly costs
- Token usage statistics

### Performance Metrics
- Analysis success rate
- Processing time per stock
- Error rates and types

## 🔄 Customization

### Modify Analysis Prompt
Edit the prompt in `config.py` or pass via environment variable:
```python
YOUR_PROMPT = "Analyze this stock for investment potential in 2025. Focus on sustainability and growth prospects."
```

### Change Schedule
Modify the cron expression in `terraform/main.tf`:
```hcl
schedule_expression = "cron(0 6 1 * ? *)"  # Monthly
# Or for weekly: "cron(0 6 ? * MON *)"
```

### Adjust Processing Limits
Configure in environment variables:
```bash
MAX_TOKENS=500        # Response length
BATCH_SIZE=10         # Stocks per batch
REQUEST_DELAY=0.1     # Delay between API calls
```

## 🐛 Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Increase `REQUEST_DELAY` in config
   - Reduce `BATCH_SIZE`
   - Check API key quotas

2. **Lambda Timeout**
   - Reduce `max_stocks` parameter
   - Increase batch processing delay
   - Use smaller batches

3. **Database Connection Issues**
   - Check VPC configuration
   - Verify security group rules
   - Ensure RDS is in private subnet

4. **High Costs**
   - Use `gpt-4o-mini` instead of `gpt-4o`
   - Reduce `MAX_TOKENS`
   - Implement caching for recent analyses

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Lambda logs:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/nasdaq"
```

## 🔒 Security

- API keys stored as Lambda environment variables
- Database in private subnet
- IAM roles with minimal permissions
- VPC isolation for Lambda and RDS

## 📈 Scaling

### For Higher Volume
1. **Increase Lambda memory** (scales CPU proportionally)
2. **Use multiple Lambda functions** with different ticker ranges
3. **Implement SQS queue** for better error handling
4. **Consider ECS Fargate** for very large datasets

### For Lower Costs
1. **Use SQLite** instead of RDS for smaller datasets
2. **Reduce analysis frequency** (quarterly instead of monthly)
3. **Filter stocks** by market cap or volume
4. **Implement intelligent caching**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## ☁️ Alternative Deployment Options

### Option 1: Cost-Optimized (SQLite)
For minimal costs, use SQLite instead of RDS:
```bash
export DATABASE_URL="sqlite:///stock_analysis.db"
```

### Option 2: Serverless Aurora
For better scalability:
```hcl
# In terraform/main.tf
resource "aws_rds_cluster" "aurora" {
  engine             = "aurora-postgresql"
  engine_mode        = "serverless"
  # ... configuration
}
```

### Option 3: Google Cloud Run
Deploy on Google Cloud for potentially lower costs:
```dockerfile
# Dockerfile included for containerized deployment
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Create an issue on GitHub
4. Contact support team

---

**Happy analyzing! 📈🚀**