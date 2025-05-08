# UPnP Port Mapping Client

This script uses MiniUPnPc to manage UPnP port mappings based on a YAML configuration file. It automatically creates specified port mappings on startup and cleans them up on exit.

## Features

- Reads port mapping configurations from a YAML file.
- Validates configuration entries.
- Adds specified port mappings using UPnP.
- Removes all managed port mappings on script termination (Ctrl+C or SIGTERM).

## Configuration

The script requires a configuration file named `ports.yaml` located at `/config/ports.yaml` (configurable via the `CONFIG_PATH` variable in the script).

The `ports.yaml` file should contain a list of port mapping entries. Each entry must have the following fields:

- `id`: A unique identifier for the mapping rule (e.g., "webserver", "ssh").
- `internal_port`: The internal port number on the machine running the script.
- `external_port`: The external port number to be opened on the router.
- `protocol`: The protocol for the mapping (either `TCP` or `UDP`).

**Example `ports.yaml`:**

```yaml
- id: "my-webserver"
  internal_port: 8080
  external_port: 80
  protocol: "TCP"
- id: "my-game"
  internal_port: 27015
  external_port: 27015
  protocol: "UDP"
```

## Dependencies

- `miniupnpc`: A Python library for UPnP port mapping.
- `PyYAML`: A Python library for YAML parsing.

You can install these dependencies using pip:

```bash
pip install miniupnpc PyYAML
```

## Running the Script

1.  **Create the configuration file**: Ensure `ports.yaml` is created and placed in the expected location (e.g., `/config/ports.yaml` if running in Docker, or update `CONFIG_PATH` in the script).
2.  **Run the Python script**:
    ```bash
    python upnp_client.py
    ```

The script will output the status of each port mapping operation.

## Docker Support

This project includes a `Dockerfile` and `docker-compose.yml` for running the script in a containerized environment.

**Prerequisites:**

- Docker
- Docker Compose

**Building the Docker image:**

```bash
docker build -t upnp-client .
```

**Running with Docker Compose:**

1.  Create a `ports.yaml` file in a directory that will be mounted into the container (e.g., `./config/ports.yaml` if you create a `config` directory in the project root).
2.  Update the `volumes` section in `docker-compose.yml` if your `ports.yaml` is located elsewhere. By default, it expects `./config/ports.yaml` on the host to be mapped to `/config/ports.yaml` in the container.

    ```yaml
    # docker-compose.yml
    version: '3.8'
    services:
      upnp-client:
        build: .
        image: upnp-client # Optional: specify image name
        container_name: upnp_client
        restart: unless-stopped
        network_mode: "host" # Required for UPnP to discover the gateway
        volumes:
          - ./ports.yaml:/config/ports.yaml # Mount your config file
        # If your ports.yaml is in a 'config' subdirectory:
        #  - ./config/ports.yaml:/config/ports.yaml
    ```
3.  Start the service:
    ```bash
    docker-compose up -d
    ```

The container will run in host network mode to allow UPnP discovery and operations. The script will read the configuration from the mounted `ports.yaml` file.

**Stopping and cleaning up (Docker Compose):**

```bash
docker-compose down
```

This will stop the container and the script inside will attempt to clean up the port mappings.

## How it Works

1.  **Initialization**:
    *   Registers signal handlers for `SIGINT` (Ctrl+C) and `SIGTERM` to ensure graceful shutdown and cleanup of port mappings.
    *   Registers an `atexit` handler for cleanup in case of normal script termination.
2.  **Configuration Loading**:
    *   Loads port mapping rules from the `ports.yaml` file.
    *   Raises an error if the configuration file is not found.
3.  **UPnP Setup**:
    *   Initializes the MiniUPnPc library.
    *   Discovers UPnP-enabled IGD (Internet Gateway Device) on the network.
    *   Selects the IGD and retrieves the LAN IP address of the host.
4.  **Applying Mappings**:
    *   Iterates through each entry in the loaded configuration.
    *   Validates each entry to ensure all required fields (`id`, `internal_port`, `external_port`, `protocol`) are present and the protocol is either `TCP` or `UDP`.
    *   For each valid entry, it attempts to add a port mapping using `upnp.addportmapping()`.
    *   Successfully added mappings (external port and protocol) are stored in an `active_mappings` list.
    *   Prints status messages for successful mappings or errors encountered.
5.  **Cleanup**:
    *   The `cleanup()` function is called automatically on script exit (normal or via signals).
    *   It iterates through the `active_mappings` list.
    *   For each active mapping, it attempts to delete the port mapping using `upnp.deleteportmapping()`.
    *   Prints status messages for removed mappings or any errors during removal.

This ensures that ports opened by the script are closed when the script is no longer running, preventing unnecessary open ports on the router.
