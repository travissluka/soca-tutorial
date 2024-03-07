# SOCA LETKF

- [SOCA LETKF](#soca-letkf)
  - [Setup work directory](#setup-work-directory)
  - [Running LETKF](#running-letkf)
    - [LETKF inflation](#letkf-inflation)
    - [Splitting HofX and LETKF](#splitting-hofx-and-letkf)
  - [Re-Centering Analysis Ensemble](#re-centering-analysis-ensemble)

## Setup work directory

The following tutorial assumes that you have already set up your environment, compiled SOCA. You not need to have run any of the previous tutorial sections beyond that.

> [!IMPORTANT]
> 
From within the tutorial directory you previously created, run the following commands to copy the sample yaml files for this section of the tutorial:

```bash
cp ../letkf/files/* .
ln -sf ../input_data/* .
mkdir ana_ens
```

## Running LETKF

- explain `obs localization` section
  - localization is in 1 sigma of gaussian, not gaspari-cohn cuttof distance
  - different observations can have different localization
- explain `obs space.distribution` section
  
> [!IMPORTANT]
> run the LETKF
>
> ```bash
> mpirun -n ./soca_letkf.x letkf.yaml
> ```

- should behave similarly to a pure-ensemble 3dEnVAR, except localization is done in observation space, not model space.
- look at output (mean, increment)
  - the mean values are saved as ensemble member number `0`
- can turn unneeded output sections off

### LETKF inflation

- unlike the 3DEnVAR, an analysis ensemble is produced, this is useful if running a dynamic ensemble, through forecast, and ensemble background for next cycle.
- Depending on the number of observations, and the spread of the forcing for you ocean ensemble, sufficient spread can often be a problem

Three types of inflation are available:

```yaml
local ensemble DA:
  inflation:
    rtps: 0.9
    rtpp: 0.6
    mult: 1.1
  ...
```

- `rtps` - **relaxation to prior spread** the spread of the analysis ensembles are relaxed back toward the spread of the background ensembles. A value of `0.0` is off, and `1.0` is increasing the spread to be identical to the background. You probably don't want to go above `1.0`.
- `rtpp` - **relaxation to prior perturbation** - Similar to `rtps`, however, the individual analysis perturbation from the mean is relaxed toward the background perturbation from the background mean.
- `mult` - **multiplicatiave inflation** - The spread is multiplied by a fixed value to increase it. `1.0` is effectively off, and anything larger than `1.0` will increase the spread.

When in doubt, use `rtps` with a value of `0.8` - `0.9` or so. The exact value used will depend on your experiment setup.
  
### Splitting HofX and LETKF

- The above example runs the observation operator (for both the background and the analysis) as part of the same executable.
- in some cases, it might be more efficient to do this as two separate steps
- explain the different modes of the drive

## Re-Centering Analysis Ensemble

If performing a hybrid LETKF/3DEnvar, where the LETKF analysis ensemble should be recentered around the deterministic [3DEnVAR](../3denvar/README.md) analysis

- show a diagram

```bash
mpirun -n 10 ./soca_ensrecenter.x letkf_recenter.yaml
```

- use cdo / nco to calculate spread/mean
- spread should be the same, mean should now be the same as the central member.

---
[Prev: SOCA 3DEnVAR](../3denvar/README.md) | [Next: SOCA advanced topics](../advanced/README.md)