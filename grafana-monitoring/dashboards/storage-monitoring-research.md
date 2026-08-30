# Server storage monitoring research

Research date: 2026-08-28

## Recommendation

Build the dashboard in three layers, in this order:

1. **Filesystem capacity and exhaustion risk** by mount point.
2. **Block-device performance and saturation** by physical device.
3. **Device and array health** from SMART/NVMe and Linux software RAID, when those metrics are available.

The first two layers are portable across Linux servers because node_exporter's `filesystem` and `diskstats` collectors are enabled by default. The project describes them as exposing filesystem space and disk I/O statistics; it also provides include/exclude filters for mount points, filesystem types, and disk devices. [node_exporter collector documentation](https://github.com/prometheus/node_exporter#collectors)

## Panel priorities and PromQL

The selectors below are placeholders: add the dashboard's existing `job`, `instance`, mount-point, filesystem-type, and device filters.

### P0 — capacity and immediate health

| Panel | Recommended query | Why it matters |
|---|---|---|
| Used space by mount | `100 * (1 - node_filesystem_avail_bytes / node_filesystem_size_bytes)` | Show a bar gauge/table with mount point, used %, available bytes, and total bytes. Use `avail`, not `free`: node_exporter defines `avail` as space available to non-root users. [filesystem metric definitions](https://github.com/prometheus/node_exporter/blob/master/collector/filesystem_common.go) |
| Available space trend | `node_filesystem_avail_bytes` | A time series catches fast growth that a current-value gauge misses. Forecast exhaustion with `predict_linear(node_filesystem_avail_bytes[6h], 24*60*60)`. The official node mixin uses a 6-hour observation window plus 24-hour warning and 4-hour critical horizons. [node mixin alert rules](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/alerts/alerts.libsonnet) |
| Inodes used by mount | `100 * (1 - node_filesystem_files_free / node_filesystem_files)` | A filesystem can become unusable with free bytes remaining if it exhausts file nodes. Suppress series where `node_filesystem_files == 0`. The official mixin monitors both inode percentage and predicted exhaustion. [node mixin alert rules](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/alerts/alerts.libsonnet) |
| Filesystem state | `node_filesystem_readonly` and `node_filesystem_device_error` | Read-only remounts and failures to retrieve device statistics are direct health signals, not capacity signals. Both metrics are explicitly exported by the filesystem collector. [filesystem metric definitions](https://github.com/prometheus/node_exporter/blob/master/collector/filesystem_common.go) |

Recommended capacity table columns: mount point, device, filesystem type, used %, used bytes, available bytes, total bytes, inode used %, read-only, and device-error state. Exclude pseudo/ephemeral filesystems such as `tmpfs`, `devtmpfs`, `overlay`, `squashfs`, and container/runtime mounts unless they are operationally important. node_exporter supports filesystem-type and mount-point filters for this purpose. [node_exporter collector filters](https://github.com/prometheus/node_exporter#collectors)

### P1 — throughput, IOPS, latency, and saturation

| Panel | Read query | Write query / note |
|---|---|---|
| Throughput | `rate(node_disk_read_bytes_total[5m])` | `rate(node_disk_written_bytes_total[5m])`; unit B/s |
| IOPS | `rate(node_disk_reads_completed_total[5m])` | `rate(node_disk_writes_completed_total[5m])`; unit ops/s |
| Mean request time | `1000 * rate(node_disk_read_time_seconds_total[5m]) / clamp_min(rate(node_disk_reads_completed_total[5m]), 1e-9)` | Use the analogous write metrics; unit ms/op |
| Busy time | `100 * rate(node_disk_io_time_seconds_total[5m])` | A useful utilization-like signal; unit percent |
| Average queue/backlog | `rate(node_disk_io_time_weighted_seconds_total[5m])` | Show by device. The official node mixin calls this disk saturation and alerts when it remains above 10 for 30 minutes. [node mixin saturation alert](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/alerts/alerts.libsonnet#L1804-L1834) |
| In-flight I/O | `node_disk_io_now` | An instantaneous companion to the weighted queue; table or compact time series |

The Linux kernel defines read/write counts, elapsed read/write time, in-flight I/O, busy time, and weighted I/O time in `/proc/diskstats`. Weighted I/O time incorporates both elapsed time and the number of operations in progress, so it exposes backlog; read/write elapsed time is measured from request allocation to completion. [Linux kernel I/O statistics documentation](https://docs.kernel.org/admin-guide/iostats.html)

Treat busy time as a trend rather than an absolute saturation ceiling on highly concurrent devices. The kernel notes that since Linux 5.0 the underlying field can miss some I/O time when requests run for more than two jiffies concurrently. Weighted queue, request time, and throughput should be read alongside it. [Linux kernel I/O time semantics](https://docs.kernel.org/admin-guide/iostats.html)

Use whole physical devices for workload panels and mount points for capacity panels. Do not sum physical disks, partitions, device-mapper/LVM devices, and RAID devices into one "server total": the same I/O can appear at multiple layers. The kernel also documents differing disk/partition accounting semantics, and node_exporter exposes device filters. [Linux disk-versus-partition notes](https://docs.kernel.org/admin-guide/iostats.html#disks-vs-partitions), [node_exporter diskstats source](https://github.com/prometheus/node_exporter/blob/master/collector/diskstats_linux.go)

`rate()` is required for the disk counters: the kernel documents them as cumulative and monotonic except for in-flight I/O, with resets possible at boot, reattachment, reinitialization, or overflow. [Linux kernel I/O statistics documentation](https://docs.kernel.org/admin-guide/iostats.html)

### P1 — SMART/NVMe device health (optional data source)

SMART is not part of the standard node_exporter filesystem/diskstats metrics. Collect it separately (for example, periodically emit machine-tied metrics through node_exporter's textfile collector) and map the chosen exporter's metric names to these canonical fields. The textfile collector is specifically intended for metrics tied to a machine and reads `*.prom` files from its configured directory. [node_exporter textfile collector](https://github.com/prometheus/node_exporter#textfile-collector)

If the Prometheus Community `smartctl_exporter` is deployed, its current first-party metric names include `smartctl_device_smart_status`, `smartctl_device_smartctl_exit_status`, `smartctl_device_temperature`, `smartctl_device_percentage_used`, `smartctl_device_available_spare`, `smartctl_device_available_spare_threshold`, `smartctl_device_critical_warning`, `smartctl_device_media_errors`, `smartctl_device_num_err_log_entries`, `smartctl_device_power_on_seconds`, `smartctl_device_bytes_written`, and the labeled `smartctl_device_attribute` series for ATA attributes. [smartctl_exporter metric definitions](https://github.com/prometheus-community/smartctl_exporter/blob/master/metrics.go)

Prefer a table with one row per physical drive:

- Overall SMART health / passed state.
- Current temperature and, where available, time above warning or critical temperature.
- NVMe critical-warning bits, available-spare %, spare threshold, percentage used/endurance used, media/data-integrity errors, error-log entries, and unsafe shutdowns.
- ATA/SATA reallocated sectors, current pending sectors, offline uncorrectable sectors, reported uncorrectable errors, interface CRC errors, power-on hours, and drive-specific remaining-life/wear indicators.
- Last self-test result and age of the last successful self-test, if exported.

smartmontools' NVMe implementation emits the critical warning, temperature, available spare and threshold, percentage used, data read/written, power-on hours, unsafe shutdowns, media errors, error-log entries, temperature-warning time, and optional sensor temperatures. [smartmontools NVMe SMART source](https://www.smartmontools.org/static/doxygen/nvmeprint_8cpp_source.html#l00484) Its ATA monitor explicitly checks current-pending and offline-uncorrectable sector counts and temperature. [smartmontools `smartd` source](https://www.smartmontools.org/static/doxygen/smartd_8cpp_source.html#l03802)

Treat ATA raw attributes as model/vendor-specific. smartctl labels `-A` output as vendor-specific, and smartmontools maintains a drive database of model/firmware-specific attribute definitions and formats. Alert first on the normalized health result, explicit failed attributes, and changes from each drive's own baseline; only apply raw-value thresholds that the drive vendor documents. [smartctl option/source documentation](https://www.smartmontools.org/static/doxygen/smartctl_8cpp_source.html#l00171), [smartmontools drive database](https://www.smartmontools.org/static/doxygen/drivedb_8h_source.html)

### P1 — RAID health (when Linux MD is used)

Show array state, active/required disks, failed disks, spare disks, and sync progress. The official node mixin defines:

- Degraded: `node_md_disks_required - ignoring(state) node_md_disks{state="active"} > 0`
- Disk failure: `node_md_disks{state="failed"} > 0`

It treats a degraded array as critical and a failed member as warning. [node mixin RAID alerts](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/alerts/alerts.libsonnet)

## Alert priority

1. **Page immediately:** SMART/NVMe overall health failure or critical warning; filesystem unexpectedly read-only; filesystem device-stat error; RAID degraded; any increase in uncorrectable/media errors on a production drive.
2. **Urgent:** available space below 3%, inodes below 3%, forecast to exhaust within 4 hours, RAID member failed, NVMe spare below threshold, or sustained severe temperature according to the drive's documented limits.
3. **Warning:** available space or inodes below 5%, forecast to exhaust within 24 hours, pending/reallocated sectors increasing, SSD endurance approaching its documented limit, or weighted queue above the workload-specific baseline. The node mixin's portable defaults are 5%/3% immediate free-space thresholds, 24 h/4 h forecast horizons, 5%/3% inode thresholds, and weighted queue above 10 for 30 minutes. [node mixin configuration](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/config.libsonnet), [node mixin alert rules](https://github.com/prometheus/node_exporter/blob/master/docs/node-mixin/alerts/alerts.libsonnet)

Tune performance and temperature alerts per storage class. HDD, SATA SSD, NVMe, RAID, and network-backed storage have materially different normal latency and concurrency, so a single universal latency, queue, or temperature threshold will generate misleading alerts.

## Suggested dashboard layout

1. **Overview:** worst mount usage, lowest available bytes, nearest forecasted exhaustion, any read-only/error state, SMART failures, RAID degradation.
2. **Capacity:** mount-point table plus used/available trends and inode usage.
3. **Performance:** read/write throughput, IOPS, mean request time, busy time, weighted queue, and in-flight I/O by physical device.
4. **Drive health:** SMART/NVMe table and temperature/wear/error trends; hide or mark this row optional when no SMART exporter metrics exist.
5. **RAID:** MD state/member counts/sync progress, shown only when `node_md_*` series exist.

This ordering keeps symptoms visible before diagnostics: capacity and hard health failures at the top, then the workload data needed to explain slow storage.
