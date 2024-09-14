#!/bin/sh
set -e -u

if [ -z "$UID" ]; then
  echo "failed to start, pls pass -e UID=<user-id>"
  exit 1
fi
if [ -z "$GID" ]; then
  echo "failed to start, pls pass -e GID=<group-id>"
  exit 1
fi
if [ -z "$UNAME" ]; then
  echo "failed to start, pls pass -e UNAME=<username>"
  exit 1
fi

FUID=$(getent passwd "$UNAME" | cut -d: -f3)
if [ -n "$FUID" -a "x$FUID" != "x$UID" ] ; then
    echo "failed to start, UNAME exists but with unexpected UID $FUID instead of $UID"
    exit 1
fi

if [ -z "$FUID" ] ; then
  # add group
  addgroup -g $GID -S $UNAME
  adduser  -s /bin/bash -u $UID -D -S $UNAME -G $UNAME
  echo "$UNAME:light" | chpasswd 2>&1 > /dev/null
  mkdir -p /etc/sudoers.d
  echo "$UNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$UNAME
  chmod 0440 /etc/sudoers.d/*
  export HOME=/home/$UNAME
  export USER=$UNAME
fi

# add docker group using injected ARG $DOCKER_GID
# on alpine ping group is coliding with docker-group on id 999 - delete it if exists
getent group ping >/dev/null && delgroup ping > /dev/null
# add docker group and add user to docker group

# add docker group if not exists, add user to the group
GR=$(getent group $DOCKER_GID | cut -d: -f1)
if [ -z "$GR" ]; then
    addgroup -g $DOCKER_GID docker
    addgroup $UNAME docker
else
    addgroup $UNAME $GR
fi


#addgroup -g $DOCKER_GID docker
#addgroup $UNAME docker

export PATH=$PATH:$HOME/.local/bin

exec su-exec $UNAME "$@"

