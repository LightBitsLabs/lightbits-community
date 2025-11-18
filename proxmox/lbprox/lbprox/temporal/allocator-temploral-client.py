import asyncio
from temporalio.client import Client
from temporalio.service import TLSConfig
import uuid
from lbprox.temporal.inaugurate_activities import InaugurateInput

interrupt_event = asyncio.Event()

async def main():

    cets_dir = "/tmp/temporal-certs/etc/certs"
    server_root_ca_cert = f"{cets_dir}/ca.cert"
    client_cert = f"{cets_dir}/client.pem"
    client_key = f"{cets_dir}/client.key"
    temporal_ip = "allocator-temporal:7233"

    with open(server_root_ca_cert, "rb") as f:
            server_root_ca_cert = f.read()
    with open(client_cert, "rb") as f:
            client_cert = f.read()
    with open(client_key, "rb") as f:
            client_key = f.read()
    
    client = await Client.connect(
        temporal_ip,
        namespace="default",
        tls=TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        ),
    )


    # result = await client.execute_workflow(
    #     "DownloadImageWorkflow",
    #     # Wrap your two parameters in a list and pass them to 'args'
    #     args=["https://pulp04.kube02.lab.lightbitslabs.com/pulp/content/rocky-9-target/qcow2/latest/rocky-9-target.qcow2", "v1.0"], 
    #     id=str(uuid.uuid4()),
    #     task_queue="download-image-worker",  
    # )
    # print(f"Result: {result}")
    # return
    input = InaugurateInput(
        storage_id="lb-local-storage",
        start_vm=True,
        wait_for_ip=True,
        tags=["tag1", "tag2"],
        allocation_descriptor_name="dms"
    )
    result = await client.execute_workflow(
        "InaugurateWorkflow",
        # Wrap your two parameters in a list and pass them to 'args'
        args=[input],
        id=str(uuid.uuid4()),
        task_queue="inaugurate-worker",  
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())