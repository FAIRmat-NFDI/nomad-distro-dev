#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from enum import Enum
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from mongoengine.queryset.visitor import Q
from pydantic import BaseModel

from nomad.app.v1.routers.auth import generate_simple_token
from nomad.config import config
from nomad.config.models.north import NORTHTool
from nomad.groups import MongoUserGroup
from nomad.processing import Upload
from nomad.utils import get_logger, slugify

from ..models import HTTPExceptionModel, User
from .auth import P


class ToolStateEnum(str, Enum):
    running = 'running'
    starting = 'starting'
    stopping = 'stopping'
    stopped = 'stopped'


class ToolModel(NORTHTool):
    name: str
    state: ToolStateEnum | None = None


class ToolResponseModel(BaseModel):
    tool: str
    username: str
    upload_mount_dir: str | None = None
    data: ToolModel
    upload_id_is_mounted: bool | None = None


class ToolsResponseModel(BaseModel):
    data: list[ToolModel] = []


class ReadMode(str, Enum):
    ro = 'ro'
    rw = 'rw'

# TODO: separate what and how to mount


class Kind(str, Enum):
    """Type of the mount. Different spawners may support different types of mounts.
    - bind: in case of Dockerspawner this equaivalent to bind mounts. In case of KubeSpawner this equivalent to hostpath mounts.
    - volume: reusae or create a new volume.
    """
    bind = 'bind'
    volume = 'volume'


class Mount(BaseModel):
    source: str
    target: str
    kind: Kind = Kind.bind
    mode: ReadMode = ReadMode.ro


class Mounts(BaseModel):
    mounts: list[Mount] = []


TOOLS = {k: v for k, v in config.north.tools.filtered_items()}


async def tool(name: str) -> ToolModel:
    if name not in TOOLS:
        raise HTTPException(
            status_code=404, detail='The tools does not exist.'
        )

    tool = TOOLS[name]
    return ToolModel(name=name, **tool.dict())

UserDep = Annotated[User, Depends(create_user_dependency(required=True))]
ToolDep = Annotated[ToolModel, Depends(tool)]


# TODO: replace with OAuth2PasswordBearer (using a user token instead of the service token)
hub_api_headers = {
    'Authorization': f'Bearer {config.north.hub_service_api_token}'
}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
OAuthDep = Annotated[str, Depends(oauth2_scheme)]

logger = get_logger(__name__)

router = APIRouter()


def _get_status(tool: ToolModel, user: User) -> ToolModel:
    # TODO: we should not do this
    if not user:
        return tool

    url = f'{config.hub_url()}/api/users/{user.username}/servers/{tool.name}/progress'
    try:
        response = requests.get(url, headers=hub_api_headers)
    except requests.ConnectionError as e:
        raise HTTPException(
            status_code=404, detail='Hub is not reachable. Please try again later.'
        )

    if response.status_code == 404:
        # The user or the tool does not yet exist
        tool.state = ToolStateEnum.stopped
    elif response.status_code == 200:
        if '"ready": true' in response.text:
            tool.state = ToolStateEnum.running
        else:
            tool.state = ToolStateEnum.starting
    else:
        logger.error(
            'unexpected jupyterhub response',
            data=dict(status_code=response.status_code),
            text=response.text,
        )
        tool.state = ToolStateEnum.stopped

    return tool


@router.get(
    '/',
    response_model=ToolsResponseModel,
    summary='Get a list of all configured tools and their current state.',
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
)
async def get_tools(user: UserDep):

    logger.info('get tools', user=user)

    return ToolsResponseModel(
        data=[
            _get_status(ToolModel(name=name, **tool.dict()), user)
            for name, tool in TOOLS.items()
        ]
    )


@router.get(
    '/{name}',
    summary='Get information for a specific tool.',
    response_model=ToolResponseModel,
    responses={
        401: {'model': HTTPExceptionModel, 'description': 'Authorization error.'},
        404: {'model': HTTPExceptionModel, 'description': "The tool does not exist."}
    },
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
)
async def get_tool(
    tool: ToolDep,
    user: UserDep,
    upload_id: str | None = None,
):
    if not config.north.enable_new_hub_api:
        status = _get_status(tool, user)

        if upload_id:
            url = f'{config.hub_url()}/api/users/{user.username}'
            response = requests.get(url, headers=hub_api_headers)
            upload_id_is_mounted = _check_uploadid_is_mounted(
                tool, response.json(), upload_id)
        else:
            upload_id_is_mounted = None

        return ToolResponseModel(
            tool=tool.name,
            username=user.username,
            data=status,
            upload_id_is_mounted=upload_id_is_mounted
        )


