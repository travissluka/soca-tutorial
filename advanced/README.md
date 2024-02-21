# Advanced Topics

- [Advanced Topics](#advanced-topics)
  - [Using gridgen for custom grids](#using-gridgen-for-custom-grids)
  - [Cycling](#cycling)
  - [Regional Issues](#regional-issues)
  - [All SOCA executables](#all-soca-executables)

## Using gridgen for custom grids

## Cycling

- using checkpoint
  `soca_checkpoint_model.x`
- differences with sea-ice
- using IAU
- outer loops

## Regional Issues

- U/V are not brought to cell center, shouldn't be a real problem
- symmetric memory mode, grid is not handled quite right
- artificial land is imposed 

## All SOCA executables

- `soca_addincrement.x`
- `soca_checkpoint_model.x`
- `soca_convertincrement.x`
- `soca_convertstate.x`
- `soca_diffstates.x`
- `soca_enshofx.x`
- `soca_ensmeanandvariance.x`
- `soca_enspert.x`
- `soca_ensrecenter.x` - recenter an ensemble around another state. See it's use in the [LETKF Recentering](../letkf/README.md#re-centering-analysis-ensemble)
- `soca_error_covariance_toolbox.x` 
- `soca_forecast.x`
- `soca_gridgen.x`
- `soca_hofx.x`
- `soca_hofx3d.x`
- `soca_hybridgain.x`
- `soca_letkf.x`
- `soca_setcorscales.x`
- `soca_sqrtvertloc.x`
- `soca_var.x`