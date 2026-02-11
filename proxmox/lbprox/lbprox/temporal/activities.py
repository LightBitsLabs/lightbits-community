from temporalio import activity
from dataclasses import dataclass
from lbprox.common import app_context
from lbprox.common import utils as pve_utils
from lbprox.cli.os_images import cli as os_images


@dataclass
class DownloadImageInput:
    image_url: str
    version: str

class DownloadImageActivity:
    def __init__(self,):
        self.STORAGE_ID = "lb-local-storage"
        self.app_context = app_context.AppContext.create()

    def _get_nodes_names(self):
        if self.app_context.config['nodes']:
            return [node['hostname'] for node in self.app_context.config['nodes']]
        else:
            cluster_nodes = pve_utils.list_cluster_nodes(self.app_context.pve)
            return [node["node"] for node in cluster_nodes]
        
    @activity.defn
    async def download_image(self, input: DownloadImageInput) -> str:

        # Simulate downloading an image from the given URL and version
        # In a real implementation, you would add code to download the image here
        # raise NotImplementedError("Image download logic not implemented.")
        should_create_image = os_images._handle_existing_image(self.app_context.pve, storage_id=self.STORAGE_ID, 
                                         url=input.image_url, desired_nodes=self._get_nodes_names(), force=False)
        if should_create_image:
            os_images._create_os_image(self.app_context.pve, self.app_context.config, storage_id=self.STORAGE_ID, url=input.image_url, 
                                   desired_nodes=self._get_nodes_names())
            return f"Downloaded image from {input.image_url} with version {input.version}"
        
        return f"Image from {input.image_url} with version {input.version} already exists on the cluster."

        
