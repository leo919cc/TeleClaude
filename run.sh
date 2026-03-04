#!/bin/bash
cd "$(dirname "$0")"
unset CLAUDECODE

while true; do
    .venv/bin/python3 -u bot.py 2>&1
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        # Clean exit (e.g. user stopped it), don't prompt
        break
    fi

    # Bot crashed — show dialog
    CHOICE=$(osascript -e '
        display dialog "Claude TG Bridge has stopped unexpectedly.\n\nPlease check your network connection." \
            with title "Claude TG Bridge" \
            buttons {"Stop", "Retry"} \
            default button "Retry" \
            with icon caution \
            giving up after 0
    ' 2>&1)

    if [[ "$CHOICE" == *"Retry"* ]]; then
        echo "Retrying..."
        continue
    else
        echo "User chose to stop."
        exit 0
    fi
done
