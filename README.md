This is highly WIP. The design intent is to have a tiny service running on the node with borgbackup repos to handle locking them. This allows dependent upstream services, such as offsite sync jobs, to perform their work without having write access to the repositories.

## Runtime requirements
- A Redis service, the address provided with the `--redis_host` flag.
- A Bearer Token, provided with the `--token` flag. Providing a matching token is required for all API calls.
- A directory with borgbackup repositories with write access, provided with the `--repodir` flag.

### All app specific flags
See `--helpfull` for the entire list. These are just the ones specific to this service.
```shell
borg_lockservice.service:
  --[no]dev: Enable development mode. Defaults to False, should not be enabled in production.
    (default: 'false')
  --host: Listen address for the host.
    (default: '0.0.0.0')
  --port: Listen port for the service. Defaults to 8000
    (default: '8000')
    (an integer)
  --redis_host: Host portion of a redis server used for keeping state.
  --redis_port: Port of the redis server.
    (default: '6379')
    (an integer)
  --repodir: Directory containing repos.
  --token: Bearer token required to access the API.
```

### Debian build dependencies
Since some packges may not have wheels available, the following were observed as needed on Debian 12 to build:
- `libacl1-dev`
- `libfuse-dev`
