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

- `id`: A unique identifier for the mapping rule.
- `name`: Your service name (e.g., "webserver", "ssh").
- `internal_port`: The internal port number on the machine running the script.
- `external_port`: The external port number to be opened on the router.
- `protocol`: The protocol for the mapping (either `TCP` or `UDP`).

**Example `ports.yaml`:**

```yaml
- id: 1
  name: "my-webserver"
  internal_port: 8080
  external_port: 80
  protocol: "TCP"
- id: 2
  name: "my-game"
  internal_port: 27015
  external_port: 27015
  protocol: "UDP"
```

**Running with Docker Compose:**

1.  Create a `ports.yaml` file in a directory that will be mounted into the container.

    ```yaml
    # docker-compose.yml
    services:
      upnp-client:
        image: miraz4300/upnp-client:latest
        container_name: upnp_client
        restart: unless-stopped
        network_mode: "host" # Required for UPnP to discover the gateway
        volumes:
          - ./config:/config # Mount your config file
    ```
3.  Start the service:
    ```bash
    docker compose up -d
    ```

The container will run in host network mode to allow UPnP discovery and operations. The script will read the configuration from the mounted `ports.yaml` file.

**Stopping and cleaning up (Docker Compose):**

```bash
docker compose down
```

This will stop the container and the script inside will attempt to clean up the port mappings.
