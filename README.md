Start by forking main repository (/FAIRmat-NDFI/dev_distro) that will house all your plugins.

# NOMAD Dev Distribution

Benefits

- One-step installations: Install everything at once with editable mode. Since all packages are installed in editable mode,
  changes you make to the code are immediately reflected. Edit your code and rerun tests or the application as needed,
  without needing to reinstall the packages.
- Centralized codebase: Easier navigation and searching across projects.
- Better editor support: Improved autocompletion and refactoring.
- Consistent tooling: Shared linting, testing, and formatting.
- Flexible plugin management: If you're developing plugins for different deployments
  with varying requirements, you can easily create different branches for each deployment
  and configure which plugins to use in the specific branch for that deployment.

Below are instructions for how to create a dev environment for developing [nomad-lab](https://gitlab.mpcdf.mpg.de/nomad-lab) and its plugins.

## Basic infra

1. Make sure you have [docker](https://docs.docker.com/engine/install/) installed.
   Docker nowadays comes with `docker compose` built in. Prior, you needed to
   install the stand-alone [docker-compose](https://docs.docker.com/compose/install/).

2. Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed. We will use it to setup,
   maintain, and use the development environment.
   The standalone installer or a global installation is the recommended way.
   (`brew install uv` on macOS or `dnf install uv` on Fedora).

3. For Windows users, we recommend using the [Devcontainer](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) plugin in VSCode to run the repository inside a container,
   or alternatively, using [GitHub Codespaces](https://github.com/features/codespaces) to run the project.

4. Clone the forked repository.

   ```bash
   git clone https://github.com/<your-username>/dev_distro.git
   cd dev_distro
   ```

5. Run the docker containers with docker compose in
   [detached](https://docs.docker.com/guides/language/golang/run-containers/#run-in-detached-mode)
   (--detach or -d) mode.

   ```sh
   docker compose up -d
   ```

   To shutdown the containers:

   ```sh
   docker compose down
   ```

## Developing nomad + plugins locally.

This guide explains how to set up a streamlined development environment for nomad-lab and its plugins using
[`uv` workspaces](https://docs.astral.sh/uv/concepts/workspaces/#workspaces).
This approach eliminates the need for multiple pip install commands by leveraging a monorepo and a single installation step.

In this example, we'll set up the development environment for a developer working
on the following plugins: `nomad-parser-plugins-electronic` and
`nomad-measurements`. The first plugin already comes as a dependency
in this dev distribution. On the contrary, the second plugin is not listed as a
dependency. In the following, we take a look at how to setup the environment in
these two situations.

### Step-by-Step Setup

1. Update submodules

   This loads the `nomad-lab` package which is already listed as a submodule.

   ```bash
   git submodule update --init --recursive
   ```

2. Add local plugins

   Assuming that you already have a git repo for your plugins, add them to the
   `packages/` directory as submodules. In case, you are looking to create a plugin
   repo from scratch, consider using our plugin template:
   [nomad-plugin-template](https://github.com/FAIRmat-NFDI/nomad-plugin-template).

   ```bash
   git submodule add https://github.com/<package_name>.git packages/<package_name>
   ```

   Repeat for all the plugin packages you want to add and develop. For our example:

   ```bash
   git submodule add https://github.com/nomad-coe/electronic-parsers.git packages/nomad-parser-plugins-electronic

   git submodule add https://github.com/FAIRmat-NFDI/nomad-measurements.git packages/nomad-measurements
   ```

3. Modify `pyproject.toml`

   To ensure `uv` recognizes the
   local plugins (a local copy of your plugin repository available in `packages/` directory),
   we need to make some modifications in the `pyproject.toml`.
   These include adding the plugin package to `[project.dependencies]` and
   `[tool.uv.sources]` tables.
   For the packages listed under `[tool.uv.sources]`, `uv` uses the local code
   directory made available under `packages/` with the previous
   step.

   Some of the plugins are already listed under
   `[project.dependencies]`. If you want to develop one of them, you
   have to add them under `[tool.uv.sources]`. We do this for `nomad-parser-plugins-electronics`.

   ```toml
   [tool.uv.sources]
   ...
   nomad-parser-plugins-electronic = { workspace = true }
   ```

   If you're developing a plugin **not** listed under `[project.dependencies]`, you
   must first add it as a dependency. After adding the dependencies, update the
   `[tool.uv.sources]` section in your `pyproject.toml` file to reflect the new
   plugins. You can either add it manually abd run `uv sync`:

   ```toml
   [project]
   dependencies = [
   ...
   "nomad-measurements",
   ]

   [tool.uv.sources]
   ...
   nomad-measurements = { workspace = true }
   ```

   Or, you can use `uv add` which adds the dependency and the source in `pyproject.toml`
   and sets up the environment:

   ```bash
   uv add nomad-measurements
   ```

> [!NOTE]
> You can also use `uv` to install a specific branch of the plugin submodule.
>
> ```bash
> uv add https://github.com/FAIRmat-NFDI/nomad-measurements --branch <specific-branch-name>
> ```

### Day-to-Day Development

After the initial setup, here’s how to manage your daily development tasks.

1. Update the environment (This step updates the submodules and installs the necessary dependencies):

   ```bash
   uv run poe setup
   ```

> [!NOTE]
>
> `uv sync` and `uv run` automatically manages the virtual environment for you.
> There's no need to manually create or activate a venv.
> Any `uv run` commands will automatically use the correct environment by default.
> Read more about `uv` commands to manage the dependencies [here](https://docs.astral.sh/uv/concepts/projects/#managing-dependencies).

2. Running `nomad` api app (equivalent to running `uv run nomad admin run appworker`).

   ```bash
   uv run poe start
   ```

3. Start NOMAD GUI

   ```bash
   cd packages/nomad-FAIR/gui
   yarn
   yarn start
   ```

4. Run the docs server (optional: only if you wish to run the documentation server):

   ```bash
   uv run poe docs
   ```

5. Running tests

   To run tests across the project, use the uv run command to execute pytest in the relevant directory. For instance:

   ```bash
   uv run --directory packages/package_name pytest
   ```

   This allows you to run tests for a specific parser or package. For running tests across all packages, simply repeat the command for each directory.

6. Linting & code formatting

   To check for code style issues using ruff, run the following command:

   ```bash
   uv run ruff check .
   ```

   This will lint all files.

   For auto-formatting:

   ```bash
   uv run ruff format .
   ```

7. Adding new plugins

   To add a new package, follow [setup guide](#step-by-step-setup) and add it into the `packages/` directory and ensure it's listed in `pyproject.toml` under `[tool.uv.sources]`. Then, install it by running:

   ```bash
   uv sync
   ```

8. Removing an existing plugin

   To remove an existing plugin from the workspace in `packages/` directory, do the following and commit:

   ```bash
   git rm <path-to-submodule>
   ```

   Then you can remove the plugin from `[tool.uv.sources]` in `pyproject.toml` to
   stop uv from using the local plugin repository.

   Additionally, if you want to remove the plugin from being a dependency of your
   NOMAD installation, you can use `uv` to entirely remove it:

   ```bash
   uv remove <plugin-name>
   ```

9. Modifying dependencies in packages.

   ```bash
   uv add --package <PACKAGE_NAME> <DEPENDENCY_NAME>
   ```

   For example:

   ```bash
   uv add --package nomad-measurements "pandas>=2.0"
   uv remove --package nomad-lab numpy
   ```

10. Keeping Up-to-Date

    To pull updates from the main repository and submodules, run:

    ```bash
    git pull --recurse-submodules
    ```

    Afterward, sync your environment:

    ```bash
    uv sync
    ```

### Updating the fork

To keep your fork up to date with the latest changes from the original repository (upstream), follow these steps:

1. Add the upstream Remote

   If you haven't already, add the original repository as upstream:

   ```bash
   git remote add upstream https://github.com/FAIRmat-NFDI/dev_distro.git
   ```

2. Fetch the Latest Changes from upstream

   Fetch the latest commits from the upstream repository:

   ```bash
   git fetch upstream
   ```

3. Merge upstream/main into Your Local Branch

   Switch to the local branch (e.g., main) you want to update, and merge the changes from upstream/main:

   ```bash
   git checkout main
   git merge upstream/main
   ```

   Resolve any merge conflicts if necessary, and commit the merge.

4. Push the Updates to Your Fork

   After merging, push the updated branch to your fork on GitHub:

   ```bash
   git push origin main
   ```
