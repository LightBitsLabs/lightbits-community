VERSION=v0.1.0
IMAGE_REPOSITORY=lbdocker:5000
IMG=$(IMAGE_REPOSITORY)/lbprox:$(VERSION)

override BUILD_HOST := $(or $(BUILD_HOST),$(shell hostname))

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


build-image:
	$(Q)docker build -t $(IMG) .

push-image:
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

docker-run: ## Run lbprox cmd
	$(Q)mkdir -p $(HOME)/.local/lbprox
	$(Q)${docker-cmd} lbprox $(ARGS)

docker-enter: ## Enter image-builder shell.
	$(Q)mkdir -p $(HOME)/.local/lbprox
	$(Q)${docker-cmd} bash

pylint:
	$(Q)pylint lbprox
