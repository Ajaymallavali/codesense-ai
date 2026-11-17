import json
import uuid
from unittest.mock import MagicMock, patch
import pytest

from app.jobs import (
    REDIS_QUEUE_KEY,
    REDIS_CACHE_PREFIX,
    check_redis_health,
    dispatch_analysis_job,
    get_redis_client,
    cache_latest_analysis,
    get_cached_latest_analysis,
    invalidate_analysis_cache,
)


def test_redis_health_fallback_behavior():
    with patch("app.jobs.get_redis_client", return_value=None):
        health = check_redis_health()
        assert health["status"] == "STANDALONE_FALLBACK"
        assert "background tasks" in health["detail"]


def test_redis_dispatch_no_duplicate_execution():
    """When Redis is online, job is enqueued to Redis and NOT scheduled via BackgroundTasks."""
    mock_redis = MagicMock()
    mock_bg = MagicMock()
    analysis_id = uuid.uuid4()

    with patch("app.jobs.get_redis_client", return_value=mock_redis):
        dispatch_analysis_job(analysis_id, mock_bg)

        # Enqueued to Redis
        assert mock_redis.lpush.call_count == 1
        args, _ = mock_redis.lpush.call_args
        assert args[0] == REDIS_QUEUE_KEY
        payload = json.loads(args[1])
        assert payload["analysis_id"] == str(analysis_id)

        # Background task was NOT added (prevents duplicate execution)
        assert mock_bg.add_task.call_count == 0


def test_redis_dispatch_offline_fallback_to_background_tasks():
    """When Redis is offline, job is scheduled via BackgroundTasks."""
    mock_bg = MagicMock()
    analysis_id = uuid.uuid4()

    with patch("app.jobs.get_redis_client", return_value=None):
        dispatch_analysis_job(analysis_id, mock_bg)

        # Background task WAS added as fallback
        assert mock_bg.add_task.call_count == 1
        args, _ = mock_bg.add_task.call_args
        assert args[1] == analysis_id


def test_redis_analysis_caching_and_invalidation():
    mock_redis = MagicMock()
    repo_id = str(uuid.uuid4())
    sample_data = {"repositoryId": repo_id, "maintainabilityScore": 92}

    with patch("app.jobs.get_redis_client", return_value=mock_redis):
        # Cache set
        cache_latest_analysis(repo_id, sample_data, ttl_seconds=1800)
        assert mock_redis.set.call_count == 1
        set_args, set_kwargs = mock_redis.set.call_args
        assert set_args[0] == f"{REDIS_CACHE_PREFIX}{repo_id}"
        assert json.loads(set_args[1]) == sample_data
        assert set_kwargs.get("ex") == 1800

        # Cache get
        mock_redis.get.return_value = json.dumps(sample_data)
        cached = get_cached_latest_analysis(repo_id)
        assert cached == sample_data

        # Cache invalidation
        invalidate_analysis_cache(repo_id)
        assert mock_redis.delete.call_count == 1
        del_args, _ = mock_redis.delete.call_args
        assert del_args[0] == f"{REDIS_CACHE_PREFIX}{repo_id}"
