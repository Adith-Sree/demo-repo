# CODING 3 - DESIGN OF A BOLTED JOINT UNDER FLUCTUATING AXIAL LOAD

## Step 0 - Input data

| Item                           | Value                                         |
|--------------------------------|-----------------------------------------------|
| Load type                      | axial                                         |
| Total external load, max / min | 120 / 30 kN                                   |
| Number of bolts                | 8                                             |
| Required factor of safety      | 2                                             |
| Property class                 | auto                                          |
| Bolt size                      | auto (coarse series, first-choice sizes only) |
| Preload                        | reusable joint: Fi = 0.75 x proof load        |
| Clamped plates (grip)          | 40 mm of AISI 1020 hot-rolled (20C8)          |
| Washer under nut               | yes                                           |

## Step 1 - Load shared by each bolt

```text
  Pmax per bolt                        = Pmax / N = 15000 N
  Pmin per bolt                        = Pmin / N = 3750 N
```

## Step 2 - Bolt selection from the ISO metric thread database

```text
  For each property class, sizes are tried from smallest up; the first that meets every
  requirement is listed. Cost index = class cost factor x d^2 x L (relative).
```

| Class | Size | L (mm) | Fatigue (Goodman) n_f | Load factor n_L | Separation n_0 | Yield / proof n_p | Meets all | Cost idx |
|-------|------|--------|-----------------------|-----------------|----------------|-------------------|-----------|----------|
| 4.6   | M16  | 65     | 4.151                 | 2.757           | 2.240          | 1.190             | yes       | 16.640   |
| 4.8   | M16  | 65     | 3.332                 | 3.799           | 3.086          | 1.226             | yes       | 16.640   |
| 5.8   | M16  | 65     | 3.996                 | 4.657           | 3.783          | 1.244             | yes       | 18.304   |
| 8.8   | M10  | 55     | 2.843                 | 3.333           | 2.022          | 1.212             | yes       | 7.150    |
| 9.8   | M10  | 55     | 3.123                 | 3.735           | 2.266          | 1.224             | yes       | 7.700    |
| 10.9  | M10  | 55     | 3.164                 | 4.769           | 2.893          | 1.246             | yes       | 9.900    |
| 12.9  | M8   | 55     | 2.611                 | 3.898           | 2.093          | 1.228             | yes       | 8.448    |

```text
  Selected: M10 class 8.8 (lowest cost index that passes).
```

## Step 3 - Thread and property-class data: M10 x 1.5, class 8.8

```text
  Nominal diameter d                   = 10 mm
  Pitch P                              = 1.500 mm
  Pitch diameter d2                    = d - 0.6495 P = 9.026 mm
  Minor diameter d3                    = d - 1.2269 P = 8.160 mm
  Tensile-stress area At               = (pi/4) ((d2 + d3)/2)^2 = 57.990 mm^2
  Root area Ar                         = (pi/4) d3^2 = 52.292 mm^2
  Shank area Ad                        = (pi/4) d^2 = 78.540 mm^2
  Proof strength Sp                    = 580 MPa
  Tensile strength Sut                 = 800 MPa
  Yield strength Sy                    = 640 MPa
  Endurance strength Se                = Shigley Table 8-17 = 129 MPa
```

## Step 4 - Bolt length

```text
  Grip l = plates + washer             = 42 mm
  Length needed  l + nut height + 2P   = 53.400 mm
  Standard length L                    = 55 mm
  Thread length LT (ISO 4014)          = 2d + 6 (L <= 125) = 26 mm
  Unthreaded length in grip ld         = 29 mm
  Threaded length in grip lt           = 13 mm
```

## Step 5 - Preload and tightening torque

```text
  Proof load Fp                        = Sp At = 33.634 kN
  Preload Fi                           = 0.75 Fp = 25.225 kN
  Tightening torque                    = K Fi d, K = 0.2000 = 50.451 N.m
```

## Step 6 - Joint stiffness

```text
  Bolt stiffness kb                    = Ad At E / (Ad lt + At ld) = 348.8 kN/mm
  Member stiffness km                  = frustum, Em = 207 GPa = 1724.9 kN/mm
  Joint constant C                     = kb / (kb + km) = 0.1682
  Only the fraction C of the external load reaches the bolt; the rest unloads the plates.
```

## Step 7 - Stresses in the bolt

```text
  Preload stress sigma_i               = Fi / At = 435 MPa
  Alternating stress sigma_a           = C (Pmax - Pmin) / (2 At) = 16.316 MPa
  Mean stress sigma_m                  = sigma_i + C (Pmax + Pmin) / (2 At) = 462.2 MPa
```

## Step 8 - Factors of safety

```text
  Fatigue, Goodman n_f                 = Se (Sut - si) / (Sut sa + Se (sm - si)) = 2.843
  Yield (proof) n_p                    = Sp At / (C Pmax + Fi) = 1.212
  Load factor n_L                      = (Sp At - Fi) / (C Pmax) = 3.333
  Joint separation n_0                 = Fi / (Pmax (1 - C)) = 2.022
  [ OK ] Fatigue (Goodman) n_f = 2.843 >= 2
  [ OK ] Load factor n_L = 3.333 >= 2
  [ OK ] Separation n_0 = 2.022 >= 2
  [ OK ] Yield / proof n_p = 1.212 >= 1
```

## FINAL OUTPUT - Standard bolt

```text
  8 x ISO 4014 hex bolt M10 x 1.5 x 55 - 8.8, with ISO 4032 hex nut and ISO 7089 washer
```

| Output                      | Value                      |
|-----------------------------|----------------------------|
| Thread                      | M10 x 1.5 (coarse)         |
| Property class              | 8.8  (Sp 580, Sut 800 MPa) |
| Length                      | 55 mm                      |
| Tensile-stress area         | 57.990 mm^2                |
| Nut height / across flats   | 8.400 / 16 mm              |
| Preload / tightening torque | 25.225 kN / 50.451 N.m     |
| Fatigue (Goodman) n_f       | 2.843                      |
| Load factor n_L             | 3.333                      |
| Separation n_0              | 2.022                      |
| Yield / proof n_p           | 1.212                      |
| Meets all requirements      | YES                        |

