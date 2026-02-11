from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
with workflow.unsafe.imports_passed_through():
    from lbprox.temporal.activities import DownloadImageActivity, DownloadImageInput


# Basic workflow that logs and invokes an activity
@workflow.defn
class DownloadImageWorkflow:
    @workflow.run
    async def run(self, image_url: str, version: str) -> str:
        workflow.logger.info("Running workflow with parameters %s, %s" % (image_url, version))
        activities = DownloadImageActivity()
        return await workflow.execute_activity(
            activities.download_image,
            DownloadImageInput(image_url, version),
            start_to_close_timeout=timedelta(seconds=100),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )