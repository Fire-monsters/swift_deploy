# Domain: Canary Safety
# Question: Is the canary safe to promote?
# Data it cares about: error rate, P99 latency

package policy.canary

import future.keywords.if
import future.keywords.contains

# Load thresholds from data.json
max_error_rate    := data.canary.max_error_rate
max_p99_latency   := data.canary.max_p99_latency_ms

# Default deny
default allow := false

# Allow only if no violations
allow if {
    count(violations) == 0
}

violations contains msg if {
    input.error_rate > max_error_rate
    msg := sprintf(
        "Error rate (%.2f%%) exceeds maximum (%.2f%%)",
        [input.error_rate * 100, max_error_rate * 100]
    )
}

violations contains msg if {
    input.p99_latency_ms > max_p99_latency
    msg := sprintf(
        "P99 latency (%dms) exceeds maximum (%dms)",
        [input.p99_latency_ms, max_p99_latency]
    )
}

# Every decision carries reasoning
decision := {
    "allow": allow,
    "violations": violations,
    "domain": "canary",
    "error_rate": input.error_rate,
    "p99_latency_ms": input.p99_latency_ms,
    "checked_at": input.timestamp
}