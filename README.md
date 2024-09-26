Start by forking main repository (/fair_nfdi/dev_distro) that will house all your plugins.

# NOMAD Dev Distribution

Benefits

- One-step installations: Install everything at once with editable mode.
- Centralized codebase: Easier navigation and searching across projects.
- Better editor support: Improved autocompletion and refactoring.
- Consistent tooling: Shared linting, testing, and formatting.

Below are instructions for how to create a dev env for developing NOMAD and nomad plugins.

## Basic infra

1. Make sure you have [docker](https://docs.docker.com/engine/install/) installed.
   Docker nowadays comes with `docker compose` built in. Prior, you needed to
   install the stand-alone [docker-compose](https://docs.docker.com/compose/install/).

2. Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.
   The standalone installer or a global installation is the recommended way.
   (`brew install uv` on macOS or `dnf install uv` on Fedora).

3. Clone the repository.

   ```bash
   git clone https://github.com/<your-username>/dev_distro.git
   cd dev_distro
   ```

4. _On Linux only,_ recursively change the owner of the `.volumes` directory to the nomad user (1000)

   ```sh
   sudo chown -R 1000 .volumes
   ```

5. Run the docker containers with docker compose in detached (--detach or -d) mode

   ```sh
   docker compose up -d
   ```

   To shutdown the containers:

   ```sh
   docker compose down
   ```

## Developing nomad + plugins locally.

This guide explains how to set up a streamlined development environment for nomad-lab and its plugins using uv workspaces.
This approach eliminates the need for multiple pip install commands by leveraging a monorepo and a single installation step.

In this example, we'll set up the development environment for a developer working on the following computational parsers:

- nomad-parser-plugins-electronic
- nomad-parser-plugins-atomistic
- nomad-parser-plugins-workflow
- nomad-parser-plugins-database

### Step-by-Step Setup

1. Update submodules

   ```bash
   git submodule update --init --recursive
   ```

2. Add local plugins

   Add the plugin repositories to the packages/ directory, either as submodules.

   ```bash
   git submodule add https://github.com/package_name.git packages/package_name
   ```

   For example:

   ```bash
   git submodule add https://github.com/nomad-coe/atomistic-parsers.git packages/nomad-parser-plugins-atomistic
   ```

   Repeat for all local dev packages (e.g., nomad-parser-plugins-electronic, nomad-parser-plugins-atomistic, etc.).

3. Modify pyproject.toml

   Ensure uv recognizes the local packages by modifying the `pyproject.toml`:

   ```toml
   [tool.uv.workspace]
   members = ["packages/*"]

   [tool.uv.sources]
   nomad-lab = { workspace = true }
   nomad-parser-plugins-electronic = { workspace = true }
   nomad-parser-plugins-atomistic = { workspace = true }
   nomad-parser-plugins-workflow = { workspace = true }
   nomad-parser-plugins-database = { workspace = true }
   ...
   ```

   > [!NOTE]
   > If you're developing a plugin not listed under [project.dependencies], you must first add it as a dependency. You can do this with uv:

   ```bash
   uv add nomad-measurements
   uv add https://github.com/FAIRmat-NFDI/nomad-parser-vasp --branch develop
   ```

   After adding the dependencies, update the [tool.uv.sources] section in your pyproject.toml file to reflect the new plugins:

   ```toml
   dependencies = [
   ...
   "nomad-measurements",
   "nomad-parser-vasp",
   ]

   [tool.uv.sources]
   ...
   nomad-measurements = { workspace = true }
   nomad-parser-vasp = { workspace = true }
   ```

4. Install dependencies

   Run the following command to install all dependencies, including the local packages in editable mode:

   ```bash
   uv sync
   ```

   > [!NOTE]
   > `uv sync` and `uv run` automatically manages the virtual environment for you. There's no need to manually create or activate a venv.
   > Any `uv run` commands will automatically use the correct environment by default.

5. Running `nomad` api app.

   ```bash
   uv run nomad admin run appworker
   ```

6. Setup GUI

   ```bash
   cd packages/nomad-FAIR/gui
   uv run python -m nomad.cli dev gui-env > .env.development
   yarn
   ```

7. Start nomad gui

   ```bash
   cd packages/nomad-FAIR/gui
   yarn start
   ```

### Day-to-Day Development

After the initial setup, here’s how to manage your daily development tasks.

1. Update submodules

   ```bash
   git submodule update --init --recursive
   ```

2. Installing dependencies

   If you've added new dependencies or made changes to your environment, install or update them by running:

   ```bash
   uv sync
   ```

   This will sync all packages and ensure everything is installed in editable mode.

3. Running tests

   To run tests across the project, use the uv run command to execute pytest in the relevant directory. For instance:

   ```bash
   uv run --directory packages/package_name pytest
   ```

   This allows you to run tests for a specific parser or package. For running tests across all packages, simply repeat the command for each directory.

4. Making code changes

   Since all packages are installed in editable mode, changes you make to the code are immediately reflected. 
   Edit your code and rerun tests or the application as needed, without needing to reinstall the packages.

5. Linting & code formatting

   To check for code style issues using ruff, run the following command:

   ```bash
   uv run ruff check .
   ```

   This will lint all files.

   For auto-formatting:

   ```bash
   uv run ruff format .
   ```

6. Adding new plugins

   To add a new package, follow setup guide and add it into the packages/ directory and ensure it's listed in pyproject.toml under [tool.uv.sources]. Then, install it by running:

   ```bash
   uv sync
   ```

7. Modifying dependencies in packages.

   ```bash
   uv add --package <PACKAGE_NAME> <DEPENDENCY_NAME>
   ```

   For example:

   ```bash
   uv add --package nomad-measurements "pandas>=2.0"
   uv remove --package nomad-lab numpy
   ```

8. Keeping Up-to-Date

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

By following these steps, you ensure that your fork stays in sync with the latest changes from the original repository.
