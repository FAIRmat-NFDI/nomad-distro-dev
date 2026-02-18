
docker exec -it jupyterhub bash




sudo chown vscode:vscode jupyterhub_config.py

docker run --rm -v ./config/jupyterhub_config.py:/srv/jupyterhub/jupyterhub_config.py -d -p 8000:8000 --name jupyterhub quay.io/jupyterhub/jupyterhub jupyterhub
# docker run --rm -v ./config/:/etc/jupyterhub/ -d -p 8000:8000 --name jupyterhub quay.io/jupyterhub/jupyterhub jupyterhub
docker exec -it jupyterhub bash
cd /etc/jupyterhub/
jupyterhub --generate-config



start
- user-redirect
stop
status

adding descriptions

nomad:
nomad-central
nomad-central-hub
nomad-public
nomad-public-hub

extra services:
fairmat-events
nomad-analytics-hub

https://gitlab.mpcdf.mpg.de/nomad-lab/nomad-distro/-/blob/main/ops/kubernetes/values.yaml?ref_type=heads



external vs internal urls? proxy?
nomad admin tokens
token scope?


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



auth_state
access_token
refresh_token
id_token
scopoe?


NOMAD_API_URL

Only logged in users can see the tools????
- creating access tokensfo jupyterhub
