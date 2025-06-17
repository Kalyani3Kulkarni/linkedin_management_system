"""
Base agent class for all LinkedIn management agents.
"""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.database import AgentActivity, get_db
from app.models.schemas import AgentActivityCreate
from app.config.settings import settings


class BaseAgent(ABC):
    """Base class for all agents in the LinkedIn Management System."""
    
    def __init__(self, name: str):
        """Initialize the base agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.logger = logger.bind(agent=name)
        self.settings = settings
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the agent's main functionality with error handling and logging.
        
        Args:
            **kwargs: Arguments specific to each agent
            
        Returns:
            Dict containing execution results
        """
        start_time = datetime.utcnow()
        execution_details = {"input_params": kwargs}
        
        try:
            self.logger.info(f"Starting {self.name} execution", **kwargs)
            
            # Validate input parameters
            self._validate_input(**kwargs)
            
            # Execute the main agent logic
            result = await self._execute_logic(**kwargs)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            execution_details.update({
                "result": result,
                "execution_time": execution_time
            })
            
            # Log successful execution
            await self._log_activity(
                activity_type="execution",
                status="success",
                details=execution_details,
                execution_time=execution_time
            )
            
            self.logger.info(
                f"{self.name} execution completed successfully",
                execution_time=execution_time
            )
            
            return {
                "success": True,
                "data": result,
                "execution_time": execution_time,
                "agent": self.name
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_message = str(e)
            
            # Log failed execution
            await self._log_activity(
                activity_type="execution",
                status="error",
                details=execution_details,
                error_message=error_message,
                execution_time=execution_time
            )
            
            self.logger.error(
                f"{self.name} execution failed",
                error=error_message,
                execution_time=execution_time
            )
            
            return {
                "success": False,
                "error": error_message,
                "execution_time": execution_time,
                "agent": self.name
            }
    
    @abstractmethod
    async def _execute_logic(self, **kwargs) -> Any:
        """Execute the main logic of the agent.
        
        This method must be implemented by each specific agent.
        
        Args:
            **kwargs: Agent-specific parameters
            
        Returns:
            Agent-specific results
        """
        pass
    
    def _validate_input(self, **kwargs) -> None:
        """Validate input parameters.
        
        Override this method in specific agents for custom validation.
        
        Args:
            **kwargs: Parameters to validate
            
        Raises:
            ValueError: If validation fails
        """
        pass
    
    async def _log_activity(
        self,
        activity_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        execution_time: Optional[float] = None
    ) -> None:
        """Log agent activity to database.
        
        Args:
            activity_type: Type of activity performed
            status: Status of the activity (success, error, pending)
            details: Additional details about the activity
            error_message: Error message if status is error
            execution_time: Time taken to execute in seconds
        """
        try:
            # Note: In a real application, you might want to use async database operations
            # For simplicity, we'll use sync operations here
            db = next(get_db())
            
            activity = AgentActivity(
                agent_name=self.name,
                activity_type=activity_type,
                status=status,
                details=details,
                error_message=error_message,
                execution_time=execution_time
            )
            
            db.add(activity)
            db.commit()
            db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log activity: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the agent.
        
        Returns:
            Dict containing health status
        """
        try:
            # Basic health check - can be overridden by specific agents
            await asyncio.sleep(0.1)  # Simulate some work
            
            return {
                "agent": self.name,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": settings.version
            }
            
        except Exception as e:
            return {
                "agent": self.name,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_agent_info(self) -> Dict[str, str]:
        """Get basic information about the agent.
        
        Returns:
            Dict containing agent information
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "version": settings.version,
            "description": self.__doc__ or "No description available"
        }