This is highly WIP. The design intent is to have a tiny service running on the node with borgbackup repos to handle locking them. This allows dependent upstream services, such as offsite sync jobs, to perform their work without having write access to the repositories.

### Debian build dependencies
Since some packges may not have wheels available, the following were observed as needed on Debian 12 to build:
- `libacl1-dev`
- `libfuse-dev`
