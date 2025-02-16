IMAGE_REGISTRY:=$(or $(IMAGE_REGISTRY),lbdocker:5000)

override GIT_VER := $(or $(shell git describe --tags --abbrev=8 --always --long --dirty),UNKNOWN)
override GIT_TAG := $(or $(shell git describe --tags),UNKNOWN)
override IMG_TAG := $(or $(IMG_TAG),$(GIT_VER))
IMG := $(IMAGE_REGISTRY)/lbprox:$(IMG_TAG)

override BUILD_HOST := $(or $(BUILD_HOST),$(shell hostname))
override BUILD_TIME := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
override WORKFLOW_ID := $(or $(WORKFLOW_ID),"UNKNOWN")


override LABELS := \
        --label org.opencontainers.image.title="lbprox" \
        --label org.opencontainers.image.version="$(IMG_TAG)" \
        --label org.opencontainers.image.description="command-line tools for managing VMs and running Lightbits cluster on Proxmox" \
        --label org.opencontainers.image.authors="Lightbits Labs <support@lightbitslabs.com>" \
        --label org.opencontainers.image.documentation="https://www.lightbitslabs.com/support/" \
        --label org.opencontainers.image.revision=$(GIT_VER) \
        --label org.opencontainers.image.created=$(BUILD_TIME)

TTY=$(if $(shell [ -t 0 ] && echo 1),-it, )
Q := $(if $(V), ,@)


##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
# More info on the usage of ANSI control characters for terminal formatting:
# https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters
# More info on the awk command:
# http://linuxcommand.org/lc3_adv_awk.php

help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)


build-image: ## Build image
	$(Q)docker build $(LABELS) -t $(IMG) .

push-image:  ## push image to registry
	$(Q)docker push $(IMG)

docker-cmd := docker run --rm --privileged $(TTY) \
	--net=host \
	-v $(HOME)/.local/lbprox:$(HOME)/.local/lbprox \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-e UID=$(shell id -u) \
	-e GID=$(shell id -g) \
	-e UNAME=$(shell whoami) \
	-e DOCKER_GID=$(shell getent group docker | cut -d: -f3) \
	-e TZ=$(TZ) \
	--cap-add=ALL \
	-h $(BUILD_HOST) \
	$(IMG) $(CMD)

local-lbprox: ## Run lbprox cmd
	$(Q)mkdir -p $(HOME)/.local/lbprox

docker-run: local-lbprox ## Run lbprox cmd
	$(Q)${docker-cmd} lbprox $(ARGS)

docker-enter: local-lbprox ## Enter image-builder shell.
	$(Q)${docker-cmd} bash

pylint:
	$(Q)pylint lbprox