def _check_uploadid_is_mounted(
    tool: ToolModel, response: dict, upload_id: str
) -> bool | None:
    try:
        servers = response.get('servers', {})
        tool_data = servers.get(tool.name, {})
        if not tool_data:
            return None
        user_options = tool_data.get('user_options', {})
        uploads = user_options.get('uploads', [])
        for upload in uploads:
            host_path = upload.get('host_path', '')
            if upload_id in host_path:
                return True
        return False
    except Exception:
        return None


@router.post(
    '/{name}',
    # response_model=ToolResponseModel,
    summary='Start a tool.',
    responses={
        401: {'model': HTTPExceptionModel, 'description': 'Authorization error.'},
        404: {'model': HTTPExceptionModel, 'description': "The tool does not exist."}
    },
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
)
async def start_tool(
    tool: ToolDep,
    user: UserDep,
    upload_id: str | None = None,
    path: str | None = None,
):
    if not config.north.enable_new_hub_api:

        tool.state = ToolStateEnum.stopped

        # Make sure the user exists
        url = f'{config.hub_url()}/api/users/{user.username}'
        response = requests.get(url, headers=hub_api_headers)
        if response.status_code == 404:
            response = requests.post(url, headers=hub_api_headers)
            if response.status_code == 200:
                logger.info('created north user', user_id=user.user_id)
            else:
                # TODO
                logger.error('could not create north user',
                             user_id=user.user_id)

        if user.username in config.fs.north_home_user_folder_map.keys():
            user_home_folder = config.fs.north_home_user_folder_map[user.username]
        else:
            user_home_folder = user.user_id
            # Make sure that the home folder of the user exists
            user_home = os.path.join(config.fs.north_home, user_home_folder)
            if not os.path.exists(user_home):
                os.makedirs(user_home)

        def truncate(path_name):
            # On Linux: The maximum length for a file name is 255 bytes
            return path_name[:230]

        upload_mount_dir = None
        user_id = str(user.user_id)
        group_ids = MongoUserGroup.get_ids_by_user_id(
            user_id, include_all=False)

        upload_query = Q()
        upload_query &= (
            Q(main_author=user_id) | Q(coauthors=user_id) | Q(
                coauthor_groups__in=group_ids)
        )
        upload_query &= Q(publish_time=None)

        uploads: list[dict] = []
        for upload in Upload.objects.filter(upload_query):
            if not hasattr(upload.upload_files, 'external_os_path'):
                # In case the files are missing for one reason or another
                logger.info(
                    'upload: the external path is missing for one reason or another'
                )
                continue

            if upload.upload_name:
                upload_dir = (
                    f'uploads/{truncate(slugify(upload.upload_name))}-{upload.upload_id}'
                )
            else:
                upload_dir = f'uploads/{upload.upload_id}'

            if upload.upload_id == upload_id:
                upload_mount_dir = upload_dir

            uploads.append(
                {
                    'host_path': os.path.join(upload.upload_files.external_os_path, 'raw'),
                    'mount_path': os.path.join(tool.mount_path, upload_dir),
                }
            )

        external_mounts: list[dict[str, str]] = []
        for ext_mount in tool.external_mounts:
            external_mounts.append(
                {
                    'host_path': ext_mount.host_path,
                    'bind': os.path.join(tool.mount_path, ext_mount.bind),
                    'mode': ext_mount.mode,
                }
            )

        # Check if the tool/named server already exists
        _get_status(tool, user)
        if tool.state != ToolStateEnum.stopped:

            if upload_id and response.json().get('servers', None):
                upload_id_is_mounted = _check_uploadid_is_mounted(
                    tool, response.json(), upload_id
                )
            else:
                upload_id_is_mounted = None

            return ToolResponseModel(
                tool=tool.name,
                username=user.username,
                data=_get_status(tool, user),
                upload_mount_dir=upload_mount_dir,
                upload_id_is_mounted=upload_id_is_mounted
            )

        url = f'{config.hub_url()}/api/users/{user.username}/servers/{tool.name}'
        access_token = generate_simple_token(
            user_id=user.user_id, expires_in=config.north.nomad_access_token_expiry_time
        )
        body = {
            'tool': {
                'image': tool.image,
                'cmd': tool.cmd,
                'privileged': tool.privileged,
                'default_url': tool.default_url,
            },
            'environment': {
                'SUBFOLDER': f'{config.services.api_base_path.rstrip("/")}/north/user/{user.username}/',
                'JUPYTERHUB_CLIENT_API_URL': f'{config.north_url()}/hub/api',
                'NOMAD_CLIENT_USER': user.username,
                'NOMAD_CLIENT_ACCESS_TOKEN': access_token,
                'NOMAD_CLIENT_URL': config.api_url(ssl=config.services.https_upload),
                'NOMAD_oasis_uses_central_user_management': str(
                    config.oasis.uses_central_user_management
                ),
            },
            'user_home': {
                'host_path': os.path.join(config.fs.north_home_external, user_home_folder),
                'mount_path': os.path.join(tool.mount_path, 'work'),
            },
            'uploads': uploads,
            'external_mounts': external_mounts,
        }

        logger.info('post tool start to jupyterhub', body=body)

        response = requests.post(url, json=body, headers=hub_api_headers)

        if (
            response.status_code == 400
            and 'is already running' in response.json()['message']
        ):
            tool.state = ToolStateEnum.running
        elif response.status_code == 201:
            tool.state = ToolStateEnum.running
        elif response.status_code == 202:
            tool.state = ToolStateEnum.starting
        else:
            logger.error(
                'unexpected jupyterhub response',
                data=dict(status_code=response.status_code),
                text=response.text,
            )
            tool.state = ToolStateEnum.stopped

        return ToolResponseModel(
            tool=tool.name,
            username=user.username,
            data=_get_status(tool, user),
            upload_mount_dir=upload_mount_dir,
        )

    url = f'{config.hub_url()}/user-redirect/{tool.name}/tree/path/to upload'
    return RedirectResponse(url)



