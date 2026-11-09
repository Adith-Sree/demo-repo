# CODING 1 - DESIGN OF A POWER TRANSMISSION SHAFT (FLUCTUATING LOADS)

## Step 0 - Input data

| Item                              | Value                                              |
|-----------------------------------|----------------------------------------------------|
| Shaft configuration               | simply supported, bearings at x = 0 and x = 600 mm |
|   Gear (r = 150 mm) at x = 150 mm | Fv 485..1456 N, Fh 1333..4000 N                    |
|   Pulley at x = 450 mm            | Fv 1500..4500 N, Fh 0..0 N                         |
| Bending stress cycle              | fully reversed (rotating shaft)                    |
| Torque, max / min                 | 600 / 200 N.m                                      |
| Factor of safety n                | 2                                                  |
| Fatigue criterion                 | DE-Goodman                                         |
| Surface finish                    | machined                                           |
| Reliability                       | 90 %                                               |
| Operating temperature             | 25 C                                               |
| Stress raiser at critical section | Shoulder fillet, well rounded (r/d = 0.1)          |
| Constraint: max shaft diameter    | 60 mm                                              |
| Constraint: max angle of twist    | 1 deg over 1000 mm                                 |
| Material                          | automatic selection                                |

## Step 1 - Bending moment at the critical section

```text
  MAX load case reactions: vertical RA = 2217 N, RB = 3739 N; horizontal RA = 3000 N, RB = 1000 N
  MIN load case reactions: vertical RA = 738.8 N, RB = 1246.2 N; horizontal RA = 999.8 N, RB = 333.2 N
  Resultant moment M = sqrt(Mv^2 + Mh^2). Bending-moment values (N.m):
```

| x (mm) | Mv (max case) | Mh (max case) | M resultant (max case) | M (min case) |
|--------|---------------|---------------|------------------------|--------------|
| 0      | 0             | 0             | 0                      | 0            |
| 150    | 332.6         | 450           | 559.5                  | 186.5        |
| 450    | 560.9         | 150           | 580.6                  | 193.5        |
| 600    | 0             | 0             | 0                      | 0            |

```text
  Critical section x (largest M)       = 450 mm from bearing A
  The stress raiser is assumed to sit at this section (conservative).
  Mmax                                 = 580.6 N.m
  Mmin                                 = 193.5 N.m
```

## Step 2 - Mean and alternating components

```text
  Rotating shaft with stationary loads: every fibre sees +M and -M each revolution,
  so bending is completely reversed: Mm = 0, Ma = max|M|.
  Mean bending moment Mm               = 0 N.m
  Alternating bending moment Ma        = 580.6 N.m
  Mean torque Tm                       = (Tmax + Tmin)/2 = 400 N.m
  Alternating torque Ta                = (Tmax - Tmin)/2 = 200 N.m
```

## Step 3 - Material selection (materials database)

```text
  Every shaft material in the database is sized with the same procedure (steps 4-9).
  Feasible = standard diameter <= d_max. Cost index = relative cost x kg per metre.
```

| Material   | IS           | Sut  | Syt  | d fatigue | d yield | d twist | d std | Feasible | Cost idx |
|------------|--------------|------|------|-----------|---------|---------|-------|----------|----------|
| 1045-CD    | 45C8         | 630  | 530  | 49.368    | 35.828  | 45.841  | 50    | yes      | 19.267   |
| 1060-HR    | 60C4         | 680  | 370  | 48.449    | 40.440  | 45.841  | 50    | yes      | 19.267   |
| 1030-HR    | 30C8         | 470  | 260  | 53.097    | 45.210  | 45.841  | 55    | yes      | 19.583   |
| 1050-CD    | 50C4         | 690  | 580  | 48.276    | 34.821  | 45.841  | 50    | yes      | 20.037   |
| 1020-CD    | 20C8         | 470  | 390  | 53.097    | 39.494  | 45.841  | 55    | yes      | 20.515   |
| 1040-HR    | 40C8         | 520  | 290  | 51.764    | 43.664  | 45.841  | 55    | yes      | 20.515   |
| 1030-CD    | 30C8         | 520  | 440  | 51.764    | 37.999  | 45.841  | 55    | yes      | 21.448   |
| 1045-HR    | 45C8         | 570  | 310  | 50.599    | 42.769  | 45.841  | 55    | yes      | 21.448   |
| 1035-CD    | 35C8         | 550  | 460  | 51.041    | 37.475  | 45.841  | 55    | yes      | 22.007   |
| 1020-HR    | 20C8         | 380  | 210  | 56.037    | 48.395  | 45.841  | 60    | yes      | 22.195   |
| 1040-CD    | 40C8         | 590  | 490  | 50.171    | 36.737  | 45.841  | 55    | yes      | 22.380   |
| 4140-N     | 42Cr4Mo2     | 1020 | 655  | 43.825    | 33.633  | 45.841  | 50    | yes      | 30.827   |
| 4340-QT540 | 40Ni2Cr1Mo28 | 1170 | 1080 | 42.342    | 28.514  | 45.841  | 50    | yes      | 43.158   |
| SS304      | X04Cr18Ni10  | 515  | 205  | 51.890    | 49.008  | 46.783  | 55    | yes      | 85.530   |

```text
  Selected: AISI 1060 hot-rolled (60C4) - cheapest feasible option.
```

