import os
import ssl
import requests
from requests.adapters import HTTPAdapter
from requests_toolbelt.multipart.encoder import MultipartEncoder


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2  # Enforcing TLSv1.2 or higher
        context.check_hostname = False  # Disable hostname checking
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


class ProxmoxClient:
    def __init__(self, node_name, base_url, username, password, verify_ssl=True):
        self.node_name = node_name
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.headers = self._get_auth_headers(username, password)
        self.sess = requests.Session()
        self.sess.mount('https://', TLSAdapter())

    def _get_auth_headers(self, username, password):
        """
        Authenticates with Proxmox and returns the headers with the PVEAPIToken.
        """

        url = f"{self.base_url}/access/ticket"
        data = {"username": f"{username}@pam", "password": password}

        try:
            # response = self.sess.post(url, data=data, verify=self.verify_ssl)
            response = requests.post(url, data=data, verify=self.verify_ssl)
            response.raise_for_status()

            ticket_data = response.json()
            api_token = f"PVEAPIToken={ticket_data['data']['ticket']}"
            csrf_prevention_token = ticket_data['data']['CSRFPreventionToken']
            return {
                "Authorization": api_token,
                "CSRFPreventionToken": csrf_prevention_token,
            }

        except requests.exceptions.RequestException as e:
            print(f"Error authenticating with Proxmox: {e}")
            # Handle the error appropriately (e.g., raise an exception or exit)
            return {}  # Return empty headers on error

    def upload(self, node, storage, file_path):
        """
        Uploads a file to the Proxmox node's storage.

        Args:
            node (str): The name of the Proxmox node.
            storage (str): The storage ID on the Proxmox node.
            content_type (str): The content type of the file (e.g., "iso").
            file_path (str): The path to the file to be uploaded.
                      The filename will be extracted from this path.
        """

        filename = os.path.basename(file_path) # Extract filename from the file path
        url = f"{self.base_url}/nodes/{node}/storage/{storage}/upload"

        with open(file_path, 'rb') as file_data:
            # files = {'filename': (filename, file_data, 'text/plain')}
            # data = {'content': content_type}

            # ref: https://github.com/proxmoxer/proxmoxer/issues/116
            mp_encoder = MultipartEncoder(
                    fields={
                        'content' : "iso",
                        'filename'    : (filename, file_data, 'text/plain'),
                    }
                )
            cookies = {
                'PVEAuthCookie': self.headers["Authorization"].split("=")[1],
            }
            headers = {
                "CSRFPreventionToken": self.headers["CSRFPreventionToken"],
                'Content-Type': mp_encoder.content_type,
            }
            try:
                response = self.sess.post(
                    url,
                    data=mp_encoder,
                    cookies=cookies,
                    headers=headers,
                    verify=self.verify_ssl
                )
                response.raise_for_status()  # Raise an exception for bad status codes

                # Handle the response and check for task completion if needed
                # (similar to WaitForCompletion in the Go code)
                task_response = response.json()
                print(f'uploaded image {url} to node {self.node_name} with id {task_response}')
                # ... (process task_response) ...

            except requests.exceptions.RequestException as e:
                raise Exception(f"error uploading file: {e}")
                # Handle the error appropriately
