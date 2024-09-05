VERSION=v0.1.0
IMAGE_REPOSITORY=lbdocker:5000
IMG=$(IMAGE_REPOSITORY)/lbprox:$(VERSION)

Q := $(if $(V), ,@)

build-image:
	$(Q)docker build -t $(IMG) .

push-image:
	$(Q)docker push $(IMG)

run:
	$(Q)mkdir -p $(HOME)/.local/lbprox
	$(Q)docker run -it --rm --net=host \
		-v $(HOME)/.local/lbprox:$(HOME)/.local/lbprox \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e UID=$(shell id -u) \
		-e GID=$(shell id -g) \
		-e UNAME=$(shell whoami) \
		-e DOCKER_GID=$(shell getent group docker | cut -d: -f3) \
		-e TZ=$(TZ) \
		--cap-add=ALL \
		$(IMG) lbprox $(ARGS)

pylint:
	$(Q)pylint lbprox