@router.delete(
    '/{name}',
    response_model=ToolResponseModel,
    summary='Stop a tool.',
    responses={
        401: {'model': HTTPExceptionModel, 'description': 'Authorization error.'},
        404: {'model': HTTPExceptionModel, 'description': "The tool does not exist."}
    },
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
)
async def stop_tool(
    tool: ToolDep,
    user: UserDep,
):
    if not config.north.enable_new_hub_api:
        url = f'{config.hub_url()}/api/users/{user.username}/servers/{tool.name}'
        response = requests.delete(
            url, json={'remove': True}, headers=hub_api_headers)

        if response.status_code == 404:
            tool.state = ToolStateEnum.stopped
        elif response.status_code == 204:
            tool.state = ToolStateEnum.stopped
        elif response.status_code == 202:
            tool.state = ToolStateEnum.stopping
        else:
            logger.error(
                'unexpected jupyterhub response',
                data=dict(status_code=response.status_code),
                text=response.text,
            )
            tool.state = ToolStateEnum.stopped

        return ToolResponseModel(
            tool=tool.name, username=user.username, data=_get_status(
                tool, user)
        )


def get_upload_dir(upload: Upload):
    # On Linux: The maximum length for a file name is 255 bytes
    if upload.upload_name:
        return f'uploads/{slugify(upload.upload_name)[:230]}-{upload.upload_id}'
    return f'uploads/{upload.upload_id}'


@router.get(
    '/mounts/{name}',
    response_model=Mounts,
    summary='Get all the  mounts for a specific user and a tool.',
    responses={
        401: {'model': HTTPExceptionModel, 'description': 'Authorization error.'},
        404: {'model': HTTPExceptionModel, 'description': "The tool does not exist."}
    },
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
)
async def get_mounts(
    tool: ToolDep,
    user: UserDep,
):
    """Get all the mounts for a specific user and a tool.
    There are 3 different kind of mounts:
    - uploads,
    - user specific "work" directories?,
    - tool specific "external" directories?
    """
    mounts: list[Mount] = []

    if user.username in config.fs.north_home_user_folder_map.keys():
        user_home = config.fs.north_home_user_folder_map[user.username]
    else:
        user_home = user.user_id

    # Make sure that the home folder of the user exists
    # user_home_dir = os.path.join(config.fs.north_home, user_home)
    # if not os.path.exists(user_home_dir):
    #     os.makedirs(user_home_dir)

    mounts.append(
        Mount(
            source=os.path.join(config.fs.north_home_external, user_home),
            target=os.path.join(tool.mount_path, 'work'),
            mode=ReadMode.rw
        )
    )

    user_id = str(user.user_id)
    group_ids = MongoUserGroup.get_ids_by_user_id(user_id, include_all=False)

    upload_query = (
        (
            Q(main_author=user_id) |
            Q(coauthors=user_id) |
            Q(coauthor_groups__in=group_ids)
        ) &
        Q(publish_time=None)
    )

    for upload in Upload.objects.filter(upload_query):
        mounts.append(
            Mount(
                source=os.path.join(
                    upload.upload_files.external_os_path, 'raw'),
                target=os.path.join(tool.mount_path, get_upload_dir(upload)),
                mode=ReadMode.rw,
            )
        )

    for ext_mount in tool.external_mounts:
        mounts.append(
            Mount(
                source=ext_mount.host_path,
                target=os.path.join(tool.mount_path, ext_mount.bind),
                mode=ReadMode(ext_mount.mode),
            )
        )

    return Mounts(mounts=mounts)
