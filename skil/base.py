import skil_client
from skil_client.rest import ApiException as api_exception

import pprint
import os
import time
import requests
import json
import subprocess
from .config import SKIL_CONFIG, save_skil_config


class Skil:
    def __init__(self, workspace_server_id=None, host='localhost', port=9008,
                 debug=False, user_id='admin', password='admin'):

        self.printer = pprint.PrettyPrinter(indent=4)

        config = skil_client.Configuration()
        config.host = "{}:{}".format(host, port)
        config.debug = debug
        self.config = config
        self.uploads = []
        self.uploaded_model_names = []
        self.auth_headers = None

        self.api_client = skil_client.ApiClient(configuration=config)
        self.api = skil_client.DefaultApi(api_client=self.api_client)

        try:
            self.printer.pprint('>>> Authenticating SKIL...')
            credentials = skil_client.Credentials(
                user_id=user_id, password=password)
            token = self.api.login(credentials)
            self.token = token.token
            config.api_key['authorization'] = self.token
            config.api_key_prefix['authorization'] = "Bearer"
            self.printer.pprint('>>> Done!')
        except api_exception as e:
            raise Exception(
                "Exception when calling DefaultApi->login: {}\n".format(e))

        if workspace_server_id:
            self.server_id = workspace_server_id
        else:
            self.server_id = self.get_default_server_id()

        # Store config for future connections
        base_config = {
            'host': host,
            'port': port,
            'username': user_id,
            'password': password
        }
        save_skil_config(base_config)

    @classmethod
    def from_config(cls):
        return Skil(**SKIL_CONFIG)

    def get_default_server_id(self):
        self.auth_headers = {'Authorization': 'Bearer %s' % self.token}
        r = requests.get(
            'http://{}/services'.format(self.config.host), headers=self.auth_headers)
        if r.status_code != 200:
            r.raise_for_status()

        content = json.loads(r.content.decode('utf-8'))
        services = content.get('serviceInfoList')
        server_id = None
        for s in services:
            if 'Model History' in s.get('name'):
                server_id = s.get('id')
        if server_id:
            return server_id
        else:
            raise Exception(
                "Could not detect default model history server instance. Is SKIL running?")

    def upload_model(self, model_name):
        self.printer.pprint('>>> Uploading model, this might take a while...')
        upload = self.api.upload(file=model_name).file_upload_response_list
        self.uploads = self.uploads + upload
        self.uploaded_model_names.append(model_name)
        self.printer.pprint(self.uploads)

    def get_uploaded_model_names(self):
        return self.uploaded_model_names

    def get_model_path(self, model_name):
        for upload in self.uploads:
            if model_name == upload.file_name:
                return "file://" + upload.path
        raise Exception("Model resource not found, did you upload it? ")

    def get_all_compute_resources(self):
        return self.api.get_resource_by_type(resource_type="COMPUTE")

    def get_all_data_resources(self):
        return self.api.get_resource_by_type(resource_type="STORAGE")

    def get_all_resources(self):
        return self.api.get_resources()

    def get_resource_by_id(self, resource_id):
        return self.api.get_resource_by_id(resource_id=resource_id)

    def get_resource_details_by_id(self, resource_id):
        return self.api.get_resource_details_by_id(resource_id=resource_id)

    def get_resource_by_type(self, resource_type):
        """            
        - EMR                   # AWS Elastic Map Reduce(Compute)
        - S3                    # AWS Simple Storage Service
        - GoogleStorage         # Google Cloud Storage
        - DataProc              # Google Big Data Compute Engine
        - HDInsight             # Azure Compute
        - AzureStorage          # Azure Blob Storage
        - HDFS                  # in house Hadoop (Storage)
        - YARN                  # in house YARN (Compute)
        """
        return self.api.get_resource_by_sub_type(resource_sub_type=resource_type)

    # TODO: cover resource groups. add, delete etc.
    # TODO: add & remove credentials
