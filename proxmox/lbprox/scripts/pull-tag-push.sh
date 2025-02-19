#!/usr/bin/env bash

set -e -u -o pipefail

# source ./scripts/.env
LB_ANSIBLE_VERSION=v9.13.0
DEFAULT_SRC_IMAGE_REGISTRY="lbdocker:5000"
DEFAULT_DST_IMG_REGISTRY="docker.lightbitslabs.com/lbprox"

# Get the tag pointing at HEAD
tag=$(git tag --points-at HEAD)

# Check if the tag is empty
if [ -z "$tag" ]; then
  echo "Error: Current HEAD does not point to a tag."
  exit 1  # Fail the script
fi

# If the tag is not empty, continue with the rest of the script
echo "Current HEAD points to tag: $tag"

export APP_VERSION="$tag"

# cloudsmith-cli installation and login:
# pip install cloudsmith-cli

# cloudsmith login
# Login: yogev@lightbitslabs.com
# Password: <look at your vault, note this is the cloudsmith PASSWORD! not the API_TOKEN>


# First update APP_VERSION in ./scripts/.env to match the current version
# you can find the next version by running:

# semantic-release  version --no-push --print-tag

# container versioning: reflects changes specific to a single service or component

## Release process:
# 1. make release (should emit new_version and tag it)
# 2. find all occerences of last version in the code and update to new_version
# 3. build lbprox image and push it to registry, build docs and ansible tarballs:
#      make build-image push-image
# 1. update version in the deploy/ansible/dms.env to match new_version.
# 2. upload all images to the new registry (pulp03.lab.lightbitslabs.com/dms in this example):
#       ./scripts/pull-tag-push.sh lb_images lbdocker:5000 docker.lightbitslabs.com/lbprox
#       ./scripts/pull-tag-push.sh upload_os_qcow_images
#       ./scripts/pull-tag-push.sh upload_dms_docs

# Tagging the artifacts:
#
# tag_name = release-${APP_VERSION}
# cloudsmith list packages lightbits/dms
# for each package:
#    tags = cloudsmith tags list lightbits/dms/<package_name>
#    if tag_name not in tags:
#       cloudsmith tags add lightbits/dms/<package_name> <tag_name>

# internal images
function lb_images() {
    docker pull ${SRC_IMAGE_REGISTRY}/lb-ansible:${LB_ANSIBLE_VERSION}
    docker tag ${SRC_IMAGE_REGISTRY}/lb-ansible:${LB_ANSIBLE_VERSION} ${DST_IMG_REGISTRY}/lb-ansible:${LB_ANSIBLE_VERSION}
    docker push ${DST_IMG_REGISTRY}/lb-ansible:${LB_ANSIBLE_VERSION}

    IMG_VERSION=$(make --no-print-directory print-GIT_TAG)
    docker pull ${SRC_IMAGE_REGISTRY}/lbprox:${IMG_VERSION}
    docker tag ${SRC_IMAGE_REGISTRY}/lbprox:${IMG_VERSION} ${DST_IMG_REGISTRY}/lbprox:${APP_VERSION}
    docker push ${DST_IMG_REGISTRY}/lbprox:${APP_VERSION}
}

function upload_os_qcow_images() {
    echo "Upload rocky-9-target image"
    curl -l https://pulp03.lab.lightbitslabs.com/pulp/content/rocky-9-target/qcow2/latest/rocky-9-target.qcow2 -o /tmp/rocky-9-target.qcow2
    cloudsmith push raw lightbits/lbprox /tmp/rocky-9-target.qcow2 \
        --version=${APP_VERSION} \
        --summary="qcow2 image of rocky 9.5 rocky-9-target.qcow2" \
        --description="qcow2 image of rocky 9.5 rocky-9-target.qcow2" \
        --content-type="application/octet-stream" \
	--tags="release-${APP_VERSION}"
    rm -rf /tmp/rocky-9-target.qcow2

    echo "Upload ubuntu-24.04-initiator image"
    curl -l https://pulp03.lab.lightbitslabs.com/pulp/content/ubuntu-24.04-initiator/qcow2/latest/ubuntu-24.04-initiator.qcow2 -o /tmp/ubuntu-24.04-initiator.qcow2
    cloudsmith push raw lightbits/lbprox /tmp/ubuntu-24.04-initiator.qcow2 \
        --version=${APP_VERSION} \
        --summary="qcow2 image of ubuntu-24.04 ubuntu-24.04-initiator.qcow2" \
        --description="qcow2 image of ubuntu-24.04 ubuntu-24.04-initiator.qcow2" \
        --content-type="application/octet-stream" \
	--tags="release-${APP_VERSION}"
    rm -rf /tmp/ubuntu-24.04-initiator.qcow2
}

function main() {
    if [ "$#" -lt 1 ]; then
        echo "Usage: $0 {lb_images|upload_os_qcow_images} [SRC_IMAGE_REGISTRY] [DST_IMG_REGISTRY]"
        exit 1
    fi
    COMMAND=$1
    if [ "$COMMAND" == "upload_os_qcow_images" ]; then
        if [ "$#" -ne 1 ]; then
            echo "Usage: $0 upload_os_qcow_images"
            exit 1
        fi
    elif [ "$COMMAND" == "lb_images" ]; then
        if [ "$#" -lt 3 ]; then
            echo "Usage: $0 lb_images SRC_IMAGE_REGISTRY DST_IMG_REGISTRY"
            exit 1
        fi
        SRC_IMAGE_REGISTRY=${2:-$DEFAULT_SRC_IMAGE_REGISTRY}
        DST_IMG_REGISTRY=${3:-$DEFAULT_DST_IMG_REGISTRY}
    fi

    case $COMMAND in
        upload_os_qcow_images) upload_os_qcow_images ;;
        lb_images) lb_images ;;
        *) echo "Invalid command"; exit 1 ;;
    esac
}

main "$@"
