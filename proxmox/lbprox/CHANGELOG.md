# CHANGELOG


## v0.1.0 (2025-02-16)


## v0.1.0-rc.1 (2025-02-16)

### Bug Fixes

- Enable paramiko to ssh to machines without adding them to known_hosts
  ([`8293bb1`](https://github.com/LightBitsLabs/lightbits-community/commit/8293bb139e061d05456511d693a00079cbdd3a2a))

till now we needed to ssh into the machine and type yes interactivly and if we didn't it would halt
  the process.

now we don't need to since it will skip the missing entry in host_key verification.

- Flavors.yml - update dms server to include both data and access nics
  ([`bff5178`](https://github.com/LightBitsLabs/lightbits-community/commit/bff517870e208772092d5af795af5e38cdcf03d0))

- Set min os vol size to 15G and resize if vol is smaller
  ([`980bf9b`](https://github.com/LightBitsLabs/lightbits-community/commit/980bf9b5e28bfaf167142123ee79fa432e473203))

some of our images are minified to 4G and it makes the OS very limited on size.

This change will make sure the min image size is at least 15G.

- Set uid+gid+uname for lb install compose
  ([`cc5cb8a`](https://github.com/LightBitsLabs/lightbits-community/commit/cc5cb8a1d53501d767d825e3eafd721ea57b8aa2))

- **lbprox**: Define WORKSPACE_TOP env-var in container
  ([`56c6360`](https://github.com/LightBitsLabs/lightbits-community/commit/56c63605f2932b34ac9972a4b3e6323991a7875b))

we need to lookup light-app path which is relative to the WORKSPACE_TOP in the past if we didn't
  find it we would have silently failed to run the deploy container. but now we will fail with an
  obvious error.

- **lbprox**: Dockerfile - bind-mount docker.sock
  ([`40a75ac`](https://github.com/LightBitsLabs/lightbits-community/commit/40a75acaf34e801cc866abf3a4fd037b2e8507c6))

### Chores

- Quite chpasswd output
  ([`26fd65f`](https://github.com/LightBitsLabs/lightbits-community/commit/26fd65ff9f6f959a6da792fe8eb4cc07cb644049))

- Update image version to user git-describe
  ([`256d5d4`](https://github.com/LightBitsLabs/lightbits-community/commit/256d5d415aa4c85c3307a5be0f7060c4794dd0bd))

- Update version in setup.py
  ([`3309882`](https://github.com/LightBitsLabs/lightbits-community/commit/33098823bdf827f426572a7deb1886fa80f0b446))

- **flavors**: Change flavor.yaml embedded struct syntax.
  ([`cbbfeb6`](https://github.com/LightBitsLabs/lightbits-community/commit/cbbfeb649162733feadf8bbbef898605e1013588))

### Features

- Add user, pass to config file
  ([`e5ef80d`](https://github.com/LightBitsLabs/lightbits-community/commit/e5ef80d63369be0dc8bcb5bddc98057e33d7a010))

- **lbprox**: Add dms and large emulated ssd flavors and new cluster setups
  ([`6ead73c`](https://github.com/LightBitsLabs/lightbits-community/commit/6ead73c47acbe881284bd24be04c51f40f819d0a))

- **lbprox**: Add docker-compose file for easy running in container
  ([`d767f0a`](https://github.com/LightBitsLabs/lightbits-community/commit/d767f0a939bba4c8dbfe9cc553fea6e5de36c9ed))

improve the way we generate the docker image. improve the docker-compose to contain lbprox and
  lbprox-bash

add instructions for adding ~/.local/bin/lbprox which is a script for launching lbprox from
  container with little effort.

- **lbprox**: Port for lb-ansible:v11.0.0
  ([`1854aae`](https://github.com/LightBitsLabs/lightbits-community/commit/1854aaea73d8cdf95cf85494a09ef1cfc972b075))

- **lbprox**: Port for lb-ansible:v9.13.0
  ([`ec6f15a`](https://github.com/LightBitsLabs/lightbits-community/commit/ec6f15ae254fc01c70372f9d24d00f13cf60372f))
