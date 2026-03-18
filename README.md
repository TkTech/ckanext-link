# ckanext-link

Broken link checker extension for CKAN 2.11+.

Checks all resource URLs across your CKAN instance for broken links. Results
are viewable by sysadmins in the CKAN admin panel. Includes SSRF protection,
crash recovery with heartbeat-based resume, and progress tracking.

## Installation

```bash
pip install -e git+https://github.com/TkTech/ckanext-link.git#egg=ckanext-link
```

Add `link` to `ckan.plugins` in your CKAN config, then run the database
migration:

```bash
ckan -c ckan.ini db upgrade -p link
```

## Usage

Navigate to `/ckan-admin/link-checker` and click **Run Link Check**. The check
runs as a background job — you'll need a CKAN jobs worker running:

```bash
ckan -c ckan.ini jobs worker
```

Progress is displayed in real-time. If the worker crashes, the job can be
resumed from where it left off.

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `ckanext.link.timeout` | `30` | Read timeout in seconds |
| `ckanext.link.connect_timeout` | `10` | Connection timeout in seconds |
| `ckanext.link.max_redirects` | `5` | Maximum redirects to follow |
| `ckanext.link.user_agent` | `"CKAN Link Checker/1.0"` | User-Agent header |
| `ckanext.link.blocked_domains` | `""` | Space-separated domains to skip |
| `ckanext.link.check_head_first` | `true` | Try HEAD before GET |
| `ckanext.link.batch_delay` | `0.5` | Delay in seconds between requests |
| `ckanext.link.verify_ssl` | `false` | Verify SSL certificates |

## i18n

English and French translations are included.
