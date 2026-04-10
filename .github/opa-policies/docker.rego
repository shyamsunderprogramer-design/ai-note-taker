# OPA Policy: Dockerfile security best practices
# Used by Conftest in the security scanning pipeline

package main

# Deny if Dockerfile uses latest tag
deny[msg] {
    input[i].Cmd == "from"
    contains(input[i].Value, ":latest")
    msg := sprintf("Line %d: Do not use :latest tag — use specific version pins", [input[i].Line])
}

# Deny if running as root
deny[msg] {
    not has_user
    msg := "Dockerfile does not specify USER — container will run as root"
}

has_user {
    input[i].Cmd == "user"
}

# Warn if no HEALTHCHECK
warn[msg] {
    not has_healthcheck
    msg := "Dockerfile should include HEALTHCHECK instruction"
}

has_healthcheck {
    input[i].Cmd == "healthcheck"
}

# Warn if using ADD instead of COPY
warn[msg] {
    input[i].Cmd == "add"
    msg := sprintf("Line %d: Prefer COPY over ADD", [input[i].Line])
}

# Deny if using sudo
deny[msg] {
    input[i].Cmd == "run"
    contains(lower(input[i].Value), "sudo")
    msg := sprintf("Line %d: Do not use sudo in Dockerfile", [input[i].Line])
}