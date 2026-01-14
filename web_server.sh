#!/bin/bash

# Web server control script for AITrader
# Usage: ./web_server.sh {start|stop|restart|status}

WORKDIR="/home/code/aitrader"
PID_FILE="$WORKDIR/web_server.pid"
LOG_FILE="$WORKDIR/logs/web_server.log"
HOST="0.0.0.0"
PORT="8000"

# Function to start server
start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Web server is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi

    echo "Starting web server..."
    cd "$WORKDIR"

    # Create logs directory if it doesn't exist
    mkdir -p "$WORKDIR/logs"

    nohup python -m uvicorn web.main:app --host $HOST --port $PORT \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    echo "Web server started (PID: $!)"
    echo "Logs: $LOG_FILE"
    echo "Access: http://$HOST:$PORT"
}

# Function to stop server
stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Web server is not running (no PID file)"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping web server (PID: $PID)..."
        kill $PID
        sleep 2

        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            echo "Force killing web server..."
            kill -9 $PID
        fi

        rm -f "$PID_FILE"
        echo "Web server stopped"
    else
        echo "Web server is not running (stale PID file)"
        rm -f "$PID_FILE"
    fi
}

# Function to check status
status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Web server is running (PID: $PID)"
            echo "Access: http://$HOST:$PORT"
            echo "Logs: $LOG_FILE"
            return 0
        else
            echo "Web server is not running (stale PID file)"
            return 1
        fi
    else
        echo "Web server is not running"
        return 1
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 1
        start_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
