# soca-tutorial

- [soca-tutorial](#soca-tutorial)
  - [Setting up Environment](#setting-up-environment)
  - [Downloading and Compiling](#downloading-and-compiling)
    - [Setting up git LFS](#setting-up-git-lfs)
    - [Downloading](#downloading)
    - [Compiling](#compiling)
    - [Testing](#testing)
  - [Tutorial Experiments](#tutorial-experiments)

>[!CAUTION]
> This tutorial is still a work in progress. When done, it will be transferred to the official JCSDA repos.

>[!CAUTION]
> <!--  TODO - change when released -->
> NOTE that this a `develop` version of the tutorial that is meant to be used
> with a non-release version of the JEDI bundle from Travis'
> personal fork on github, [travissluka/jedi-bundle:
> release/soca](https://github.com/travissluka/jedi-bundle/tree/release/soca).
> The rest of the documentation has not been reflected to show this. Check with
> Travis that you are using the right version of things!

The Sea-ice, Ocean, and Coupled Assimilation interface (SOCA) is the MOM6 interface to JEDI. In addition to ocean, any variables that are on the MOM6 grid can be handled (sea-ice, biogeochemistry, etc.)

This tutorial will help users to setup an environment on a supported machine, compile SOCA, and run a single cycle of various DA methods using provided scripts. It is up to the user to setup their own model configuration, and HPC cycling script, for their own experiments. It is also assumed that the user has a working knowledge of data assimilation, as high level explanations of the various DA methods are omitted.

The two primary sources of additional documentation are updated quarterly with every release of JEDI, the latest releases are here:

- [JEDI read-the-docs v8](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/8.0.0/)
- [spack-stack v1.7.0](https://spack-stack.readthedocs.io/en/1.7.0/index.html)

## Setting up Environment

The build environment is handled by `spack-stack`, which contains all the libraries needed to compile JEDI and UFS code. Fortunately, on the main HPCs that we use, `spack-stack` has already been compiled and is available as a set of modules.

Load the environment for your given HPC per the [spack-stack hpc module instructions](https://spack-stack.readthedocs.io/en/1.7.0/PreConfiguredSites.html#pre-configured-sites-tier-1).

For example, for the GNU compiler on Orion, you would run the following

```bash
module purge
module use /work/noaa/epic/role-epic/spack-stack/orion/modulefiles
module load ecflow/5.8.4

module use /work/noaa/epic/role-epic/spack-stack/orion/spack-stack-1.7.0/envs/ue-gcc/install/modulefiles/Core
module load stack-gcc/12.2.0
module load stack-openmpi/4.1.6
module load stack-python/3.10.13
```

You'll then load the modules specific for the SOCA environment

```bash
module load soca-env
module load fms
module load sp
## UNCOMMENT next two lines for orion:
#module unload git-lfs
#module load git-lfs/3.1.2
```

last, depending on which machine you're on, you'll probably require the following commands

```bash
export OMP_NUM_THREADS=1
ulimit -s unlimited
```

You probably want to have a bash script do the above for you so that so you don't have to type it every time you want to compile or run SOCA.

## Downloading and Compiling

### Setting up git LFS

Some of the binary test files require git LFS. If this is your first time using git LFS you'll want to run the following command:

```bash
git lfs install
```

This only needs to be done once on any given machine. Double check in your home directory that you have a file `~/.gitconfig` that contains an `lfs` section, such as

```Git Config
[filter "lfs"]
clean = git-lfs clean -- %f
smudge = git-lfs smudge -- %f
process = git-lfs filter-process
required = true
```

### Downloading

Each quarter, all of the individual JEDI repositories are tagged and tested, and a demonstration run (called [Skylab](https://skylab.jcsda.org) ) is performed. These stable tagged versions are available from the [jedi-bundle](https://github.com/JCSDA/jedi-bundle) repository.

> [!WARNING]
> The following instructions will use the latest tagged Skylab release to ensure the source code and environment are guaranteed to be working together. You can also build from the latest `develop` branches available on GitHub, but it is advised not to do this unless you are developing SOCA/JEDI code or for some reason need the latest version and can't wait for the next quarterly release.

Get the latest release of the public JEDI bundle:

```bash
git clone https://github.com/JCSDA/jedi-bundle -b release/skylab-v8
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

Be sure to check the JEDI documentation for any specific compilation instructions for your machine. For example, some HPCs have memory limits on the login nodes that interfere with compiling, so it is suggested to [grab a compute node](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/8.0.0/using/running_skylab/HPC_users_guide.html) on those machines for compiling.

You'll want to `cd` into the soca build directory, otherwise a lot of other executables
that soca doesn't need will get build (e.g. OOPS toy models and tests)

> [!WARNING]
> There is currently a bug in the cmake for SOCA where `mom6.x` is not getting
> detected as a dependency and so is not build automatically when you build
> after `cd` into the `soca` directory. `mom6.x` is needed for the ctests to
> run. Either run `make` from the root of the build directory so that everything
> gets built, or also `cd` into the `mom6` directory and run `make` there.

```bash
cd soca
make -j 5
```

### Testing

Assuming SOCA compiled correctly, you should be able to run the ctests, which are simple tests using a 5 degree ocean grid. See the notes [here](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/8.0.0/using/running_skylab/HPC_users_guide.html) about obtaining a compute node before running the tests. Assuming you are within the `build/soca` directory, running `ctest` will only run the tests for SOCA (there are hundreds of other tests for the other JEDI components that you probably don't care about)

If for some reason a test fails, you can rerun a given test and view the output with `ctest -R <test name> -V`.

If for some reason ALL of the tests fail, it's possible that the data files were not downloaded correctly with git lfs, double check to make sure git lfs was setup correctly. (Look at the netCDF files in `./soca/test/Data/` they should be actual netCDF files, not tet files describing which data file git lfs should download.)

## Tutorial Experiments

The files need for a single cycle of several DA methods are provided (observations, background, static files, and yaml configurations). To get the binary data, download the input data from our [Google drive here](https://drive.google.com/uc?export=download&id=15dpIwXWXU72hYQy-wGLuYnrVB-J0eIb4) . Unpack the file with the following command and you should now have a `soca-tutorial/input_data` directory.

```bash
tar -xaf soca-tutorial.input_data.tgz
```

The SOCA tutorial proceeds in several steps:

1. [SOCA initialization](init/README.md)
2. [HofX and 3DVAR](3dvar/README.md)
3. [3DEnVAR](3denvar/README.md)
4. [LETKF](letkf/README.md) (🚧 documentation still being developed)
5. [Advanced Topics](advanced/README.md) (🚧 documentation still being developed)

Afterward you should know everything you need to know to develop you own cycling experiment scripts to suit your own needs. The tutorials do assumme you already have a working knowledge of variational and ensemble DA methods. General DA background information may be added at a later date.

Be sure to pay special attention to any sections in special colors:

> [!IMPORTANT]
> These purple sections of the tutorial require action on your part, be sure to do them in order!

> [!TIP]
> These green sections are optional actions on your part, you can skip them if you want
