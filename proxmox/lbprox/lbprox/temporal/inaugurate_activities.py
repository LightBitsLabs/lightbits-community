from temporalio import activity
from dataclasses import dataclass
from lbprox.common import app_context
from lbprox.common import utils as pve_utils
from lbprox.cli.allocations import cli as allocations_cli


@dataclass
class InaugurateInput:
    storage_id: str
    start_vm: bool
    tags: list[str]
    wait_for_ip: bool
    allocation_descriptor_name: str

class InaugurateActivity:
    def __init__(self):
        self.STORAGE_ID = "lb-local-storage"
        self.app_context = app_context.AppContext.create()

    def _get_nodes_names(self):
        if self.app_context.config['nodes']:
            return [node['hostname'] for node in self.app_context.config['nodes']]
        else:
            cluster_nodes = pve_utils.list_cluster_nodes(self.app_context.pve)
            return [node["node"] for node in cluster_nodes]
        
    @activity.defn
    async def inaugurate(self, input: InaugurateInput) -> str:
       username = self.app_context.config['username']
       password = self.app_context.config['password']
       allocations_cli._create_vms(self.app_context.pve, self._get_nodes_names()[0],
                                   storage_id=input.storage_id, start_vm=input.start_vm, tags=input.tags,
                                   wait_for_ip=input.wait_for_ip, ssh_username=username,
                                   ssh_password=password,
                                   allocation_descriptor_name=input.allocation_descriptor_name)
       
       return f"Inauguration completed with storage {input.storage_id} and allocation descriptor {input.allocation_descriptor_name}."
        
