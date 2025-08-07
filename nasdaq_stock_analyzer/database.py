from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class StockAnalysis(Base):
    """Database model for storing stock analysis results"""
    __tablename__ = 'stock_analyses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String(255))
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    prompt_used = Column(Text)
    gpt_response = Column(Text)
    model_used = Column(String(50))
    tokens_used = Column(Integer)
    cost_estimate = Column(Float)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<StockAnalysis(ticker='{self.ticker}', date='{self.analysis_date}')>"

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        
    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self):
        """Get a new database session"""
        if not self.SessionLocal:
            self.initialize_database()
        return self.SessionLocal()
    
    def save_analysis(self, ticker, company_name, prompt_used, gpt_response, 
                     model_used, tokens_used=None, cost_estimate=None, error_message=None):
        """Save stock analysis to database"""
        session = self.get_session()
        try:
            analysis = StockAnalysis(
                ticker=ticker,
                company_name=company_name,
                prompt_used=prompt_used,
                gpt_response=gpt_response,
                model_used=model_used,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                error_message=error_message
            )
            
            session.add(analysis)
            session.commit()
            logger.info(f"Saved analysis for {ticker}")
            return analysis.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save analysis for {ticker}: {e}")
            raise
        finally:
            session.close()
    
    def get_recent_analysis(self, ticker, days=30):
        """Check if we have recent analysis for a ticker"""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            analysis = session.query(StockAnalysis).filter(
                StockAnalysis.ticker == ticker,
                StockAnalysis.analysis_date >= cutoff_date,
                StockAnalysis.error_message.is_(None)
            ).first()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to check recent analysis for {ticker}: {e}")
            return None
        finally:
            session.close()
    
    def get_analysis_summary(self):
        """Get summary statistics of analyses"""
        session = self.get_session()
        try:
            total_analyses = session.query(StockAnalysis).count()
            successful_analyses = session.query(StockAnalysis).filter(
                StockAnalysis.error_message.is_(None)
            ).count()
            
            total_cost = session.query(StockAnalysis.cost_estimate).filter(
                StockAnalysis.cost_estimate.isnot(None)
            ).all()
            
            cost_sum = sum([cost[0] for cost in total_cost if cost[0] is not None])
            
            return {
                'total_analyses': total_analyses,
                'successful_analyses': successful_analyses,
                'total_cost': cost_sum,
                'success_rate': (successful_analyses / total_analyses * 100) if total_analyses > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis summary: {e}")
            return {}
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()