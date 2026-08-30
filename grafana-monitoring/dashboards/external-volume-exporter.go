package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"syscall"
)

var (
	deviceID   = flag.String("device-id", "mini", "stable device identifier")
	deviceName = flag.String("device-name", "Mac mini", "human-readable device name")
	listen     = flag.String("listen", "0.0.0.0:9104", "HTTP listen address")
	mountpoint = flag.String("mountpoint", "/Volumes/xsExternal", "external volume mountpoint")
	volume     = flag.String("volume", "xsExternal", "volume label")
)

func main() {
	flag.Parse()
	http.HandleFunc("/metrics", metrics)
	http.HandleFunc("/-/healthy", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	log.Printf("external-volume-exporter watching %s on %s", *mountpoint, *listen)
	log.Fatal(http.ListenAndServe(*listen, nil))
}

func metrics(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
	labels := fmt.Sprintf("device_id=%s,device_name=%s,volume=%s,mountpoint=%s",
		quote(*deviceID), quote(*deviceName), quote(*volume), quote(*mountpoint))

	fmt.Fprintln(w, "# HELP external_volume_mounted Whether the configured external volume is mounted.")
	fmt.Fprintln(w, "# TYPE external_volume_mounted gauge")

	var stat syscall.Statfs_t
	if err := syscall.Statfs(*mountpoint, &stat); err != nil {
		fmt.Fprintf(w, "external_volume_mounted{%s} 0\n", labels)
		fmt.Fprintln(w, "# HELP external_volume_collection_success Whether filesystem statistics were collected successfully.")
		fmt.Fprintln(w, "# TYPE external_volume_collection_success gauge")
		fmt.Fprintf(w, "external_volume_collection_success{%s} 0\n", labels)
		return
	}

	blockSize := uint64(stat.Bsize)
	total := stat.Blocks * blockSize
	available := stat.Bavail * blockSize
	used := total - stat.Bfree*blockSize
	usedPercent := 0.0
	if total > 0 {
		usedPercent = float64(used) / float64(total) * 100
	}

	fmt.Fprintf(w, "external_volume_mounted{%s} 1\n", labels)
	fmt.Fprintln(w, "# HELP external_volume_collection_success Whether filesystem statistics were collected successfully.")
	fmt.Fprintln(w, "# TYPE external_volume_collection_success gauge")
	fmt.Fprintf(w, "external_volume_collection_success{%s} 1\n", labels)
	fmt.Fprintln(w, "# HELP external_volume_size_bytes Total filesystem capacity in bytes.")
	fmt.Fprintln(w, "# TYPE external_volume_size_bytes gauge")
	fmt.Fprintf(w, "external_volume_size_bytes{%s} %d\n", labels, total)
	fmt.Fprintln(w, "# HELP external_volume_available_bytes Space available to non-root users in bytes.")
	fmt.Fprintln(w, "# TYPE external_volume_available_bytes gauge")
	fmt.Fprintf(w, "external_volume_available_bytes{%s} %d\n", labels, available)
	fmt.Fprintln(w, "# HELP external_volume_used_bytes Filesystem space in use in bytes.")
	fmt.Fprintln(w, "# TYPE external_volume_used_bytes gauge")
	fmt.Fprintf(w, "external_volume_used_bytes{%s} %d\n", labels, used)
	fmt.Fprintln(w, "# HELP external_volume_used_percent Filesystem capacity currently in use as a percentage.")
	fmt.Fprintln(w, "# TYPE external_volume_used_percent gauge")
	fmt.Fprintf(w, "external_volume_used_percent{%s} %s\n", labels, strconv.FormatFloat(usedPercent, 'f', -1, 64))
}

func quote(value string) string {
	return strconv.Quote(value)
}
