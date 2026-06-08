"""eval-studio Python SDK."""

from eval_studio.async_client import AsyncEvalStudioClient
from eval_studio.client import EvalStudioClient
from eval_studio.config import EvalStudioConfig, load_config, save_config
from eval_studio.exceptions import (
    AuthenticationError,
    ConnectionError,
    EvalStudioError,
    EvalStudioTimeoutError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from eval_studio.models import (
    ApiKey,
    ApiKeyWithSecret,
    Dataset,
    DatasetList,
    Evaluation,
    EvaluationList,
    HealthStatus,
    Result,
    ResultList,
    RunAsyncResult,
    RunResult,
)

__version__ = "0.1.0"

__all__ = [
    "ApiKey",
    "ApiKeyWithSecret",
    "AsyncEvalStudioClient",
    "AuthenticationError",
    "ConnectionError",
    "Dataset",
    "DatasetList",
    "EvalStudioClient",
    "EvalStudioConfig",
    "EvalStudioError",
    "EvalStudioTimeoutError",
    "Evaluation",
    "EvaluationList",
    "ForbiddenError",
    "HealthStatus",
    "NotFoundError",
    "Result",
    "ResultList",
    "RunAsyncResult",
    "RunResult",
    "ServerError",
    "ValidationError",
    "load_config",
    "save_config",
]
