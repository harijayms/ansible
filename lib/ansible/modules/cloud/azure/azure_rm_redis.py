#!/usr/bin/python
#
# Copyright (c) 2016 Matt Davis, <mdavis@ansible.com>
#                    Chris Houseknecht, <house@redhat.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_redis
version_added: "2.4"
short_description: Manage Azure Redis cache.
description:
    - Create, update and delete a Azure Redis cache.
options:
    resource_group_name:
        description:
            - Azure resource group name where the Redis cache will be created.
        required: true
    location:
        description:
            - Azure location for the resource group where . Required when creating a new resource group. Cannot
              be changed once resource group is created.
        required: false
        default: null
    name:
        description:
            - Name of the Redis cache.
        required: true
    sku_name:
        description: 
            - The type of Redis cache to deploy. Valid values: (Basic, Standard, Premium)
        required: true
    sku_family:
        description:
            - The SKU family to use. Valid values: (C, P). (C = Basic/Standard, P = Premium).
        required: true
    sku_capacity:
        description:
            - The size of the Redis cache to deploy. Valid values: for C (Basic/Standard) family (0, 1, 2, 3, 4, 5, 6), for P (Premium) family (1, 2, 3, 4).
        required: true
    redis_configuration:
        description:
            - All Redis Settings. Few possible keys: rdb-backup-enabled,rdb-storage-connection-string,rdb-backup-frequency,maxmemory-delta,maxmemory-policy,notify-keyspace-events,maxmemory-samples,slowlog-log-slower-than,slowlog-max-len,list-max-ziplist-entries,list-max-ziplist-value,hash-max-ziplist-entries,hash-max-ziplist-value,set-max-intset-entries,zset-max-ziplist-entries,zset-max-ziplist-value etc
        required: true    
    enable_nonssl_port:
        description: 
            - Specifies whether the non-ssl Redis server port (6379) is enabled.
        required: false
        default: false
    shard_count:
        description:
            - The number of shards to be created on a Premium Cluster Cache.
        required: true
    subnet_id:
        description:
            - The full resource ID of a subnet in a virtual network to deploy the Redis cache in. Example format: /subscriptions/{subid}/resourceGroups/{resourceGroupName}/Microsoft.{Network|ClassicNetwork}/VirtualNetworks/vnet1/subnets/subnet1
        required: true
    static_ip:
        description:
            - Static IP address. Required when deploying a Redis cache inside an existing Azure Virtual Network.
    tags:
        description:
            - Tags associated with this resource
        required: false
    state:
        description:
            - Assert the state of the resource group. Use 'present' to create or update and
              'absent' to delete. When 'absent' a resource group containing resources will not be removed unless the
              force option is used.
        default: present
        choices:
            - absent
            - present
        required: false

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Hariharan Jayaraman"

'''

EXAMPLES = '''
    - name: Create a new redis cache
      azure_rm_redis:
        resource_group_name: azureredistest
        name: azureredis
        location: westus
        tags:
            testing: testing
            delete: never
        sku_name: Premium
        sku_family: family
        capacity: 1
        enable_nonssl_port: true
        shard_count: 2
        redis_configuration:
            maxmemory-policy: allkeys-lru
        subnet_id: /subscriptions/subid/resourceGroups/rg2/providers/Microsoft.Network/virtualNetworks/network1/subnets/subnet1
        static_ip: 192.168.0.5
    - name: Delete a resource group
      azure_rm_redis:
        resource_group_name: azureredistest
        name: azureredis
        state: absent
