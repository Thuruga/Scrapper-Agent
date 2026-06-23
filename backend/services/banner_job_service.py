"""Sequential multi-brand job orchestration for desktop banner extraction."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import contextmanager
from typing import Any, Iterable

from core.banner_models import (
    BannerCandidate,
    BannerRun,
    BannerRunStatus,
    BrandBannerProgress,
    BrandBannerStatus,
)
from core.browser_manager import BrowserManager
from core.job_manager import JOB_CANCEL_FLAGS
from core.websocket import manager
from services.banner_extraction_service import BannerExtractionService, banner_extraction_service
from services.banner_report_service import BannerReportService
from services.banner_storage_service import BannerStorageService, banner_storage_service
from services.brand_service import BrandManagerService, brand_service


@contextmanager
def chromium_session():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=BrowserManager.CHROMIUM_ARGS)
        try:
            yield browser
        finally:
            browser.close()


class BannerJobService:
    def __init__(
        self,
        storage: BannerStorageService = banner_storage_service,
        collector: BannerExtractionService = banner_extraction_service,
        brands: BrandManagerService = brand_service,
        browser_session_factory=chromium_session,
    ):
        self.storage = storage
        self.collector = collector
        self.brands = brands
        self.browser_session_factory = browser_session_factory
        self.reports = BannerReportService(storage)

    def create_job(self, requested_brands: Iterable[str]) -> BannerRun:
        requested = list(dict.fromkeys(key.lower().strip() for key in requested_brands if key.strip()))
        if not requested:
            raise ValueError("select at least one active brand")
        active = {brand.brand_key: brand for brand in self.brands.list_brands(active_only=True)}
        invalid = [key for key in requested if key not in active]
        if invalid:
            raise ValueError(f"inactive or unknown brands: {', '.join(invalid)}")
        run_id = str(uuid.uuid4())
        run = BannerRun(
            run_id=run_id,
            selected_brands=requested,
            brand_progress={
                key: BrandBannerProgress(brand_key=key, brand_name=active[key].brand_name)
                for key in requested
            },
        )
        self.storage.save_run(run)
        JOB_CANCEL_FLAGS[run_id] = asyncio.Event()
        return run

    async def run_job(self, run_id: str) -> BannerRun:
        loop = asyncio.get_running_loop()
        cancel_event = JOB_CANCEL_FLAGS.get(run_id)
        if cancel_event is None:
            raise KeyError(run_id)
        try:
            return await asyncio.to_thread(self._run_sync, run_id, cancel_event, loop)
        finally:
            JOB_CANCEL_FLAGS.pop(run_id, None)

    def _run_sync(self, run_id: str, cancel_event: asyncio.Event, loop: asyncio.AbstractEventLoop) -> BannerRun:
        run = self.storage.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        active = {brand.brand_key: brand for brand in self.brands.list_brands(active_only=True)}

        with self.browser_session_factory() as browser:
            for key in run.selected_brands:
                progress = run.brand_progress[key]
                if cancel_event.is_set():
                    progress.status = BrandBannerStatus.CANCELLED
                    continue
                progress.status = BrandBannerStatus.RUNNING
                self._publish(loop, run, {"kind": "brand", "brand_key": key, "status": progress.status})

                def collector_progress(event: dict) -> None:
                    if event.get("kind") == "banner":
                        candidate = BannerCandidate.model_validate(event["banner"])
                        if all(existing.banner_id != candidate.banner_id for existing in run.banners):
                            run.banners.append(candidate)
                            progress.banner_count = len([b for b in run.banners if b.brand_key == key])
                    self._publish(loop, run, {**event, "brand_key": key})

                try:
                    result = self.collector.extract_brand(
                        browser, active[key], cancel_event=cancel_event,
                        progress_callback=collector_progress,
                    )
                    for banner in result.banners:
                        if all(existing.banner_id != banner.banner_id for existing in run.banners):
                            run.banners.append(banner)
                    run.video_slides.extend(result.videos)
                    progress.banner_count = len([b for b in run.banners if b.brand_key == key])
                    progress.video_count = len(result.videos)
                    progress.screenshot_asset = result.screenshot_asset
                    progress.status = BrandBannerStatus.COMPLETED
                except InterruptedError:
                    progress.status = BrandBannerStatus.CANCELLED
                    cancel_event.set()
                except Exception as exc:  # isolate each retailer failure
                    progress.status = BrandBannerStatus.FAILED
                    progress.error = f"{type(exc).__name__}: {exc}"
                self._publish(loop, run, {
                    "kind": "brand", "brand_key": key, "status": progress.status,
                    "banner_count": progress.banner_count, "error": progress.error,
                })

        if cancel_event.is_set():
            for progress in run.brand_progress.values():
                if progress.status in {BrandBannerStatus.PENDING, BrandBannerStatus.RUNNING}:
                    progress.status = BrandBannerStatus.CANCELLED
            run.status = BannerRunStatus.CANCELLED
        else:
            failed = [p for p in run.brand_progress.values() if p.status == BrandBannerStatus.FAILED]
            if failed:
                run.status = BannerRunStatus.PARTIAL if run.banners else BannerRunStatus.FAILED
            elif not run.banners:
                run.status = BannerRunStatus.FAILED
                run.error = "Nenhum banner foi encontrado nas marcas selecionadas."
            else:
                run.status = BannerRunStatus.REVIEW

        self.storage.save_run(run)
        self.reports.generate(run)
        self._publish(loop, run, {"kind": "terminal", "status": run.status})
        return run

    def stop_job(self, run_id: str) -> bool:
        event = JOB_CANCEL_FLAGS.get(run_id)
        if not event:
            return False
        event.set()
        return True

    def _publish(self, loop: asyncio.AbstractEventLoop, run: BannerRun, event: dict) -> None:
        self.storage.save_run(run)
        payload = {
            "type": "banner_progress",
            "job_id": run.run_id,
            "event": {
                **event,
                "status": str(event["status"].value if hasattr(event.get("status"), "value") else event.get("status")),
            },
            "run": run.model_dump(mode="json"),
        }
        asyncio.run_coroutine_threadsafe(manager.send_message(payload, run.run_id), loop)


banner_job_service = BannerJobService()
