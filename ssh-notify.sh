# Place this file in /etc/profile.d/ (files there are sourced, not executed,
# so it can't be the Python script itself).
#
# It starts /usr/local/bin/ssh-notify (ssh-notify.py) in the background so
# the login isn't delayed by the network requests.

if [ -n "$SSH_CLIENT" ] && [ -x /usr/local/bin/ssh-notify ]; then
    ( /usr/local/bin/ssh-notify </dev/null >/dev/null 2>&1 & )
fi
