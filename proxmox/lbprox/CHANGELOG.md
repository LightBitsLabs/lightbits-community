# CHANGELOG


## v0.4.0 (2025-02-27)

### Documentation

- Document photon deployment on proxmox using lbprox
  ([`b7f82d2`](https://github.com/LightBitsLabs/lightbits-community/commit/b7f82d277fcc135f5543c76132ac8aa5973d5b55))

- Update README.md with external public os image urls
  ([`e7106b3`](https://github.com/LightBitsLabs/lightbits-community/commit/e7106b31c24968a8e9bc5fae42606090bf1b6b28))

### Features

- Add support for creating photon VM by specifing custom cloud-init data
  ([`61fd34d`](https://github.com/LightBitsLabs/lightbits-community/commit/61fd34d4c891fe64c820e067dd4ddb51cf1e04aa))

- Add support for photon vm
  ([`092884e`](https://github.com/LightBitsLabs/lightbits-community/commit/092884effc43d14c251af82ae6a9714e83401046))

- Add support for uploading tar.gz from url (like cloudsmith)
  ([`62b8501`](https://github.com/LightBitsLabs/lightbits-community/commit/62b8501fbd0aac142348221db6edc7aec8e2dc6b))

this feat will allow us to specify external URL of tar.gz the lbprox will download the file, extract
  it, look for qcow2 and if present will upload it to the node/nodes specified.

also supported --force flag to create os-images to delete an existing image and upload a new one.

by default it will not upload if the image is present on one of the nodes in the cluster.


## v0.3.0 (2025-02-19)

### Bug Fixes

- Add -s short option
  ([`97695c9`](https://github.com/LightBitsLabs/lightbits-community/commit/97695c93117b09effd64408c57e870b3349f3c51))

- Create-image should work only on one nodename - given as required arg
  ([`8400dfe`](https://github.com/LightBitsLabs/lightbits-community/commit/8400dfe684273befdc64af53ba8236074b46220d))

- Git_tag target
  ([`49fdbaa`](https://github.com/LightBitsLabs/lightbits-community/commit/49fdbaab76b2892a39a88c840c7cf4f74f76fd67))

- Propagation of user/pass from file/variable
  ([`bc55650`](https://github.com/LightBitsLabs/lightbits-community/commit/bc55650d416514f4735b4255e3f75c4e0cf73abc))

### Chores

- Add scripts/pull-tag-push.sh to deploy container-images and os-images
  ([`009f50e`](https://github.com/LightBitsLabs/lightbits-community/commit/009f50ef26d54e903477ebc0650e9173f0df7275))

- Makefile add print-* target
  ([`b0f60b7`](https://github.com/LightBitsLabs/lightbits-community/commit/b0f60b7592f97caff0b09998403a313711bef473))

- Update lb-ansible image to cloudsmith public lbprox repo
  ([`2a78791`](https://github.com/LightBitsLabs/lightbits-community/commit/2a787910fa36666400773243e4177ecfbc13a22a))

### Documentation

- Document that we need to disable dnsmasq.service
  ([`96a0f53`](https://github.com/LightBitsLabs/lightbits-community/commit/96a0f5362d90018ccf08362d2a01569db210c2a7))

- **README.md**: Hide python package installation.
  ([`f67f8b4`](https://github.com/LightBitsLabs/lightbits-community/commit/f67f8b49f39b3b1da2a8959e09e3cb989a44d616))

### Features

- Add light_app_path var to lbprox.yaml
  ([`b0c3daf`](https://github.com/LightBitsLabs/lightbits-community/commit/b0c3daf839e4855162d2d2442adaacbea2c39877))

till now we counted on WORKSPACE_TOP env var. in a world outside the lab we don't have WORKSPACE_TOP
  so the user must provide this path to the expanded light-app directory where we can find the
  ansible playbook and roles.

if not provided we will try to look for WORKSPACE_TOP/light-app if not provided we will fail with a
  clear error msg.


## v0.2.1 (2025-02-16)

### Bug Fixes

- **Makefile**: Push image with git-tag if git HEAD points to git-tag
  ([`8dc9f4e`](https://github.com/LightBitsLabs/lightbits-community/commit/8dc9f4e2b2b9f1d616f87184727d4dd59ad812a5))


## v0.2.0 (2025-02-16)

### Features

- Add support for python-semantic-release
  ([`7ed7561`](https://github.com/LightBitsLabs/lightbits-community/commit/7ed75613793d01704ae2622062a9ca762a5ffd87))


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
