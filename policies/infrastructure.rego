# Domain: Infrastructure
# Question: Is the host safe to deploy to?
# Data it cares about: disk, cpu, memory

package policy.infrastructure

import future.keywords.if
import future.keywords.contains

# Load thresholds from data.json (not hardcoded here)
min_disk_gb   := data.infrastructure.min_disk_gb
max_cpu_load  := data.infrastructure.max_cpu_load
max_mem_pct   := data.infrastructure.max_mem_percent

# Default deny
default allow := false

# Allow only if no violations
allow if {
    count(violations) == 0
}

# Collect all violations with reasons
violations contains msg if {
    input.disk_free_gb < min_disk_gb
    msg := sprintf(
        "Disk free (%.1fGB) is below minimum (%.1fGB)",
        [input.disk_free_gb, min_disk_gb]
    )
}

violations contains msg if {
    input.cpu_load > max_cpu_load
    msg := sprintf(
        "CPU load (%.2f) exceeds maximum (%.2f)",
        [input.cpu_load, max_cpu_load]
    )
}

violations contains msg if {
    input.mem_percent > max_mem_pct
    msg := sprintf(
        "Memory usage (%.1f%%) exceeds maximum (%d%%)",
        [input.mem_percent, max_mem_pct]
    )
}

# Every decision carries reasoning — never a bare boolean
decision := {
    "allow": allow,
    "violations": violations,
    "domain": "infrastructure",
    "checked_at": input.timestamp
}