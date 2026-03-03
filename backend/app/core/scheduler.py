import logging
import os
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.training_service import run_night_training

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def train_night_model_job() -> None:
    """
    매일 새벽 실행되는 Night Model 학습 작업입니다.
    
    * **수행 작업**:
      - Night Model 재학습 (사용자 및 아이템 임베딩 업데이트)
      - 학습 결과로 DB의 `night_v1` 데이터 갱신
      - `day_v1` 데이터를 `night_v1` 값으로 초기화
    """
    logger.info("[Scheduler] Starting Night Model Training Job...")
    
    try:
        run_night_training()
        logger.info("[Scheduler] Night Model Training Job Completed Successfully.")
    except Exception as e:
        logger.error(f"[Scheduler] Night Model Training Job Failed: {e}")


def start_scheduler() -> None:
    """
    스케줄러를 시작합니다.
    (매일 새벽 3시에 `train_night_model_job` 작업 예약)
    """
    if not scheduler.running:
        trigger = CronTrigger(hour=3, minute=0)
    
        scheduler.add_job(
            train_night_model_job,
            trigger=trigger,
            id="train_night_model",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("[Scheduler] Background Scheduler Started. Night Training scheduled at 03:00 AM.")


def shutdown_scheduler() -> None:
    """스케줄러를 종료합니다."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Background Scheduler Shutdown.")
