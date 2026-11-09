# CODING 3 - DESIGN OF A BOLTED JOINT UNDER FLUCTUATING SHEAR LOAD

## Step 0 - Input data

| Item                           | Value                                         |
|--------------------------------|-----------------------------------------------|
| Load type                      | shear (bearing type)                          |
| Total external load, max / min | 30 / 10 kN                                    |
| Number of bolts                | 4                                             |
| Required factor of safety      | 2                                             |
| Property class                 | 8.8                                           |
| Bolt size                      | auto (coarse series, first-choice sizes only) |
| Preload                        | reusable joint: Fi = 0.75 x proof load        |
| Clamped plates (grip)          | 24 mm of AISI 1020 hot-rolled (20C8)          |
| Washer under nut               | yes                                           |
| Shear planes                   | 1                                             |
| Friction coefficient           | 0.3000                                        |
| Threads in shear plane         | no                                            |

## Step 1 - Load shared by each bolt

```text
  Pmax per bolt                        = Pmax / N = 7500 N
  Pmin per bolt                        = Pmin / N = 2500 N
  Shear per bolt per shear plane = P / (N x 1)
```

## Step 2 - Bolt selection from the ISO metric thread database

```text
  For each property class, sizes are tried from smallest up; the first that meets every
  requirement is listed. Cost index = class cost factor x d^2 x L (relative).
```

| Class | Size | L (mm) | Fatigue (Goodman) n_f | Static shear n_s | Bearing on bolt | Bearing on plate | Meets all | Cost idx |
|-------|------|--------|-----------------------|------------------|-----------------|------------------|-----------|----------|
| 8.8   | M12  | 45     | 2.548                 | 5.047            | 11.136          | 4.032            | yes       | 8.424    |

```text
  Selected: M12 class 8.8 (lowest cost index that passes).
```

## Step 3 - Thread and property-class data: M12 x 1.75, class 8.8

```text
  Nominal diameter d                   = 12 mm
  Pitch P                              = 1.750 mm
  Pitch diameter d2                    = d - 0.6495 P = 10.863 mm
  Minor diameter d3                    = d - 1.2269 P = 9.853 mm
  Tensile-stress area At               = (pi/4) ((d2 + d3)/2)^2 = 84.267 mm^2
  Root area Ar                         = (pi/4) d3^2 = 76.247 mm^2
  Shank area Ad                        = (pi/4) d^2 = 113.1 mm^2
  Proof strength Sp                    = 580 MPa
  Tensile strength Sut                 = 800 MPa
  Yield strength Sy                    = 640 MPa
  Endurance strength Se                = Shigley Table 8-17 = 129 MPa
```

## Step 4 - Bolt length

```text
  Grip l = plates + washer             = 26.500 mm
  Length needed  l + nut height + 2P   = 40.800 mm
  Standard length L                    = 45 mm
  Thread length LT (ISO 4014)          = 2d + 6 (L <= 125) = 30 mm
  Unthreaded length in grip ld         = 15 mm
  Threaded length in grip lt           = 11.500 mm
```

## Step 5 - Preload and tightening torque

```text
  Proof load Fp                        = Sp At = 48.875 kN
  Preload Fi                           = 0.75 Fp = 36.656 kN
  Tightening torque                    = K Fi d, K = 0.2000 = 87.974 N.m
```

## Step 6 - Bearing-type joint: shear stresses in the bolt

```text
  Shear area                           = Ad = 113.1 mm^2
  tau_max / tau_min                    = 66.315 / 22.105 MPa
  tau_a, tau_m                         = 22.105, 44.210 MPa
  von Mises sigma'_a, sigma'_m         = sqrt(3) tau = 38.287, 76.573 MPa
```

## Step 7 - Factors of safety

```text
  Fatigue, Goodman n_f                 = 1 / (s'a/Se + s'm/Sut) = 2.548
  Static shear n_s                     = 0.577 Sp / tau_max = 5.047
  Bearing stress on bolt / plate       = Pmax / (N d t), t = 12 mm = 52.083 MPa
  Bearing FoS, bolt                    = Sp / sigma_b = 11.136
  Bearing FoS, plate                   = Sy(plate) / sigma_b, Sy = 210 = 4.032
  Se from the bolt table includes the thread notch effect, so it is conservative for a plain shank.
  [ OK ] Fatigue (Goodman) n_f = 2.548 >= 2
  [ OK ] Static shear n_s = 5.047 >= 2
  [ OK ] Bearing on bolt = 11.136 >= 2
  [ OK ] Bearing on plate = 4.032 >= 2
```

## FINAL OUTPUT - Standard bolt

```text
  4 x ISO 4014 hex bolt M12 x 1.75 x 45 - 8.8, with ISO 4032 hex nut and ISO 7089 washer
```

| Output                      | Value                      |
|-----------------------------|----------------------------|
| Thread                      | M12 x 1.75 (coarse)        |
| Property class              | 8.8  (Sp 580, Sut 800 MPa) |
| Length                      | 45 mm                      |
| Tensile-stress area         | 84.267 mm^2                |
| Nut height / across flats   | 10.800 / 18 mm             |
| Preload / tightening torque | 36.656 kN / 87.974 N.m     |
| Fatigue (Goodman) n_f       | 2.548                      |
| Static shear n_s            | 5.047                      |
| Bearing on bolt             | 11.136                     |
| Bearing on plate            | 4.032                      |
| Meets all requirements      | YES                        |

