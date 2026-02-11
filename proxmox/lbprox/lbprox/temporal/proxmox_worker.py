import asyncio
import click
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.service import TLSConfig
from lbprox.temporal.workflow_download_image import DownloadImageWorkflow
from lbprox.temporal.workflow_inaugurate import InaugurateWorkflow
from lbprox.temporal.activities import DownloadImageActivity
from lbprox.temporal.inaugurate_activities import InaugurateActivity

interrupt_event = asyncio.Event()

async def create_client(temporal_config):
    """Create and return a Temporal client with TLS configuration."""
    with open(temporal_config.ca_cert, "rb") as f:
        server_root_ca_cert = f.read()
    with open(temporal_config.client_pem, "rb") as f:
        client_cert = f.read()
    with open(temporal_config.client_key, "rb") as f:
        client_key = f.read()

    return await Client.connect(
        temporal_config.endpoint,
        namespace="default",
        tls=TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        ),
    )

async def run_download_image_worker(client, task_queue):
    """Run worker for DownloadImageWorkflow."""
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[DownloadImageWorkflow],
        activities=[DownloadImageActivity().download_image],
    ):
        print(f"DownloadImage worker started for task queue '{task_queue}'")
        await interrupt_event.wait()

async def run_inaugurate_worker(client, task_queue):
    """Run worker for InaugurateWorkflow."""
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[InaugurateWorkflow],
        activities=[InaugurateActivity().inaugurate],
    ):
        print(f"Inaugurate worker started for task queue '{task_queue}'")
        await interrupt_event.wait()

async def main(ctx):
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    client = await create_client(ctx.obj.temporal_config)

    # Run both workers concurrently
    await asyncio.gather(
        run_download_image_worker(client, "download-image-worker"),
        run_inaugurate_worker(client, "inaugurate-worker"),
    )



@click.group("temporal")
def temporal_group():
    pass

@temporal_group.command("serve", help="runs temporal worker server")
@click.pass_context
def serve_temporal_worker(ctx):
    asyncio.run(main(ctx))
    

if __name__ == "__main__":
    asyncio.run(main())