# SOCA 3DEnVAR

- [SOCA 3DEnVAR](#soca-3denvar)
  - [Setup work directory](#setup-work-directory)
  - [Initialize BUMP\_NICAS for localization](#initialize-bump_nicas-for-localization)
  - [Ensemble Covariance](#ensemble-covariance)
    - [Dirac test](#dirac-test)
    - [3DEnVAR Run](#3denvar-run)
  - [Hybrid Covariance](#hybrid-covariance)
    - [Run dirac with hybrid covariance](#run-dirac-with-hybrid-covariance)
    - [Run 3DEnVAR with hybrid covariance](#run-3denvar-with-hybrid-covariance)
  - [4DEnVAR (information only)](#4denvar-information-only)

This section of the tutorial will cover the basics of using an ensemble for the background error covariance, both as part of a pure 3DEnVAR, and as a hybrid-3DEnVAR. Also, the changes that would be needed to run a 4DEnVAR will be discussed.

The use of an ensemble for the background error covariance can allow for more sophisticated covariances than what is possible with the parameterized static B in the 3DVAR of SOCA.

## Setup work directory

The following tutorial assumes that you have already set up your environment, compiled SOCA, and run the SOCA initialization tutorial in the [previous section](../init/README.md).

> [!IMPORTANT]
> Within your main `soca-tutorial` directory perform the following actions to create the directories and link in the required files,  including the initialized diffusion from the previous tutorials:
>
> ```bash
> mkdir -p tutorial/3denvar
> cd tutorial/3denvar
> ln -s ../../input_data/* .
> cp ../../3denvar/files/* .
> ln -s ../init/diffusion_{hz,vt}.nc .
> ln -s <PATH_TO_SOCA_BUILD_DIR>/bin/soca_{error_covariance_toolbox,var}.x .
> mkdir obs_out
> ```

## Initialize BUMP_NICAS for localization

The localization method for the 3DEnVAR, can be either `BUMP_NICAS` or
`EXPLICIT_DIFFUSION` (similar to the choice of correlation model used for the
static background error covariance). As discussed previously in the [background
error initialization](../init/README.md#background-error-initialization),
`BUMP_NICAS` is preferable when using long length scales, and
`EXPLICIT_DIFFUSION` is preferable when using short length scales. Since we
often want localization length scales to be longer than correlation length
scales, `BUMP_NICAS` is often a good choice here.

The `nicas_parameters.yaml` file has already been prepared for you. There are some differences when calibrating  NICAS for localization compared with using it for correlation. You'll notice the following setting:

```yaml
  drivers:
    multivariate strategy: duplicated
```

which tells NICAS that we will not be using any inter-variable localization (more on that in the following dirac test section). Specifying localization between variables is something that can be done with NICAS, but is outside the scope of this tutorial.

For simplicity, we are using a fixed horizontal localization length chosen to be reasonably larger than the Rossby radius. In the real world, you probably will want to use a length scale that is horizontally varying, and set to some multiple (2x?) of the Rossby radius. Unlike the choice of length scale for the correlation operator, the localization lengths can be considerably larger, how large they can be depends on how many ensemble members you have.

```yaml
nicas:
  explicit length-scales: true
  horizontal length-scale:
  - groups:
    - common
    value: 750e3 # meters
  ...
```

It is important to note that the lengths specified for NICAS are the half width of a Gaspari Cohn function, the lengths for the diffusion operator were specified as 1 sigma of a Gaussian (yes, confusing, I know!). To convert between the two:

$gaspari\_cohn= 3.57 * gaussian$

The vertical length scale (in units of number of levels), is set to a very large number, because we essentially want to disable localization in the vertical for the ocean.

```yaml
nicas:
  vertical length-scale:
  - groups:
    - common
    value: 5000 # number of levels
  ...
```

> [!IMPORTANT]
> Run the calibration for `BUMP_NICAS` localization, (this will take a while!)
>
> ```bash
> mpirun -n 10 ./soca_error_covariance_toolbox.x nicas_parameters.yaml
> ```

After running the calibration, you will see several `nicas_loc_nicas_local_...nc` files. One will be generated for each PE that was used with `mpirun`. It is important that the number of PEs used for any other application that uses NICAS (e.g. `soca_var.x`) is the same as what is used here.

Another important thing to note is the NICAS subgrid resolution. The number of subgrid points required is dynamically determined based on the length scales, and it is possible that NICAS is trying to use more points than are available. If you see the following warning, make sure `max horizontal grid size` is set sufficiently large in  your configuration file, otherwise bad things will happen. (This warning will be turned into error in the next quarterly release).

```text
Info     :                 Estimated nc1 from horizontal support radius:   106809
Warning  : in nicas_cmp_compute_horizontal: required nc1 larger than nc1max, resetting to nc1max
```

The parameters given in the configuration file for this tutorial should be fine as is.

## Ensemble Covariance

Now that the localization method has been initialized, we will look at what happens when we completely replace the parametric background error covariance used in the previous 3DVAR with an ensemble based covariance. For these examples, ocean states have been pseudo-randomly picked from the same season over a several year period of a separate analysis.

### Dirac test

To visualize what is happening with the ensemble covariance, we will use the dirac test, similar to what was done with the background error covariance in previous sections.

We will be using the `dirac.yaml` configuration file, which has already been setup for you to use. You'll notice that the `covariance model` has been set to `ensemble`. This covariance model requires two sections, 1) a list of ensemble members to read in, and 2) the localization method (which can be either `BUMP_NICAS` or `EXPLICIT_DIFFUSION`)

```yaml
  background error:
    covariance model: ensemble
    members:
    - ...
    - ...
    ...

    localization:
      localization method: SABER
      saber central block:
        saber block name: BUMP_NICAS
        ...
```

Other than the `background error`, the dirac configuration file should otherwise look the same as what was used in the previous tutorial sections.

> [!IMPORTANT]
> Run the dirac test with the ensemble covariance:
>
> ```bash
> mpirun -n 10 ./soca_error_covariance_toolbox.x dirac.yaml
> ```

Two output files will be produced. First, look at `ocn.dirac_ens_ensemble.an.2022-02-15T12:00:00Z.nc`, which are the dirac increments. You'll notice that the dirac increments look similar to what was done in previous tutorials, however, there is a bit more structure in some areas (e.g. look at the increments created for salinity, and the difference in increment structure in the vertical). Importantly, we now have a U increment, which we did not have with the parametric background error covariance model!

| ensemble dirac: T | ensemble dirac: S | ensemble dirac: U |
| :--: | :--: | :--: |
| ![ensemble dirac: T](img/dirac_ens_T.png) | ![ensemble dirac: S](img/dirac_ens_S.png) | ![ensemble dirac: U](img/dirac_ens_U.png) |

Look at the other output file, `ocn.dirac_ens_ensemble_localization.an.2022-02-15T12:00:00Z.nc`. This files shows the ensemble localization that was used to calculate the above increments.

| localization|
| :--: |
| ![localization ](img/dirac_ens_loc.png) |

You'll notice that the localization near Central America crosses from the Pacific into the Atlantic. It is possible when calibrating NICAS to enforce the use of the land mask to prevent this. However, in reality, this cross-basin impact is not as big of a concern for localization than it is for the correlation operator, so we usually skip the added cost required from imposing the land mask.

> [!TIP]
> (Optional Exercise) Try decreasing the number of ensemble members in the background error covariance to just 5 and see how the resulting diracs get noisier. This shows the importance of having a large enough ensemble to have meaningful cross-variable and spatial correlations.

> [!TIP]
> (Optional Exercise) As of Skylab v8, `EXPLICIT_DIFFUSION` can also be
> used for localization! This may be useful if you have few ensemble members and
> need localization lengths that are still close to the Rossby radius
> correlation lengths. Re-run the above the above dirac test and swap the
> `BUMP_NICAS` central block for the `EXPLICIT_DIFFUSION` central block. (look
> at what is done in the [SOCA 3dhyb
> ctest](https://github.com/JCSDA/soca/blob/develop/test/testinput/3dhyb_diffusion.yml#L110)
> for an example. Some things you'll need to add to your yaml:
>
> - **duplicated multivariate strategy**: Same concept as with `BUMP_NICAS`
>   localization is combined for the given variables.
> - **duplicated vertical strategy**: Since `EXPLICIT_DIFFUSION` does not work
>   well with long length scales, we can't just use a very large number to "turn
>   off" vertical localization (like we did with `BUMP_NICAS`). Instead we
>   specify a duplicated vertical strategy in place of actual diffusion to copy
>   the localization across the vertical levels.
>
> The above will result in a yaml that will look something like the following
> inside the `EXPLICIT_DIFFUSION` section of your localization:
>
> ```yaml
> ...
> read:
>   groups:
>   - name: group1
>     multivariate strategy: duplicated
>     horizontal:
>       filename: ./diffusion_hz.nc
>     vertical:
>       strategy: duplicated
> ```

### 3DEnVAR Run

Now we will run SOCA's 3DEnVAR, which is otherwise the same as the previous 3DVAR run except for the specifications of the background error covariance. The `3denvar.yaml` file has already been configured for you with the same ensemble background error covariance that was used in the above dirac tests.

> [!IMPORTANT]
> Run the 3DEnVAR:
>
> ```bash
> mpirun -n 10 ./soca_var.x 3denvar.yaml
> ```

Altimetry and SST observations have been enabled, but there are no direct observations of salinity. You can see in the output increment from the previous 3DVAR run that there are very small increments in salinity (these are coming from the balances involved with the altimetry observations), and there are no increments in currents (because we don't have U/V/SSH balances implemented).

The 3DEnVAR, on the other-hand, has substantial increments for salinity and the currents! The temperature increments do not look markedly different, because the SST observation coverage was dense. But now, the correlations present in the ensemble allow temperature to impact all the other state variables. You can also examine the vertical structure of the increments and see how they differ between the 3DVAR and 3DEnVAR.

| | increment: T | increment: S | increment: U |
| -- |:--: | :--: | :--: |
| 3DVAR | ![3DVAR T increment](img/3dvar_inc_T.png) | ![3DVAR S increment](img/3dvar_inc_S.png) | ![3DVAR U increment](img/3dvar_inc_U.png) |
| 3DEnVAR |![3DEnVAR T increment](img/3denvar_inc_T.png) | ![3DEnVAR S increment](img/3denvar_inc_S.png) | ![3DEnVAR U increment](img/3denvar_inc_U.png) |

The cross-variable covariance here might be a little noisy, after all, 15 ensemble members is not very many. In the real world you would want to spend more time carefully crafting your ensemble, (if you chose to use a static climatological ensemble) to make sure that the ensemble size is large enough, and that the ensemble variance and cross-variable correlations are what you would expect them to be.

With the 3DEnVAR, the ensemble members used in the background error covariance are not updated during the analysis (they're static). One way to have dynamic ensemble members is to use the [LETKF](../letkf/README.md) (presented in the next tutorial) along with ensemble forecasts. A dynamic ensemble would allow you to have more appropriate "errors-of-the-day" in your ensemble covariance compared with a static ensemble.

## Hybrid Covariance

We've seen how to use a parameterized background error covariance using balances imposed by variable changes ([3DVAR](../3dvar/README.md)), and how to use an ensemble based background error covariance (this tutorial). Now we'll see how to combine the two together.

OOPS provides the `hybrid` covariance model that can be used to combine any number of independent background error covariance models. Using it looks like the following:

```yaml
  background error:
    covariance model: hybrid
    components:
    - weight:
        value: 0.5
      covariance:
        covariance model: ensemble
        # <Copy the existing ensemble covariance settings here>
        ...
    - weight:
        value: 0.5
      covariance:
        covariance model: SABER
        # <copy the static B covariance settings from the 3DVAR>
        ...
    ...
```

For each covariance model you want to use, a fractional `weight` is provided (all weights *should* add up to 1.0, but they don't have to), along with the same type of covariance model configuration we have used previously for `SABER` NICAS/EXPLICIT_DIFFUSION or `ensemble`.

A hybrid covariance can be especially useful to help strike a balance between the problems of limited capabilities of the parametric background error covariance, and the sampling error from limited ensemble size of the ensemble covariance. Here we have a 50% / 50% weighting, but typically you would want put more weight on the ensemble covariance as your ensemble size increases.

### Run dirac with hybrid covariance

A separate yaml file for hybrid covariances has **not** been provided. Instead, use the existing `dirac.yaml`.

> [!IMPORTANT]
> Copy `dirac.yaml` to `dirac_hyb.yaml`, modify as described above to use a hybrid background error covariance, pulling the ensemble covariance configuration from this tutorial, and the parameterized covariance from the 3DVAR tutorial. Rerun the dirac test. In `dirac_hyb.yaml` you might want to rename the output files `output dirac.exp` so as not to overwrite the previous pure ensemble output.

You should see several output files after running the dirac test this time:

- `...hybrid1_ensemble.an...`  This is the increment from the ensemble covariance
- `...hybrid1_ensemble_localization.an...` This is the localization that was used for the ensemble covariance
- `...hybrid2_SABER.an...` The increment from the parametric covariance
- `...hybrid.an...` The final, combined, increment

Looking at temperature, for example, you'll see that the final increment here is simply a weighted average of the ensemble and parametric covariance models.

| T : hybrid covariance | T : parametric covariance | T : ens covariance|
| :--: | :--: | :--: |
| ![hybrid dirac for T](img/dirac_hyb_T.png) | ![parametric dirac for T](img/dirac_static_T.png) | ![ensemble dirac for T](img/dirac_ens_T.png) |

### Run 3DEnVAR with hybrid covariance

Now we will make the same hybrid covariance change to the 3DVAR.

> [!IMPORTANT]
> Modify the `3denvar.yaml` as described above to use a hybrid background error covariance, and rerun the 3DEnVAR
>
> ```bash
> mpirun -n 10 ./soca_var.x 3denvar.yaml
>```

Look at the output increment and compare with those of the previous 3DVAR and pure ensemble 3DEnVAR.

## 4DEnVAR (information only)

The 4DEnVAR is a simple extension of the 3DEnVAR. We will not be running a 4DEnVAR here, (while the plumbing should be hooked up and working correctly, we have not spent much time scientifically validating it.)

The following yaml snippet provides an example of what needs to be changed, (assuming you have a 4D ensemble background available). Compared with 3DEnVAR, the following changes are made:

- The cost function type is changed to `4D-Ens-Var`
- the `background` now reads in multiple states, one state dated at the center of each subwindow.
- the ensemble portion of the `background error` covariance now includes 4D states (a state for each subwindow of each ensemble member)


```yaml
cost function:
  cost type: 4D-Ens-Var
  time window:
    begin: 2021-08-01T00:00:00Z
    length: PT24H
  subwindow: PT12H
  parallel subwindows: false

  # Background at center of each subwindow
  background:
    states:
    - ocn_filename: ocn.bkg.PT0H.nc
      date: 2021-08-01T00:00:00Z
      ...
    - ocn_filename: ocn.bkg.PT12H.nc
      date: 2021-08-01T12:00:00Z
      ...
    - ocn_filename: ocn.bkg.PT24H.nc
      date: 2021-08-02T00:00:00Z
      ...

  # 4D Ensemble background
  background error:
    covariance model: ensemble
    members from template:
      pattern: '%mem%'
      nmembers: 15
      template:
        states:
        - ocn_filename: ocn.ens_bkg.%mem%.PT0H.nc
          date: 2021-08-01T00:00:00Z
        - ocn_filename: ocn.ens_bkg.%mem%.PT12H.nc
          date: 2021-08-01T12:00:00Z
        - ocn_filename: ocn.ens_bkg.%mem%.PT12H.nc
          date: 2021-08-02T00:00:00Z

    ...
```

>[!WARNING]
> There is a bug with the ADT observation operator with parallel subwindows. Make sure to set `parallel subwindows: false` if using SOCA 4DEnVAR

As with 3DEnVAR, the 4DEnVar can work either as a pure ensemble based background error covariance, or as a hybrid covariance. If using a hybrid covariance, the parametric portion of the background error covariance should behave the same nearly the same as that of the 3DEnVAR/3DVAR.

---
[Prev: SOCA 3DVAR](../3dvar/README.md) | [Next: SOCA LETKF](../letkf/README.md)
