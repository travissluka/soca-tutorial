# SOCA HofX and 3DVAR 

- [SOCA HofX and 3DVAR](#soca-hofx-and-3dvar)
  - [Setup work directory](#setup-work-directory)
  - [Standalone HofX](#standalone-hofx)
    - [State](#state)
    - [Observations](#observations)
      - [Identity Operator](#identity-operator)
      - [ADT Operator](#adt-operator)
      - [Composite (InsituTemperature / VertInterp) Operator](#composite-insitutemperature--vertinterp-operator)
    - [Output](#output)
  - [3DVAR](#3dvar)
    - [Quality Control filters](#quality-control-filters)
      - [Bounds Check](#bounds-check)
      - [Domain Check](#domain-check)
      - [Background Check](#background-check)
    - [Convergence / Minimizer](#convergence--minimizer)
      - [Iterations](#iterations)
      - [Minimizers](#minimizers)
  - [3DVAR-FGAT](#3dvar-fgat)

This section of the tutorial will go over the basics of setting up a 3DVAR with a plain static background error covariance.

## Setup work directory

The following tutorial assumes you have already set up your environment, compiled SOCA, and run the initialization steps in the [previous section](../init/README.md).

From within the tutorial directory you previously created, run the following commands to copy the sample yaml files for this section of the tutorial and setup the output directories:

```bash
cp ../3dvar/files/* .
mkdir obs_out
```

### Rerun diffusion calibration (optional) <!-- omit in toc -->

The length scales that were used in the previous section were a little larger than should be used, on purpose, in order to help visualize the dirac tests. To use length scales that are more realistic you may want to do the following:

- change `diffusion_setscales.yaml` so that `HZ_ROSSBY_MULT: 1.0` and `HZ_MIN_GRID_MULT: 1.5`
- rerun  `./calc_scales.py` and the diffusion calibration

Note how there are fewer iterations of the diffusion operator required now (since the length scales are shorter). This will help the 3DVAR in this part of the tutorial run faster!

## Standalone HofX

Before actually performing a data assimilation cycle, it's helpful to look at the HofX (i.e. $h(x)$ or "observation operator"). There is a special executable `soca_hofx3d.x` that will read in a background state and observation files and calculate the model equivalent at the given observation locations.

Look at the `hofx.yaml` configuration file and note the following sections:

### State

The `state` section specifies the background state, which variables should be loaded, and the date of the background. Note that the date given by `state.date` overwrites anything that is present in the ocean or ice restart files. In our case here we are pretending these backgrounds are for Aug 1, 2021 at 12Z (even though they actually came from a previous data assimilation run in 2019).

There are several state variables listed. If you're curious about how the state variable names are mapped from the input restart files to what is in SOCA, and what is expected by other parts of JEDI such as UFO, look at the field mapping file (`fields_metadata.yml`). In short, the variables listed here are for:

from the file given by `ice_filename`:
- `cice` - sea ice concentration
- `hicen` - sea ice thickness
- `hsnon` - sea ice snow thickness

from the file given by `ocn_filename`:
- `tocn` - ocean temperature
- `socn` - ocean salinity
- `ssh` - ocean surface height
- `hocn` - ocean layer thickness

and the following fields, which are not directly present in the input files, but rather are calculated by SOCA, and are needed by some of the variable changes for now:

- `mld` - mixed layer depth
- `layer_depth` - model layer depth

Unused variables can be removed. For example, if you are only doing ocean DA, without sea ice, you can remove everything ice related from this list.

### Observations

The `time window` section specifies the time window in which observations are considered valid. Note that the date of the background state is in the center of this time window.

The `observations.observers` section is where one or more observation input files are specified. Each observation has the following sections:

- `obs space` - this section has an arbitrary name (`name`) that can be whatever you want, input file (`obsdatain`), the optional output file (`obsdataout`), and the variables that should be used from the files (`simulated variables`)
- `obs filters` - optional quality control filters (this will be discussed more later)
- `obs operator` - the observation operator. There are many types of observation operators available in UFO (see [observation operator documentation](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/obsops.html) for more extensive information). We will discuss the major three that are important for the ocean (excluding radiances).

#### Identity Operator

For observations that directly observe some variable in the model state, the [`Identity`](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/obsops.html#obsops-identity) observation operator type is used. Here we have SST observations. Our simulated variable name is `seaSurfaceTemperature` which maps to the model variable `sea_surface_temperature`. This simple variable name mapping is listed in the [`obsop_name_map.yml`](files/obsop_name_map.yml) file.

```yaml
- obs space:
    name: sst_avhrr_metop-b
    ...
    simulated variables: [seaSurfaceTemperature]
  obs operator:
    name: Identity
    observation alias file: ./obsop_name_map.yml
```

| Metop-B SST observations 2021-08-01|
| :--: |
| ![metop-b observations](img/obs_metop.png) |

#### ADT Operator

The [`ADT` operator](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/obsops.html#absolute-dynamic-topography) (absolute dynamic topography) is close to being an identity operator, however there is a special step that removes the global offset between the model SSH and the observed ADT. This offset is calculated individually for each ADT obs space present.

```yaml
- obs space:
    name: ADT
    ...
    simulated variables: [absoluteDynamicTopography]
  obs operator:
    name: ADT
```

| Cryosat-2 observations 2021-08-01 |
| :--: |
| ![cryosat-2 observations](img/obs_cryosat2.png) |

#### Composite (InsituTemperature / VertInterp) Operator

The [`Composite`](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/obsops.html#obsops-composite) operator is used for insitu T/S profiles so that we may apply different observation operators for different variables in the file. Here, the [`VertInterp`](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/obsops.html#vertical-interpolation) operator is used for `salinity`. It is similar to the `Identity` operator, but performs vertical interpolation in addition to horizontal interpolation. The `InsituTemperature` operator is used for `waterTemperature`. It is similar ot the `VertInterp` operator, however it also converts between potential temperature (model) and insitu temperature (observation).

```yaml
- obs space:
    name: insitu_ts
    ...
    simulated variables: [waterTemperature, salinity]          
  obs operator:
    name: Composite
    components:
    - name: InsituTemperature
      variables:
      - name: waterTemperature
    - name: VertInterp
      observation alias file: ./obsop_name_map.yml
      variables:
      - name: salinity
      vertical coordinate: sea_water_depth
      observation vertical coordinate: depth
      interpolation method: linear
```

| Insitu observations 2021-08-01 |
| :--: |
| ![insitu observations](img/obs_insitu.png) |

### Output
  
Run the observation operators:

```bash
mpirun -n 10 ./soca_hofx3d.x hofx.yaml
```

If you look at the output log, you'll notice several sections that let you know what is happening. There is an `H(x)` section that shows you the number of input observations that are valid for the given `time window`, as well as some statistics on the observation operator values that were calculated from the given background state.

```text
H(x):
sst_avhrr_metop-b nobs= 775202 Min=-1.86137, Max=33.1543, RMS=20.5008
adt_c2 nobs= 40476 Min=-1.50592, Max=1.86233, RMS=0.791879
insitu_ts nobs= 730386 Min=-1.90618, Max=38.0376, RMS=26.3217
```

You'll notice that, unfortunately, the temperature and salinity statistics are combined for the `insitu_ts` obs space, but that is just a side effect of how the diagnostics are presented in the log file.

The log file will also present details on how many observations passed the quality control filters, and how many failed for each filter. (We will discuss basic QC filters in more detail in the 3DVAR section below.) There is a long list of [generic quality control filters in UFO](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/index.html), see the online documentation for more information on the filters available. Here is the log output with the qc filters that were given in `hofx.yaml`

```text
QC sst_avhrr_metop-b seaSurfaceSkinTemperature: 809406 rejected as processed but not assimilated.
QC sst_avhrr_metop-b seaSurfaceSkinTemperature: 0 passed out of 809406 observations.                 
QC sst_avhrr_metop-b seaSurfaceTemperature: 5 out of bounds.                                         
QC sst_avhrr_metop-b seaSurfaceTemperature: 34203 H(x) failed.                                       
QC sst_avhrr_metop-b seaSurfaceTemperature: 775198 passed out of 809406 observations.                
QC adt_c2 absoluteDynamicTopography: 81 out of bounds.                                               
QC adt_c2 absoluteDynamicTopography: 28 H(x) failed.                                                 
QC adt_c2 absoluteDynamicTopography: 40476 passed out of 40585 observations.  
QC insitu_ts salinity: 1 missing values.                                                                                                         
QC insitu_ts salinity: 22936 H(x) failed.                                                                                                        
QC insitu_ts salinity: 365192 passed out of 388129 observations.                                                                                 
QC insitu_ts waterTemperature: 178 missing values.                                                                                               
QC insitu_ts waterTemperature: 22879 H(x) failed.                                                                                                
QC insitu_ts waterTemperature: 149223 rejected by first-guess check.                                                                             
QC insitu_ts waterTemperature: 215849 passed out of 388129 observations.  
```

Output observation files are generated as defined in the `obsdataout` section of each observation space. Look at the contents of one of the output in `obs_out/`, for example:

```bash
ncdump -h obs_out/hofx.adt_c2.20210801T120000Z.nc4
```

The contents of this file should look similar to the input file, except now several additional variable groups have been added:

- `EffectiveError` - this is the calculated observation error that would be used for data assimilation. The input file *may* have had the `ObsError`variable, which is the default used for determining the observation error. However, there are various filters than can either modify or explicitly set the final error. (see [UFO filter actions](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/FilterOptions.html#filter-actions)). If an observation is QC'ed out, the `EffectiveError` is missing.
- `EffectiveQC` - non-zero values here indicate the observation was removed for some reason and will not be used in the data assimilation. The value indicates which filter (listed in the UFO [QCflags.h](https://github.com/JCSDA/ufo/blob/master/src/ufo/filters/QCflags.h)) was responsible for removing the observations.
- `hofx` - this is the end product of the forward operator

You can examine these output files to get detailed information of which observations are or aren't used, and the resulting hofx values.

## 3DVAR

The variational data assimilation methods are available via the `soca_var.x` executable. In addition to 3DVAR, the other variational methods are available via this executable, including 3DFGAT, 3DEnVAR, 4DEnVAR, and (if we had a model TL/ADJ) 4DVAR. The effective variational methods used depend on the cost function type and the background error type specified in the configuration file. First, we will look at a plain 3DVAR.

Look at the `3dvar.yaml` configuration file in your working directory. It is set up  to perform data assimilation with insitu T/S profiles only. You'll notice the cost function type is set to 3DVAR:

```yaml
cost function:
  cost type: 3D-Var
```

The background error section looks similar to what was done in the previous section for the dirac tests (indicating a plain 3DVAR, and not a 3DEnVAR which will be covered in the next section), and the observations section should look similar to what was in the `hofx.yaml` configuration.

Lets run the 3DVAR and see what happens:

```bash
mpirun -n 10 ./soca_var.x 3dvar.yaml
```

The output log contains some useful information. It has the same observation hofx and qc information that the hofx application produced. It also shows the final analysis and increment values, lets look at those to make sure everything is working:

```text
CostFunction::addIncrement: Increment:                                                                                                           
  Valid time: 2021-08-01T12:00:00Z                                                                                                               
   socn   min=  -52.225874   max=    2.759373   mean=   -0.002550                                                                                
   tocn   min=  -42.685815   max=   55.446582   mean=   -0.005559                                                                                
    ssh   min=   -2.106387   max=   11.213957   mean=    0.002550                                                                                
  ...

CostFunction::addIncrement: Analysis:                                                                                                            
  Valid time: 2021-08-01T12:00:00Z                                                                                                               
   socn   min=  -17.546187   max=   40.756473   mean=   34.283437                                                                                
   tocn   min=  -14.931892   max=   69.766894   mean=    7.859047                                                                                
    ssh   min=   -2.176699   max=   10.284270   mean=   -0.308790                                                                                
  ...
```

Wow, that looks horrible! The increments are huge, and the resulting analysis is crazy. An SSH increment of 11m, and salinity analysis of -17, what happened??

You could look at the observation output file. Similar to the hofx application, the observation space statistics are saved and if you run a `ncdump -h ...` on a file in the `obs_out/` directory you'll see the additional variables that are created for each observation space. We don't provide tools (yet) to easily look at the statistics in these files, but you could easily write a python script to do so for you.

- `hofx0` - The observation operator applied to the background
- `hofx1` - The observation operator applied after the first outer iteration of 3DVAR (i.e. the observation operator applied to the analysis in this case since we only have a single outer loop)
- `EffectiveQC0` - The same meaning as `EffectiveQC` from the hofx application, applied to the initial background
- `EffectiveQC1` - The same as `EffectiveQC0`, though after the first outer iteration of 3DVAR
- `ombg` - observation minus background, effectively the same as `(ObsValue - hofx0)`
- `oman` - observation minus analysis, effectively the same as `(ObsValue - hofx1)`
  
The executable produces two other output files, an increment (`ocn.3dvar.incr.2021-08-01T12:00:00Z.nc`), and an analysis (`ocn.3dvar.an.2021-08-01T12:00:00Z.nc`) ( which is just the increment plus the background). If you open those you'll see that there are some large increments and bad analysis in a few localized spots.

| bad SSH Analysis without QC|
| :--: |
| ![bad analysis](img/an_ssh_bad.png) |

It's time to add some basic QC to those observations!

### Quality Control filters

For each observation space in the config file you can  enable one or more QC filters. These are the same filters that can be  enabled in the hofx application. There is a long list of filters available that can remove obs, change obs values, set or inflate obs errors, create derived variables, etc. You can read more about them in the [UFO obs filters](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/index.html) documentation. We'll look at 3 basic qc filters here. Enable these filters by uncommenting the appropriate lines in your `3dvar.yaml` file for the insitu TS observations.

(If you're curious about how complicated QC filters could get, check out what we are currently using for the full set of QC for the insitu obs in [`ocean_profile.yaml`](./ocean_profile.yaml) !)
  
#### Bounds Check

The [Bounds Check Filter](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/GenericQC.html#bounds-check-filter) simply rejects observations that lie outside specific min/max values. Here, temperature obs outside -1.9 to 40.0 C are rejected, and salinity observations outside 2.0 to 41.0 PSU are rejected.

```yaml
- filter: Bounds Check
  filter variables: [{name: waterTemperature}]      
  minvalue: -1.9
  maxvalue: 40.0

- filter: Bounds Check
  filter variables: [{name: salinity}]
  minvalue: 2.0
  maxvalue: 41.0
```

#### Domain Check

The [Domain Check Filter](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/GenericQC.html#domain-check-filter) only keeps observations that pass all the given `where` sections listed. The tests in the `where` section can be based on any variable that is in the observation file, or interpolated from the model state (e.g. `GeoVaLs/sea_surface_temperature`). Here observations that do not have a proper observation error assigned to them from the input file are rejected.

```yaml
- filter: Domain Check
  filter variables: [{name: waterTemperature}]
  where:
  - variable: {name: ObsError/waterTemperature}
    minvalue: 0.001      
```

#### Background Check

The [Background Check Filter](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/ufo/qcfilters/GenericQC.html#background-check-filter) rejects observations that are too far from the background, either as an absolute value (`absolute threshold`) or as a number calculated as a multiple of the observation error (`threshold`). Here, we remove temperature observations that are more than 5 times the observation error away from the background.

```yaml
- filter: Background Check
  filter variables: [{name: waterTemperature}]
  threshold: 5
```

#### Rerun 3DVAR <!-- omit in toc -->

If you rerun the var now with the QC filters in place, you'll see a much more reasonable analysis. The output log will indicate that additional TS observations are being rejected now by the filters, most notably quite a few observations are removed by the bounds check and are shown as "out of bounds" in the log:

```text
QC insitu_ts salinity: 1 missing values.
QC insitu_ts salinity: 815 out of bounds.
QC insitu_ts salinity: 22814 H(x) failed.
QC insitu_ts salinity: 85380 rejected by first-guess check.
QC insitu_ts salinity: 279119 passed out of 388129 observations.
QC insitu_ts waterTemperature: 178 missing values.
QC insitu_ts waterTemperature: 654 out of bounds.
QC insitu_ts waterTemperature: 23042 H(x) failed.
QC insitu_ts waterTemperature: 148349 rejected by first-guess check.
QC insitu_ts waterTemperature: 215906 passed out of 388129 observations.
```

Turn on all the observations that are in `3dvar.yaml` and the results should look like the following:

| SSH increment | SST increment | SSS increment |
| :--: | :--: | :--:|
| ![ssh increment](img/inc_ssh_good.png) | ![sst increment](img/inc_sst_good.png) | ![sss increment](img/inc_sss_good.png)

Using the resulting analysis for the next forecast as part of a cycling system will be covered in a later tutorial. But, in short, you can either use the increment file to drive IAU for MOM6, or you can use the analysis file to replace the given state variables in the original background restart file. (The analysis file only contains the small number of variables used in the data assimilation, it does not contain all the variables needed for a MOM6 restart).

#### ✨ Optional exercises <!-- omit in toc -->

Add observations and the appropriate QC filters for the other observation files that are in `input_data/obs/` but are not yet included in `3dvar.yaml`. In order to add the ice concentration observations, you'll need to:

- add ice to the background state
- add the ice vars to the state, analysis variables, and the diffusion operator variables

### Convergence / Minimizer

There are several other options in the `variational` section of `3dvar.yaml` that are of importance.

#### Iterations

First is the `variational.iterations` section. Each item of this list defines an outer loops. We normally only do a single outer loop with 3DVAR with the ocean, however multiple outer loops, where everything is re-linearized at the beginning of the loop, is possible. The geometry is specified again, because in theory you could use a lower resolution geometry for the variational minimizer, though we don't exercise that option yet within SOCA.

The number of iterations of the minimizer is controlled by two parameters. Minimization stops when one of the two conditions are met:

- `iterations.ninner` - the maximum number of inner iterations
- `iterations.gradient norm reduction` - the target norm for the minimization of the gradient.

But how do I know what to set for these two parameters? When you run the 3DVAR the output log will show diagnostics for each iteration of the minimization, including the value of the norm reduction for the iterations, which will let you know how it is converging:

```text
DRPCG end of iteration 1
  Gradient reduction ( 1) = 2598709.78851671
  Norm reduction ( 1) = 0.5090873539758356
  Quadratic cost function: J   ( 1) = 660206600.3306482
  Quadratic cost function: Jb  ( 1) = 38.85576871046547
  Quadratic cost function: JoJc( 1) = 660206561.4748795

...
 
DRPCG end of iteration 2
  Gradient reduction ( 2) = 1928596.023566572
  Norm reduction ( 2) = 0.3778120399839757
  Quadratic cost function: J   ( 2) = 647740573.7450265
  Quadratic cost function: Jb  ( 2) = 139.8621227075966
  Quadratic cost function: JoJc( 2) = 647740433.8829038
```

If you parse the output and plot the cost function (J) over the iterations we get the following plot. You can see that there is a big decrease in the cost function at first, but then after 20 or 30 iterations you get diminishing returns as it converges slower. This is why, for this tutorial, the number of iterations was set to only 20. The number of iterations required will vary depending on the configuration of SOCA, and the observations used.

![cost function](img/cost_function.png)

##### ✨ Optional Exercises <!-- omit in toc -->

Add a second outer loop to the 3DVAR. (you can simply duplicate the existing outer loop). Make sure to name the increment output file to something different for the second loop, otherwise the increment from the first loop will be overwritten. Bonus points for plotting the cost function over the two outer loops.

#### Minimizers

The `cost function.cost type` parameter in `3dvar.yaml` is set to one of the long list of [minimizers available in OOPS](https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/en/latest/inside/jedi-components/oops/applications/variational.html), however there only two that you should be concerned with:

- **DRPCG** - Derber-Rosati Preconditioned Conjugate Gradients. For details see S. Gurol, PhD Manuscript, 2013. **Use this if your model space is smaller than your observation space**
- **RPCG** : Augmented Restricted Preconditioned Conjugate Gradients. Based on the algorithm proposed in Gratton and Tshimanga, QJRMS, 135: 1573-1585 (2009). **Use this if your observation space is smaller than your model space**

These two minimizers should produce nearly the same results, the difference will simply be in runtime and memory usage. Since with ocean DA we nearly always have fewer observations than 3D model points, **you should use `RPCG`** unless you have reason to do otherwise.

For example, for 30 iterations, you can see that `RPCG` uses much less memory and CPU time with the given observations and grid size used in this tutorial:

- **`DRPCG`**

  ```text
  OOPS_STATS ------------------------ Parallel Timing Statistics (  30 MPI tasks) -----------------------------------
  OOPS_STATS Run end    - Runtime:  105.91 sec,  Memory: total:  40.34 Gb, per task: min =     1.23 Gb, max =     1.43 Gb
  ```

- **`RPCG`**

  ```text
  OOPS_STATS ------------------------ Parallel Timing Statistics (  30 MPI tasks) -----------------------------------
  OOPS_STATS Run end    - Runtime:   89.46 sec,  Memory: total:  22.23 Gb, per task: min =   696.48 Mb, max =   770.02 Mb
  ```

## 3DVAR-FGAT

One variation on the previously shown 3DVAR is the 3DVAR-FGAT (**F**irst **G**uess at **A**ppriopriate **T**ime). This differs from the standard 3DVAR mainly in how the hofx is calculated. Instead of a single background at the center of the window, multiple background time slots can be given so that the hofx is calculated using the background time slot that is closest to the actual observation time. The ocean changes slowly, so if using short windows (e.g. 6 hrs) it's uncertain how much benefit FGAT would have, though it might be beneficial in the mixed layer where there is a strong diurnal signal, or with a high resolution grid.

You can run 3DFGAT with the sample yaml given.

```bash
mpirun -n 10 ./soca_var.x 3dfgat.yaml
```

Looking inside the configuration file, to enable FGAT this with the variational application, you'll need to change the cost function type to:

```yaml
cost function:
  cost type: 3D-FGAT
```

and add a `model` section. We will not be running an actual model from the initial background, as part of the variational application (this is possible though with other JEDI systems, namely FV3-JEDI or MPAS-JEDI, but not so much with SOCA). Instead, we will be using a "pseudo model" which will load in several time slots that have already been saved from a model run.

```yaml
model:
  name: PseudoModel
  tstep: PT6H
  states:
  - read_from_file: 1
    date: 2021-08-01T06:00:00Z
    basename: ./bkg/
    ocn_filename: ocn.bkg.2019080112.nc
  - read_from_file: 1
    date: 2021-08-01T12:00:00Z
    basename: ./bkg/
    ocn_filename: ocn.bkg.2019080112.nc
  - read_from_file: 1
    date: 2021-08-01T18:00:00Z
    basename: ./bkg/
    ocn_filename: ocn.bkg.2019080112.nc
  - read_from_file: 1
    date: 2021-08-02T00:00:00Z
    basename: ./bkg/
    ocn_filename: ocn.bkg.2019080112.nc
```

One thing to notice is that the background time is no longer at the center of the window, but rather at the beginning.

Also, if you actually ran the 3DFGAT and looked at the output, you should notice that the output is the same as the simple 3DVAR case, this is because the same background file was used for each time slot! (I didn't have multiple time slots available in the input data)

The next tutorial will present how to add a hybrid ensemble background error covariance to run a 3DEnVAR. 

---
[Prev: SOCA Initialization](../init/README.md) | [Next: SOCA 3DEnVAR](../3denvar/README.md)
