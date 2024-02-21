# SOCA Initialization

- [SOCA Initialization](#soca-initialization)
  - [Set up work directory](#set-up-work-directory)
  - [Grid Initialization](#grid-initialization)
  - [Background Error Initialization](#background-error-initialization)
    - [Generating Lengthscales](#generating-lengthscales)
    - [EXPLICIT\_DIFFUSION Calibration](#explicit_diffusion-calibration)
    - [BUMP\_NICAS Calibration](#bump_nicas-calibration)
  - [Dirac Test (optional)](#dirac-test-optional)
    - [Identity static B](#identity-static-b)
    - [Enabling Diffusion Operator](#enabling-diffusion-operator)
    - [Enabling Standard Deviation](#enabling-standard-deviation)
    - [Enabling vertical balance](#enabling-vertical-balance)

These are tasks that are usually run a single time whenever setting up a new experiment and/or a new grid. They are not run every cycle.

## Set up work directory

The following tutorial assumes you have already set up your environment, compiled soca, and downloaded the tutorial input data. ([See previous section](../README.md))

> [!IMPORTANT]
> Within your main `soca-tutorial` directory perform the following actions to create the directories and link in the required files:
>
> ```bash
> mkdir -p tutorial/init
> cd tutorial/init
> ln -s ../../input_data/* .
> cp ../../init/files/* .
> ln -s <PATH_TO_SOCA_BUILD_DIR>/bin/soca_{gridgen,error_covariance_toolbox}.x .
> ```

## Grid Initialization

When using a new model domain for the first time `soca_gridgen.x` will need to be run to create all of the static grid-specific variables that are needed for the other executables. We do this so that the subsequent soca executables will not need to load in all the MOM6 input files that are needed to fully initialize MOM6 and its grid, saving time. For this tutorial, a 1 deg MOM6 grid (`soca_gridspec.nc`) has already been prepared in the binary files you downloaded. Instructions for running `soca_gridgen.x` will be provided under Advanced Topics so you can run SOCA with your own domains. You can use `ncview` to examine the variables present in `soca_gridspec.nc`:

| soca_gridspec: mask2d | soca_gridspec: distance_from_coast |
|:--:|:--:|
| ![gridspec mask](img/gridspec_mask.png) | ![gridspec distance to coast](img/gridspec_coastdist.png) |

## Background Error Initialization

The background error covariance is modelled by a series of generic "saber blocks" and SOCA-specific "linear variable changes". For SOCA this takes the form of

$$ \mathbf{B}=\mathbf{K}\space\mathbf{\Sigma}\space\mathbf{C}\space\mathbf{\Sigma}\space\mathbf{K}^T$$

Where

- $\mathbf{K}$ is the multivariate balance operator connecting temperature, salinity, and sea-surface height (and maybe someday U and V)
- $\mathbf{\Sigma}$ is the diagonal of the background error (i.e. the background error standard deviation)
- $\mathbf{C}$ is the spatial correlation operator

The background error used in the 3DVAR and 3DEnVAR, as well as the localization used in the 3DEnVAR will require the spatial correlation operator ($\mathbf{C}$) to be initialized ("calibrated") before it is used. This is often a slow process, so it is done once before doing any cycling experiments. There are two options for "saber central blocks" that provide a spatial correlation operator:

- `BUMP_NICAS` This lives in the `SABER` repository and is a generic operator that works for any of the model interfaces. Given the way it works, it is best suited for cases where the correlation lengths are much larger than the grid cells. Documentation can be found [here](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/saber/BUMP_saber_blocks.html#bump-nicas-saber-block).
- `EXPLICIT_DIFFUSION` This (for now) is a SOCA specific saber central block (but will be moved into the SABER repository in the near future). It implements the (explicit equation) Weaver et al. style of a normalized diffusion operator. Since it is explicitly timestepped, it works best for short correlation lengths, compared with the size of a grid cell. The person who wrote this code has been too lazy to write documentation (yet).
  
For this tutorial, and for any other case where the longest correlation length is no more than an order of magnitude larger than the grid size, `EXPLICIT_DIFFUSION` should be your choice.
  
### Generating Lengthscales

The first step in calibrating the correlation operator is to generate the desired correlation lengths. An example Python script has been provided for this purpose (`calc_scales.py`) which will generate horizontal correlation lengths as a function of the Rossby radius and vertical correlation lengths as a function of the mixed layer depth. The Rossby radius has already been computed and is stored in `soca_gridspec.nc`, the mixed layer depth is given by the initial condition file.

> [!IMPORTANT]
> Run the script to generate the length scales:
>
> ```bash
> ./calc_scales.py diffusion_setscales.yaml
> ```

You can look at the resulting `scales.nc` file. You can notice that the vertical scales are deeper in the southern hemisphere, and shallow in the Northern hemisphere, which is appropriate for the date of the initial conditions (Aug 1).

| hz scales (0-300km) | vt scales (0-50 lvls) |
| :--: | :--: |
| ![horizontal scales](img/scales_hz.png) | ![vertical scales](img/scales_vt.png) |

If you open the configuration file, `diffusion_setscales.yaml`, you'll notice the parameters that are used to calculate the lengths. One key thing to notice is that the scales have a maximum imposed to keep the lengths from being too long. Remember, the explicit diffusion operator is most efficient with short scales (BUMP_NICAS is most efficient with long scales).

### EXPLICIT_DIFFUSION Calibration

The explicit diffusion operator follows Weaver et al. and is implemented as a separable horizontal 2D and vertical 1D pair of diffusion operators.

$$ \mathbf{C}=\Gamma_v\Gamma_h\mathbf{C}_v^\frac{1}{2}\mathbf{C}_h^\frac{1}{2}\mathbf{C}_h^\frac{T}{2}\mathbf{C}_v^\frac{T}{2}\Gamma_h\Gamma_v $$

Where

- $\mathbf{C}_v$ is the vertical diffusion operator
- $\mathbf{C}_h$ is the horizontal diffusion operator
- $\Gamma_v$ is the vertical normalization weights
- $\Gamma_h$ is the horizontal normalization weights

The operator is split in this way so that the calculation of the horizontal diffusion normalization weights (which is slow) only has to be done once, whereas the vertical diffusion normalization weights (which are a lot faster) can be calculated every cycle if desired to respond to the changing mixed layer depths of the background.

Open the configuration file, `diffusion_parameters.yaml`, to see the structure of the yaml file. You'll notice that the vertical and horizontal parameters are specified and calculated separately as two distinct `group` items, and they use the scales that were generated in the previous step.

> [!IMPORTANT]
>  Run the diffusion operator calibration, replace `-n 10` with the actual number of cores you have available:
>
> ```bash
> mpirun -n 10 ./soca_error_covariance_toolbox.x diffusion_parameters.yaml
> ```

For each group, the log file will display some important information. One important thing to note is how many iterations of the diffusion operator will be required. This is a function of the length scale and grid size, and the number of iterations required will be kept large enough in order to keep the system stable.

In our case here, the horizontal operator shows:

```yaml
minimum iterations:   140 
```

And the vertical operator shows:

```yaml
minimum iterations:   200
```

For real world scenarios you probably want to make sure that the number of iterations stays below 200 or 300 for the horizontal operator, otherwise your DA will start going slower. You can get away with more iterations in the vertical operator without noticing as much performance penalty because no MPI communication is required for the vertical diffusion operator. MPI communication IS required for each iteration of the horizontal diffusion operator.

One important task of the calibration step is to calculate the normalization weights. In order to do this in an efficient manner, a randomization technique is used to estimate the weights for the horizontal operator. A random vector is created, the diffusion operator is applied, and a running variance calculation is maintained to keep track of the estimated weights. You can see in the output file, `diffusion_hz.nc` that the weights are quite noisy with only 100 iterations.

> [!IMPORTANT]
> Open the `diffusion_parameters.yaml` configuration file, increase the randomization iterations to 20,000, and re-run the calibration step.

You'll notice that calibration takes quite a bit longer now, but the resulting normalization weights are a lot smoother.

| randomization iterations: 100  | randomization iterations: 20,000|
| :--: | :--: |
| ![randomization_100](img/hz_norm_100.png) | ![randomization_10000](img/hz_norm_10000.png) |

### BUMP_NICAS Calibration

For length scales that are significantly longer than the grid cell size, it is better to use `BUMP_NICAS`. A tutorial section for this will be added in the future, but for now, if you're interested, you can look at the extensive [BUMP_NICAS documentation](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/saber/BUMP_saber_blocks.html#bump-nicas-saber-block).
  
## Dirac Test (optional)

The following steps are not needed for running subsequent data assimilation cycles, but they are useful for illustrating what is happening with the background error covariance. The `soca_error_covariance_toolbox.x` executable can also be used to run a dirac test, whereby a single unit increment is created and the background error covariance is applied once. This allows us to see how the background error covariance is performing.

> [!IMPORTANT]
> Run the dirac test:
>
> ```bash
> mpirun -n 10 ./soca_error_covariance_toolbox.x dirac.yaml
> ```
>
> and look at the `ocn.dirac_diffusion_SABER.an.2022-02-15T12:00:00Z.nc` output file.

### Identity static B

The `dirac.yaml` configuration file starts off with an identity static B enabled.

```yaml
background error:
  covariance model: SABER
  saber central block:
    saber block name: ID
```

If you look at the output, and squint, you'll see grid cells with a value of 1.0, two for the T field, and one for the SSH field, corresponding to the x/y locations specified in the configuration file. Since our static B is identity, these increments are not spread out horizontally, vertically, or across variables. Boring.

| Identity: T | Identity: SSH |
| :--: | :--: |
| ![identity dirac, T](img/dirac_step0_t.png) | ![identity dirac, SSH](img/dirac_step0_ssh.png) |

### Enabling Diffusion Operator

The first step is to enable the spatial correlation operator, here we'll enable the explicit diffusion that we already initialized.

> [!IMPORTANT]
> modify `dirac.yaml` and uncomment the following section, then rerun `soca_error_covariance_toolbox.x`

```yaml
background error:
  covariance model: SABER
  saber central block:
    saber block name: EXPLICIT_DIFFUSION
    active variables: [tocn, socn, ssh]
    geometry: *geom
    group mapping:
    - name: group1
      variables: [tocn, socn]
    - name: group2
      variables: [ssh]
    read:
      groups:
      - name: group1
        multivariate strategy: univariate
        horizontal:
          filename: ./diffusion_hz.nc
        vertical:
          filename: ./diffusion_vt.nc
      - name: group2
        horizontal:       
          filename: ./diffusion_hz.nc
```

Now when you look at the output you'll see a nice smooth 3D correlation for the increments (you should look at the vertical component as well). The increments are normalized with a maximum that is *close* to 1.0. It is not exactly 1.0 because our normalization weight initialization was an estimate, not exact, but close enough. Notice how the temperature increment near Central America "diffuses" along the coastline and does not cross it.

| with diffusion: T | with diffusion: SSH |
| :--: | :--: |
| ![with diffusion, T](img/dirac_step1_t.png) | ![with diffusion, SSH](img/dirac_step1_ssh.png) |

In the configuration file, `ssh` is in a separate group than the other variables. Usually `ssh` is defined with a correlation length that is a little larger than the other variables.

> [!TIP]
> (optional) Run another horizontal calibration with a larger scale, and use that file for `ssh` and see the difference in the dirac test

### Enabling Standard Deviation

An important part of the background error covariance is the diagonal, i.e. the standard deviation of the error. There are two ways to enable this:

- The `StdDev` SABER outer block (not covered here) that reads the standard deviations from a file.
- The SOCA specific `BkgErrGODAS` variable change. This will (eventually) be generalized, and moved to the SABER repo as a SABER outer block.

The `BkgErrGODAS` variable change calculates the diagonal of the background error parametrically based on the background temperature. (Travis, insert more details and plots on how this is calculated) In short, the errors are assumed to be the largest along the thermocline, where the `dT/dz` is the largest, and decreases with depth. At the surface, minimum temperature errors are precalculated and read in from a file. The salinity errors are assumed to be large in the mixed layer, and decrease with depth. For example, temperature errors will be something like the following.

| T stddev at lvl 0 | T stddev at lvl 35 |
| :--: | :--: |
| ![T stddev lvl 0](img/bkg_err_t_lvl0.png) | ![plus stddev, SSH](img/bkg_err_t_lvl35.png) |

> [!IMPORTANT]
> Modify `dirac.yaml` and uncomment the following `BkgErrGODAS` block, rerun the `soca_error_covariance_toolbox.x`, and look at the output.

```yaml
linear variable change:
  input variables: *soca_vars
  output variables: *soca_vars
  linear variable changes:

  - linear variable change name: BkgErrGODAS
    sst_bgerr_file: ./godas_sst_bgerr.nc
    t_min: 0.1
    t_max: 2.0
    t_dz:  20.0
    t_efold: 500.0
    s_min: 0.0
    s_max: 0.25
    ssh_min: 0.0   # value at EQ
    ssh_max: 0.1   # value in Extratropics
    ssh_phi_ex: 20 # lat of transition from extratropics
```

The magnitude of the increments now vary spatially. Note that these are the standard deviations for the "unbalanced" S and SSH (see next section)

| plus stddev: T | plus stddev: SSH |
| :--: | :--: |
| ![plus stddev, T](img/dirac_step2_t.png) | ![plus stddev, SSH](img/dirac_step2_ssh.png) |

### Enabling vertical balance

The multivariate balances follow Weaver et al. 2006, and convert T/S/SSH into T and "unbalanced" S and SSH (read the paper).

$$ \mathbf{K} = \begin{bmatrix} I & 0 & 0 & 0 \\
                                K_{ST} & I & 0 & 0 \\
                                K_{\eta T} & K_{\eta S} & I & 0 \\
                                K_{cT} & 0 & 0 & I
                 \end{bmatrix}$$

The main balance we'll show here is the one connecting SSH with the density in the column, this is important for being able to assimilate altimetry observations.

$$ \delta \eta_B = - \int^0_{bottom}{\frac{\delta\rho(T,S,z)}{\rho_0}dz}$$

> [!IMPORTANT]
> Modify `dirac.yaml` and uncomment the following `BalanceSOCA` block, rerun the `soca_error_covariance_toolbox.x`, and look at the output.

```yaml
- linear variable change name: BalanceSOCA
  ksshts:
    nlayers: 2
```

Enable the `ksshts` section of `BalanceSOCA` and you will then see that the T/S/SSH fields (S is not shown here) are all connected now. Now, a positive SSH increment is associated with a positive T increment, as one would physically expect.

| plus ssh balance: T | plus ssh balance: SSH |
| :--: | :--: |
| ![](img/dirac_step3_t.png) | ![](img/dirac_step3_ssh.png) |

The `kst` section should be left commented out. There are issues with it working correctly and we need to take a closer look at it. The T/S balance is important in the tropics where there there is a well defined thermocline. It doesn't work so well elsewhere.

> [!TIP]
> You probabably don't want to use the T/S balance (yet) in real uses, but you can go ahead and enable the T/S balance here, re-run the dirac test, and look at the results.

---
[Prev: Compiling](../README.md) | [Next: 3DVAR](../3dvar/README.md)