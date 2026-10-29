from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
with workflow.unsafe.imports_passed_through():
    from lbprox.temporal.inaugurate_activities import InaugurateActivity, InaugurateInput


# Basic workflow that logs and invokes an activity
@workflow.defn
class InaugurateWorkflow:
    @workflow.run
    async def run(self, input: InaugurateInput) -> str:
        workflow.logger.info("Running workflow with parameters %s, %s" % (input.storage_id, input.allocation_descriptor_name))
        activities = InaugurateActivity()
        return await workflow.execute_activity(
            activities.inaugurate,
            input,
            start_to_close_timeout=timedelta(seconds=100),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )