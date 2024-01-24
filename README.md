# soca-tutorial

> ❗This tutorial is still a work in progress. When done, it will be transfered to the official JCSDA repos.
> 
The Sea-ice, Ocean, and Coupled Assimilation interface (SOCA) is the MOM6 interface to JEDI. In addition to ocean, any variables that are on the MOM6 grid can be handled (sea-ice, biogeochemistry, etc.)


Table of Contents
- [soca-tutorial](#soca-tutorial)
  - [Intro](#intro)
  - [Seting up Environment](#seting-up-environment)
  - [Downloading and Compiling](#downloading-and-compiling)
    - [Setting up git LFS](#setting-up-git-lfs)
    - [Downloading](#downloading)
    - [Compiling](#compiling)
    - [Testing](#testing)
  - [Tutorial Experiments](#tutorial-experiments)
  
## Intro
This tutorial will help users to setup an environment on a supported machine, compile SOCA, and run a single cycle of various DA methods using provided scripts. It is up to the user to setup their own model conifguration, and HPC cycling script, for their own experiments.

The two primary sources of additional documentation are updated quarterly with every release of JEDI, the latest releases are here:
- [JEDI read-the-docs v7](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/7.0.0/)
- [spack-stack v1.5.1](https://spack-stack.readthedocs.io/en/1.5.1/index.html)


## Seting up Environment
The build environment is handled by `spack-stack`, which contains all the libraries needed to compile JEDI and UFS code. Fortunately, on the main HPCs that we use, `spack-stack` has already been compiled and is available as a set of modules.

Load the environment for your given HPC per the [spack-stack hpc module instructions](https://spack-stack.readthedocs.io/en/1.5.1/PreConfiguredSites.html#pre-configured-sites-tier-1).

For example, for the GNU compiler on Orion, you would run the following
```bash
module purge
module use /work/noaa/epic/role-epic/spack-stack/orion/modulefiles
module load python/3.9.2
module load ecflow/5.8.4
module load mysql/8.0.31

module use /work/noaa/epic/role-epic/spack-stack/orion/spack-stack-1.5.1/envs/unified-env/install/modulefiles/Core
module load stack-gcc/10.2.0
module load stack-openmpi/4.0.4
module load stack-python/3.10.8
```

You'll then load the modules specific for the SOCA environment

```bash
module load soca-env
module load fms/release-jcsda
```

You probably want to have a bash script do the above for you so that so you don't have to type it every time you want to compile or run SOCA.

## Downloading and Compiling

### Setting up git LFS
Some of the binary test files require git LFS. If this is your first time using git LFS you'll want to run the following command:
```bash
git lfs install
```
This only needs to be done once on any given machine. Double check in your home directory that you have a file ` ~/.gitconfig` that contains an `lfs` section, such as 
```
[filter "lfs"]  
clean = git-lfs clean -- %f  
smudge = git-lfs smudge -- %f  
process = git-lfs filter-process  
required = true
```

### Downloading
Once a quarter all of the individual JEDI repositories are tagged and tested, and a demonstration run (called [Skylab ](https://skylab.jcsda.org) ) is performed. These stable tagged versions are available from the [jedi-bundle](https://github.com/JCSDA/jedi-bundle) repository.

> ❗ The following instructions will use the latest tagged Skylab release to ensure the source code and environment are guaranteed to be working together. You can also build from the latest `develop` branches available on GitHub, but it is advised not to do this unless you are developing SOCA/JEDI code or for some reason need the latest version and can't wait for the next quarterly release.

Get the latest release of the public JEDI bundle:

```bash
git clone https://github.com/JCSDA/jedi-bundle -b release/skylab-v7
```

This bundle will pull the individual repositories for everything JEDI related. Since you only want to use SOCA, you can comment a couple of things out to make everything compile faster. You'll see a `CMakeLists.txt` file, and in that file near the end are several `ecbuild_bundle( PROJECT ...` lines, comment out the ones that we don't need for SOCA:
- `crtm`
- `fv3`
- `femps`
- `fv3-jedi-lm`
- `fv3-jedi`
- `mpas`
- `mpas-jedi`
- `coupling`

Run `ecbuild` to get all the required repositories and prepare to compile:
```bash
mkdir build
cd build
ecbuild ../
```

Hopefully there were no errors at this point. If there are, it's possible that the environment was not setup correctly.


### Compiling
Be sure to check the JEDI documentation for any specific compilation instructions for your machine. For example, some HPCs have memory limits on the login nodes that interfere with compiling, so it is suggested to [grab a compute node](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/7.0.0/using/running_skylab/HPC_users_guide.html) on those machines for compiling.

You'll want to `cd` into the soca build directory, otherwise a lot of other executables that soca doesn't need will get build (e.g. OOPS toy models and tests)
```bash
cd soca
make -j 5
```

### Testing

Assuming SOCA compiled correctly, you should be able to run the ctests, which are simple tests using a 5 degree ocean grid. See the notes [here](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/7.0.0/using/running_skylab/HPC_users_guide.html) about obtaining a compute node before running the tests. Assuming you are within the `build/soca` directory, running `ctest` will only run the tests for SOCA (there are hundreds of other tests for the other JEDI components that you probably don't care about)

## Tutorial Experiments
The files need for a single cycle of several DA methods are provided (observations, background, static files, and yaml configurations). See each section for more detail.
1. [3DVAR](3dvar/README.md) (🚧 documentation still being developed)
2. [3DEnVAR](letkf/README.md) (🚧 documentation still being developed)
3. [LETKF](letkf/README.md) (🚧 documentation still being developed)
