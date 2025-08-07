#!/bin/bash

# NASDAQ Stock Analyzer - Deployment Script
# This script packages and deploys the stock analysis application to AWS

set -e  # Exit on any error

# Configuration
PROJECT_NAME="nasdaq-stock-analyzer"
AWS_REGION="${AWS_REGION:-us-east-1}"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message $BLUE "🚀 Starting deployment of ${PROJECT_NAME}"

# Check prerequisites
print_message $YELLOW "📋 Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_message $RED "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_message $RED "❌ Terraform not found. Please install it first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_message $RED "❌ Python 3 not found. Please install it first."
    exit 1
fi

# Check if zip is installed
if ! command -v zip &> /dev/null; then
    print_message $RED "❌ zip not found. Please install it first."
    exit 1
fi

print_message $GREEN "✅ All prerequisites satisfied"

# Check if API keys are provided
if [ -z "$FMP_API_KEY" ]; then
    print_message $RED "❌ FMP_API_KEY environment variable not set"
    echo "Please set your Financial Modeling Prep API key:"
    echo "export FMP_API_KEY='your_api_key_here'"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    print_message $RED "❌ OPENAI_API_KEY environment variable not set"
    echo "Please set your OpenAI API key:"
    echo "export OPENAI_API_KEY='your_api_key_here'"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    print_message $YELLOW "⚠️  DB_PASSWORD environment variable not set, generating random password..."
    export DB_PASSWORD=$(openssl rand -base64 32)
    print_message $BLUE "Generated database password: ${DB_PASSWORD}"
    echo "Please save this password securely!"
fi

print_message $GREEN "✅ API keys configured"

# Create deployment directory
DEPLOY_DIR="../lambda_deployment"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

print_message $YELLOW "📦 Creating Lambda deployment package..."

# Go to project root
cd ..

# Copy Python files
cp *.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/

# Install dependencies in deployment directory
cd $DEPLOY_DIR

print_message $YELLOW "📥 Installing Python dependencies..."

# Create virtual environment for clean package installation
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt -t .

# Remove virtual environment
deactivate
rm -rf venv

# Remove unnecessary files to reduce package size
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

# Create the zip file
print_message $YELLOW "🗜️  Creating deployment package..."
zip -r lambda_deployment.zip . -x "*.git*" "*.DS_Store*" "venv/*" > /dev/null

print_message $GREEN "✅ Lambda package created successfully"

# Go to Terraform directory
cd ../deploy/terraform

print_message $YELLOW "🏗️  Initializing Terraform..."

# Initialize Terraform
terraform init

print_message $YELLOW "📋 Planning Terraform deployment..."

# Create terraform.tfvars file
cat > terraform.tfvars << EOF
fmp_api_key = "${FMP_API_KEY}"
openai_api_key = "${OPENAI_API_KEY}"
database_password = "${DB_PASSWORD}"
aws_region = "${AWS_REGION}"
project_name = "${PROJECT_NAME}"
environment = "prod"
EOF

# Plan deployment
terraform plan -var-file="terraform.tfvars"

# Ask for confirmation
print_message $YELLOW "⚠️  Ready to deploy infrastructure. This will create AWS resources and may incur costs."
read -p "Do you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_message $YELLOW "Deployment cancelled"
    exit 0
fi

print_message $YELLOW "🚀 Deploying infrastructure..."

# Apply Terraform configuration
terraform apply -var-file="terraform.tfvars" -auto-approve

print_message $GREEN "✅ Infrastructure deployed successfully!"

# Get outputs
LAMBDA_FUNCTION_NAME=$(terraform output -raw lambda_function_name)
DB_ENDPOINT=$(terraform output -raw database_endpoint)
LOG_GROUP=$(terraform output -raw cloudwatch_log_group)

print_message $BLUE "📊 Deployment Summary:"
echo "Lambda Function: $LAMBDA_FUNCTION_NAME"
echo "Database Endpoint: $DB_ENDPOINT"
echo "Log Group: $LOG_GROUP"
echo "Region: $AWS_REGION"

print_message $YELLOW "🧪 Testing Lambda function..."

# Test Lambda function
aws lambda invoke \
    --function-name $LAMBDA_FUNCTION_NAME \
    --payload '{"test_mode": true, "max_stocks": 3}' \
    --region $AWS_REGION \
    response.json

if [ $? -eq 0 ]; then
    print_message $GREEN "✅ Lambda function test successful"
    cat response.json | python3 -m json.tool
    rm response.json
else
    print_message $RED "❌ Lambda function test failed"
fi

print_message $GREEN "🎉 Deployment completed successfully!"
print_message $BLUE "📝 Next steps:"
echo "1. Monitor the logs in CloudWatch: $LOG_GROUP"
echo "2. The function will run automatically on the 1st of each month at 6 AM UTC"
echo "3. Check the database for analysis results"
echo "4. Adjust the max_stocks parameter in EventBridge rule if needed"

print_message $YELLOW "💰 Cost estimate:"
echo "- Lambda: ~$0.20/month (assuming 100 stocks analyzed monthly)"
echo "- RDS t3.micro: ~$13/month (can be free tier eligible)"
echo "- NAT Gateway: ~$45/month"
echo "- OpenAI API: Variable based on usage (~$0.02-0.10 per stock with gpt-4o-mini)"
echo ""
echo "Total estimated cost: ~$58-60/month"

print_message $BLUE "🔧 To modify the schedule or configuration:"
echo "1. Edit the terraform/main.tf file"
echo "2. Run 'terraform apply' to update the infrastructure"

print_message $GREEN "Deployment script completed! 🚀"