'''
RETURN = '''
state:
    description: Current state of the Redis cache.
    returned: always
    type: dict
    sample: {
        "id": "subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Cache/Redis/{name}",
        "location": "westus",
        "name": "azureredis",
        "tags": {
            "delete": "on-exit",
            "testing": "no"
        },
        "properties": {
					"accessKeys": {
						"primaryKey": "secretkey1",
						"secondaryKey": "secretKey2"
					},
		"provisioning_state": "Succeeded",
		"redis_version": "3.0",
		"sku": {
				"name": "Premium",
				"family": "P",
				"capacity": 1
				},
		"enable_nonssl_port": false,
		"redis_configuration": {
				"maxmemory-policy": "allkeys-lru"
		},
		"hostname": "cache1.redis.cache.windows.net",
		"port": 6379,
		"ssl_port": 6380
    }
'''

try:
    from msrestazure.azure_exceptions import CloudError
    from azure.mgmt.resource.resources.models import ResourceGroup
    from ansible.module_utils.azure_rm_common import AzureRMModuleBase
    from azure.mgmt.redis import RedisManagementClient
    from azure.mgmt.redis.models import Sku, RedisCreateParameters
    import time
except ImportError:
    pass


AZURE_EXPECTED_VERSIONS = dict(
    redis_client_version="1.0.0"
)

def azure_redis_dic(redis):
    return dict(
        id=redis.id,
        name=redis.name,
        location=redis.location,
        tags=redis.tags,
        provisioning_state=redis.provisioning_state,
        properties=redis.properties,
        hostname=redis.hostname,
        redis_version=redis.redis_version,
        sku=redis.sku,
        enable_nonssl_port=redis.enable_nonssl_port,
        redis_configuration=redis.redis_configuration,
        port=redis.port,
        ssl_port=redis.ssl_port,

    )


class AzureRMRedisCache(AzureRMModuleBase):

    def __init__(self):
        self.module_arg_spec = dict(
            name=dict(type='str', required=True),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            location=dict(type='str'),
            resource_group_name=dict(type='str',required=True),
            tags=dict(type='dict'),
            sku_name=dict(type='str',required=True, choices=['Basic','Standard','Premium']),
            sku_family=dict(type='str',required=True,choices=['C','P']),
            sku_capacity=dict(type='int',choices=[0,1,2,3,4,5,6]),
            redis_configuration=dict(type='dict',required=True),
            enable_nonssl_port=dict(type='bool',default=False),
            shard_count=dict(type='int',required=True),
            subnet_id=dict(type='str', required=True),
            static_ip=dict(type='str',required=True),

        )

        self.name = None
        self.state = None
        self.location = None
        self.tags = None
        self.resource_group_name = None
        self.sku_name = None
        self.sku_family = None
        self.sku_capacity = None
        self.redis_configuration = None
        self.enable_nonssl_port = None
        self.shard_count = None
        self.subnet_id = None
        self.static_ip = None
        self._redis_client = None
        self.to_update = False
        self.redis_cache = None




        self.results = dict(
            id=None,
            name=None,
            location=None,
            tags=None,
            provisioning_state=None,
            accessKeys=None,
            hostname=None,
            redis_version=None,
            sku=None,
            enable_nonssl_port=None,
            redis_configuration=None,
            port=None,
            ssl_port=None,
            changed=None,
            state=dict(),
        )

        super(AzureRMRedisCache, self).__init__(self.module_arg_spec,
                                                   supports_check_mode=True,
                                                   supports_tags=True)

    def exec_module(self, **kwargs):

        for key in list(self.module_arg_spec.keys()) + ['tags']:
            setattr(self, key, kwargs[key])

        results = dict()
        changed = False
        rg = None
        contains_resources = False
        self._redis_client = None
        
        # Check first if the resource exists 

        self.log('Fetching existing redis cache {0}'.format(self.name))
        try:
            self.redis_cache = self.redis_client.redis.get(self.resource_group_name,self.name)
            self.to_update = True
        except CloudError as exc:
            self.log('Redis cache does not exists its an update operation')

        if self.check_mode :
            # Delete operation
            if self.state == 'absent' and self.to_update:
                self.results['changed'] = True
                self.results['state'] = 'absent'
                return self.results 
            # update operation 
            if self.state == 'present' and self.to_update:
                # update logic 
                self.results['changed'] = True
                self.results['state'] = 'present'
                return self.results
            # create operation 
            else if self.state == 'present':
                self.results['changed'] = changed
                self.results['state'] = 'present'
                self.results['name'] = self.name
                return self.results
                    
        
        # Check if the resource needs to be deleted 
        if self.state == 'absent' and self.to_update == True:
            self.log("CHANGED: redis cache {0} exists but requested state is 'absent'".format(self.name))
            self.log("Will be deleting the resource")
            try:
                poller = self.redis_client.redis.delete(self.resource_group_name,self.name)
                self.get_poller_result(poller)
            except CloudError as exc:
                self.fail('Failed with {}'.format(exc))
            changed = True
            self.results['changed'] = changed
            self.results['state'] = 'absent'
            return self.results 
   
       # do an update of the redis resource 
        if self.state == 'present' and self.to_update == True:
            ## Add logic here to only do the update of the fields
            try:
                self.redis_cache = self.redis_client.redis.create(
                    self.resource_group_name,
                    self.name,
                    RedisCreateParameters(
                    self.location, Sku(self.sku_name,self.sku_family,self.sku_capacity),
                    tags=self.tags, redis_configuration=None, 
                    enable_non_ssl_port=None, tenant_settings=None,
                    shard_count=None, subnet_id=None, static_ip=None
                    )
                ).result()
                
                self.log(self.redis_cache)
            except CloudError as exc:
                self.fail('Failed with {}'.format(exc))
            self.log('Successfuly updated the Redis cache')
            self.log('getting the updated cache resource')
            
            self.results['changed'] = True
            self.results['state'] = 'present'
            self.populate_results()
            return self.results

        # Create the resource 
        try:
            self.redis_cache = self.redis_client.redis.create(
                self.resource_group_name,
                self.name,
                RedisCreateParameters(
                self.location, Sku(self.sku_name,self.sku_family,self.sku_capacity),
                tags=self.tags, redis_configuration=None, 
                enable_non_ssl_port=None, tenant_settings=None,
                shard_count=None, subnet_id=None, static_ip=None
                )
            ).result()
            # wait for the resource to get to running state
            if self.check_resource_created() == False:
                self.populate_results()
                self.fail('Waited too long, resource might be created')
            self.log(self.redis_cache)
        
        except CloudError as exc:
            self.fail('Failed with {}'.format(exc))
        self.results['changed'] = True
        self.results['state'] = 'present'
        self.populate_results()
        return self.results
        

    @property
    def redis_client(self):
        self.log('Getting redis client')
        if not self._redis_client:
            self._redis_client = RedisManagementClient(
            self.azure_credentials,
            self.subscription_id
            )   
        self._register('Microsoft.Cache')
        return self._redis_client

    def populate_results(self):
        self.results['id']= self.redis_cache.id
        self.results['name'] = self.redis_cache.name
        self.results['location'] = self.redis_cache.location
        self.results['tags'] = self.redis_cache.tags
        self.results['provisioning_state'] = self.redis_cache.provisioning_state
        #self.results.properties = self.redis_cache.properties
        self.results['hostname'] = self.redis_cache.host_name
        self.results['redis_version'] = self.redis_cache.redis_version
        self.results['sku'] = self.redis_cache.sku
        self.results['enable_nonssl_port'] = self.redis_cache.ssl_port
        self.results['accessKeys']=self.redis_cache.access_keys
        
        return 
    def check_resource_created(self):
        try:
            delay = 10
            count = 0
            
            while not self.redis_cache.provisioning_state=='Succeeded':
                self.log("Waiting for {0} sec".format(delay))
                time.sleep(delay) 
                count= count + 1
                self.redis_cache = self.redis_client.redis.get(self.resource_group_name,self.name)
                if count == 180:
                    self.log("Waited for 30 min, this sucks, bailing out")
                    return False

            return True
        except Exception as exc:
            self.log(str(exc))
            raise

def main():
    AzureRMRedisCache()

if __name__ == '__main__':
    main()
