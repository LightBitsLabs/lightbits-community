# Lightbits Cluster Provisioning

- [Lightbits Cluster Provisioning](#lightbits-cluster-provisioning)
  - [Overview](#overview)
  - [Current Virtual Environments](#current-virtual-environments)
  - [Future Environments](#future-environments)

## Overview

This repository contains many ways to deploy Lightbits cluster in virtualized environments.

Sometimes people just want to try Lightbits software to see how it works, what it can do.

Performant cluster requires bare-metal deployment with many resources that may not be available for customers
that just want to play with the system, try installation, upgrade, working against the API, etc...

## Current Virtual Environments

1. [All-In-One Vagrant deployment using libvirt provider.](./vagrant/README.md)

## Future Environments

1. Lightbits on kubernetes using Kube-Virt.
2. Lightbits on Openstack.
3. Lightbits on VMWare.
4. Lightbits on oVirt.


# Disclaimers and Limitations of Liability

THIS REPOSITORY IS NOT FOR PRODUCTION USE AND SERVES ONLY AS A REFERENCE FOR DEPLOYING LIGHTBITS' CLUSTERS AND CONFIGURATION FOR PROOF OF CONCEPT PURPOSES ONLY. THIS REPOSITORY IS PROVIDED BY LIGHTBITS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL LIGHTBITS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, LOSS AND/OR CORRUPTION OF DATA, LOST PROFITS, OR BUSINESS INTERRUPTION) OR ANY OTHER LOSS HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS REPOSITORY, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. DO NOT PLACE VALUABLE DATA ON THIS PROVISIONAL CLUSTER WITHOUT PRIOR BACKUP.
