import yaml
from nomad.config import config

from pydantic import BaseModel, Field


class KubeSpawnerOverride(BaseModel):
    image: str = Field(..., description="Docker image for the profile")
    default_url: str = Field(
        "/lab", description="Default URL to open when the profile is started")


class DockerSpawnerOverride(BaseModel):
    image: str = Field(..., description="Docker image for the profile")
    default_url: str = Field(
        "/lab", description="Default URL to open when the profile is started")


class Profile(BaseModel):
    display_name: str = Field(..., description="Name of the profile")
    default: bool = Field(False, description="Is this the default profile?")
    description: str = Field(..., description="Description of the profile")
    slug: str = Field(..., description="Slug for the profile")
    kubespawner_override: KubeSpawnerOverride = Field(...,
                                                      description="Docker image for the profile")
    dockerspawner_override: DockerSpawnerOverride = Field(...,
                                                          description="Docker image for the profile")


class Jupyterhub(BaseModel):
    nomad: dict = Field(..., description="Configuration for Nomad")
    hub: dict = Field(..., description="Configuration for JupyterHub")
    profile_list: list['Profile'] = Field(
        ..., description="List of profiles available in JupyterHub")


nomad = {
    'api_url': config.api_url(),
    'north_hub_host': config.north.hub_host,
    'north_hub_port': config.north.hub_port,
    'north_docker_network': config.north.docker_network,
    'north_docker_prefix': 'nomad_oasis_north'
}


keycloak_url = f'{config.keycloak.public_server_url.rstrip("/")}/realms/{config.keycloak.realm_name}'
hub = {
    'base_url': f'{config.services.api_base_path.rstrip("/")}/north',
    'allow_named_servers': True,
    'shutdown_on_logout': True,
    'config': {
        'JupyterHub': {
            'authenticator_class': 'generic-oauth'
        },
        'Authenticator': {
            'auto_login': True,
            'enable_auth_state': True,
            'allow_all': True,
            'admin_users': ['test']
        },
        'GenericOAuthenticator': {
            # 'client_id': config.keycloak.client_id,
            # 'client_id': config.keycloak.client_id,
            'oauth_callback_url': f'{config.north_url().rstrip("/")}/hub/oauth_callback',
            'authorize_url': f'{keycloak_url}/protocol/openid-connect/auth',
            'token_url': f'{keycloak_url}/protocol/openid-connect/token',
            'userdata_url': f'{keycloak_url}/protocol/openid-connect/userinfo',
            'login_service': 'keycloak',
            'username_key': 'preferred_username',
            'scope':  ['openid', 'profile'],
            'userdata_params': {
                'state': 'state'
            },
        }
    }
}

profile_list = []
for (name, tool) in config.north.tools.filtered_items():
    profile_list.append(
        Profile(
            display_name=name,
            description=tool.short_description,
            slug=name,
            kubespawner_override=KubeSpawnerOverride(
                image=tool.image,
                default_url=tool.default_url
            ),
            dockerspawner_override=DockerSpawnerOverride(
                image=tool.image,
                default_url=tool.default_url
            )
        )
    )

c = Jupyterhub(nomad=nomad, hub=hub, profile_list=profile_list)

# Writing the data to a YAML file
with open('profile_list_generated.yaml', 'w') as filename:
    yaml.dump(c.model_dump(), filename)

print("Data has been written to 'profile_list_generated.yaml'")


#       01-prespawn-hook.py: |
#         import os
#         import requests
#         import asyncio
#
#         hub_service_api_token = os.getenv('NOMAD_NORTH_HUB_SERVICE_API_TOKEN')
#
#         # configure nomad service
#         c.JupyterHub.services.append(
#             {
#                 "name": "nomad-service",
#                 "admin": True,
#                 "api_token": hub_service_api_token,
#             }
#         )
#
#         async def pre_spawn_hook(spawner):
#             await spawner.load_user_options()
#             username = spawner.user.name
#
#             spawner.log.info(f"username: {username}")
#             spawner.log.debug(f'Configuring spawner for named server {spawner.name}')
#
#             if spawner.handler.current_user.name != 'nomad-service':
#                 # Do nothing, will only launch the default image with no volumes.
#                 return
#
#             user_home = spawner.user_options.get('user_home')
#             spawner.log.info(f"user_home: {user_home}")
#             if user_home:
#                 spawner.volumes.append({
#                     'name': 'user-home',
#                     'hostPath': {'path': user_home['host_path']}
#                 })
#                 spawner.volume_mounts.append({
#                     'name': 'user-home',
#                     'mountPath': user_home['mount_path'],
#                     'readOnly': False
#                 })
#
#             uploads = spawner.user_options.get('uploads', [])
#             spawner.log.info(f"uploads: {uploads}")
#             for (i, upload) in enumerate(uploads):
#                 spawner.volumes.append({
#                     'name': f"uploads-{i}",
#                     'hostPath': {'path': upload['host_path']}
#                 })
#                 spawner.volume_mounts.append({
#                     'name': f"uploads-{i}",
#                     'mountPath': upload['mount_path'],
#                     'readOnly': False
#                 })
#
#             environment = spawner.user_options.get('environment', {})
#             spawner.environment.update(environment)
#
#             tool = spawner.user_options.get('tool')
#             if tool:
#                 spawner.image = tool.get('image')
#                 spawner.cmd = tool.get('cmd')
#
#                 # Workaround to have specific default_url for specific containers without using profiles
#                 if tool.get('default_url'):
#                   spawner.default_url = tool.get('default_url')
#
#                 # Workaround for webtop based images (no connection to jupyterhub itself)
#                 if tool.get('privileged'):
#                     spawner.privileged = True
#                     spawner.allow_privilege_escalation = True
#                     spawner.uid = 0
#
#         c.Spawner.pre_spawn_hook = pre_spawn_hook
#         c.OAuthenticator.allow_all = True

#
#
