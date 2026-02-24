#!/usr/bin/env bash
# Automated incremental load test runner — TeaStore Image Provider (Person 5).
#
# Usage:
#   chmod +x run_image_tests.sh && ./run_image_tests.sh
set -euo pipefail

COMPOSE_FILE="docker-compose-image.yaml"
LOCUST_FILE="locust_image.py"
HOST="http://localhost:8080"
WEBUI_URL="${HOST}/tools.descartes.teastore.webui/"
IMAGE_URL="http://localhost:8083/tools.descartes.teastore.image/rest/image/finished"
REGISTRY_URL="http://localhost:8081/tools.descartes.teastore.registry/"

RESULTS_DIR="results/image_service/raw"
GRAPHS_DIR="results/image_service/graphs"
USER_COUNTS=(10 25 50 100 200)
# Portable last-element access — bash 3.x (macOS default) does not support
# negative array indices like ${USER_COUNTS[-1]}.
LAST_USER_COUNT="${USER_COUNTS[$(( ${#USER_COUNTS[@]} - 1 ))]}"
SPAWN_RATE=10
RUN_TIME="2m"
MAX_WAIT=300

# Find locust binary.
if command -v locust &>/dev/null; then
    LOCUST="locust"
else
    LOCUST="$(python3 -m site --user-base)/bin/locust"
    [[ -f "$LOCUST" ]] || { echo "❌ locust not found. pip3 install locust"; exit 1; }
fi

wait_for() {
    local url=$1 name=$2 elapsed=0
    echo "Waiting for ${name}..."
    while ! curl -sf "$url" >/dev/null 2>&1; do
        ((elapsed += 10))
        [[ $elapsed -ge $MAX_WAIT ]] && { echo "  ❌ ${name} timed out"; exit 1; }
        echo "  ... ${elapsed}s / ${MAX_WAIT}s"
        sleep 10
    done
    echo "  ✅ ${name} ready (${elapsed}s)"
}

main() {
    mkdir -p "$RESULTS_DIR" "$GRAPHS_DIR"

    echo "==> Starting Docker stack"
    docker compose -f "$COMPOSE_FILE" up -d

    echo "==> Waiting for services"
    wait_for "$REGISTRY_URL" "registry"
    wait_for "$IMAGE_URL" "image"
    wait_for "$WEBUI_URL" "webui"
    echo "Warm-up: 30s..." && sleep 30

    echo "==> Running load tests"
    for users in "${USER_COUNTS[@]}"; do
        echo "--- ${users} users (${RUN_TIME}, spawn ${SPAWN_RATE}/s) ---"
        "$LOCUST" -f "$LOCUST_FILE" --host="$HOST" \
            --users "$users" --spawn-rate "$SPAWN_RATE" \
            --run-time "$RUN_TIME" --headless \
            --csv="${RESULTS_DIR}/${users}_users" --csv-full-history \
            2>&1 | tee "${RESULTS_DIR}/${users}_users_console.log"
        echo "  ✅ Done: ${users} users"
        [[ "$users" != "$LAST_USER_COUNT" ]] && sleep 15
    done

    echo "==> Generating graphs"
    python3 generate_image_graphs.py

    echo "==> Tearing down"
    docker compose -f "$COMPOSE_FILE" down

    echo "==> Complete"
    echo "  CSV:    ${RESULTS_DIR}/"
    echo "  Graphs: ${GRAPHS_DIR}/"
}

main "$@"