| Property                      | Value                       |
|-------------------------------|-----------------------------|
| Material                      | AISI 1060 hot-rolled (60C4) |
| Ultimate tensile strength Sut | 680 MPa                     |
| Yield strength Syt            | 370 MPa                     |
| Modulus of elasticity E       | 207 GPa                     |
| Modulus of rigidity G         | 79.300 GPa                  |
| Density                       | 7850 kg/m^3                 |
| Elongation / hardness         | 12 % / 201 BHN              |

## Step 4 - Endurance limit (Marin equation  Se = ka kb kc kd ke Se')

```text
  Specimen endurance limit Se'         = 0.5 x Sut = 340 MPa
  Surface factor ka (machined)         = 4.51 x Sut^(-0.265) = 0.8009
  Size factor kb                       = depends on d - see iteration in step 6
  Load factor kc (combined, von Mises) = 1
  Temperature factor kd (25 C)         = 1
  Reliability factor ke (90 %)         = 0.8970
  Se without kb                        = ka kc kd ke Se' = 244.2 MPa
```

## Step 5 - Stress concentration at the critical section

```text
  Shoulder fillet, well rounded (r/d = 0.1)
  Theoretical factor, bending Kt       = 1.700
  Theoretical factor, torsion Kts      = 1.500
  Notch radius ratio r/d               = 0.1000
  Notch sensitivity (Neuber): q = 1/(1 + sqrt(a)/sqrt(r)),  Kf = 1 + q(Kt - 1)
  q depends on r = (r/d) x d, so Kf and Kfs are updated in the iteration below.
```

## Step 6 - Fatigue diameter (DE-Goodman)

```text
  A = sqrt(4(Kf Ma)^2 + 3(Kfs Ta)^2),  B = sqrt(4(Kf Mm)^2 + 3(Kfs Tm)^2)
  d = [ 16n/pi * ( A/Se + B/Sut ) ]^(1/3)
  Start with kb = 1 and Kf = Kt, then repeat until d stops changing:
```

| Iter | d assumed (mm) | kb     | q      | qs     | Kf    | Kfs   | Se (MPa) | d new (mm) |
|------|----------------|--------|--------|--------|-------|-------|----------|------------|
| 1    | 46.522         | 0.8222 | 0.8708 | 0.8989 | 1.610 | 1.449 | 200.8    | 48.374     |
| 2    | 48.374         | 0.8188 | 0.8730 | 0.9006 | 1.611 | 1.450 | 200.0    | 48.446     |
| 3    | 48.446         | 0.8187 | 0.8731 | 0.9007 | 1.611 | 1.450 | 200.0    | 48.449     |
| 4    | 48.449         | 0.8186 | 0.8731 | 0.9007 | 1.611 | 1.450 | 200.0    | 48.449     |

```text
  Fatigue diameter d_f                 = 48.449 mm
```

## Step 7 - First-cycle yield check (static, peak load)

```text
  sigma'_max = (16/(pi d^3)) sqrt(4(Kf Mmax)^2 + 3(Kfs Tmax)^2) <= Syt / n
  Peak bending moment |Mm| + Ma        = 580.6 N.m
  Peak torque |Tm| + Ta                = 600 N.m
  Yield diameter d_y                   = 40.440 mm
```

## Step 8 - Torsional rigidity (angle of twist constraint)

```text
  theta = T L / (G J),  J = pi d^4 / 32   =>   d = [32 T L / (pi G theta)]^(1/4)
  Allowable twist theta                = 1 deg = 0.0175 rad
  Rigidity diameter d_t                = 45.841 mm
```

## Step 9 - Required diameter, standard size and diameter constraint

```text
  Required d = max(d_f, d_y, d_t)      = 48.449 mm
  Governing requirement: fatigue
  Next standard shaft diameter         = 50 mm
  [ OK ] d = 50 mm <= d_max = 60 mm
```

## Step 10 - Verification of the standard shaft

```text
  kb, Kf, Kfs at final d               = 0.8159, 1.612, 1.451
  Endurance limit Se                   = 199.3 MPa
  Alternating bending stress sigma_a   = Kf 32 Ma/(pi d^3) = 76.278 MPa
  Mean bending stress sigma_m          = Kf 32 Mm/(pi d^3) = 0 MPa
  Alternating shear stress tau_a       = Kfs 16 Ta/(pi d^3) = 11.824 MPa
  Mean shear stress tau_m              = Kfs 16 Tm/(pi d^3) = 23.648 MPa
  von Mises alternating sigma'_a       = sqrt(sa^2 + 3 ta^2) = 78.980 MPa
  von Mises mean sigma'_m              = sqrt(sm^2 + 3 tm^2) = 40.960 MPa
  Fatigue factor of safety (DE-Goodman) = 2.190
  Yield factor of safety Syt/sigma'_max = 3.778
  Angle of twist                       = 0.7065 deg
  [ OK ] Fatigue FoS 2.190 >= required 2
  [ OK ] Yield FoS 3.778 >= required 2
  [ OK ] Twist 0.7065 deg <= allowed 1 deg
  [ OK ] Diameter 50 mm <= d_max 60 mm
```

## FINAL OUTPUT

```text
  Standard shaft: diameter 50 mm, AISI 1060 hot-rolled (60C4)
```

| Output                    | Value                       |
|---------------------------|-----------------------------|
| Shaft diameter (standard) | 50 mm                       |
| Material                  | AISI 1060 hot-rolled (60C4) |
| Sut / Syt                 | 680 / 370 MPa               |
| Fatigue factor of safety  | 2.190                       |
| Yield factor of safety    | 3.778                       |
| Angle of twist            | 0.7065 deg over 1000 mm     |
| Mass per metre            | 15.413 kg/m                 |
| Governing requirement     | fatigue                     |

