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


class JupyterhubConfig(BaseModel):
    profile_list: list['Profile'] = Field(
        ..., description="List of profiles available in JupyterHub")


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

c = JupyterhubConfig(profile_list=profile_list)

# Writing the data to a YAML file
with open('profile_list_generated.yaml', 'w') as filename:
    yaml.dump(c.model_dump(), filename)

print("Data has been written to 'profile_list_generated.yaml'")
