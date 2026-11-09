# CODING 1 - DESIGN OF A POWER TRANSMISSION SHAFT (FLUCTUATING LOADS)

## Step 0 - Input data

| Item                              | Value                         |
|-----------------------------------|-------------------------------|
| Bending moment, max / min         | 600 / 200 N.m                 |
| Bending stress cycle              | as given by Mmax / Mmin       |
| Torque, max / min                 | 600 / 200 N.m                 |
| Factor of safety n                | 2                             |
| Fatigue criterion                 | DE-Soderberg                  |
| Surface finish                    | machined                      |
| Reliability                       | 99 %                          |
| Operating temperature             | 25 C                          |
| Stress raiser at critical section | End-mill keyseat (r/d = 0.02) |
| Constraint: max shaft diameter    | 80 mm                         |
| Constraint: max angle of twist    | 1 deg over 800 mm             |
| Material                          | AISI 1045 cold-drawn (45C8)   |

## Step 1 - Bending moment at the critical section

```text
  Mmax                                 = 600 N.m
  Mmin                                 = 200 N.m
```

## Step 2 - Mean and alternating components

```text
  Mean bending moment Mm               = (Mmax + Mmin)/2 = 400 N.m
  Alternating bending moment Ma        = (Mmax - Mmin)/2 = 200 N.m
  Mean torque Tm                       = (Tmax + Tmin)/2 = 400 N.m
  Alternating torque Ta                = (Tmax - Tmin)/2 = 200 N.m
```

## Step 3 - Material selection (materials database)

| Property                      | Value                       |
|-------------------------------|-----------------------------|
| Material                      | AISI 1045 cold-drawn (45C8) |
| Ultimate tensile strength Sut | 630 MPa                     |
| Yield strength Syt            | 530 MPa                     |
| Modulus of elasticity E       | 207 GPa                     |
| Modulus of rigidity G         | 79.300 GPa                  |
| Density                       | 7850 kg/m^3                 |
| Elongation / hardness         | 12 % / 179 BHN              |

## Step 4 - Endurance limit (Marin equation  Se = ka kb kc kd ke Se')

```text
  Specimen endurance limit Se'         = 0.5 x Sut = 315 MPa
  Surface factor ka (machined)         = 4.51 x Sut^(-0.265) = 0.8172
  Size factor kb                       = depends on d - see iteration in step 6
  Load factor kc (combined, von Mises) = 1
  Temperature factor kd (25 C)         = 1
  Reliability factor ke (99 %)         = 0.8140
  Se without kb                        = ka kc kd ke Se' = 209.5 MPa
```

## Step 5 - Stress concentration at the critical section

```text
  End-mill keyseat (r/d = 0.02)
  Theoretical factor, bending Kt       = 2.140
  Theoretical factor, torsion Kts      = 3
  Notch radius ratio r/d               = 0.0200
  Notch sensitivity (Neuber): q = 1/(1 + sqrt(a)/sqrt(r)),  Kf = 1 + q(Kt - 1)
  q depends on r = (r/d) x d, so Kf and Kfs are updated in the iteration below.
```

## Step 6 - Fatigue diameter (DE-Soderberg)

```text
  A = sqrt(4(Kf Ma)^2 + 3(Kfs Ta)^2),  B = sqrt(4(Kf Mm)^2 + 3(Kfs Tm)^2)
  d = [ 16n/pi * ( A/Se + B/Syt ) ]^(1/3)
  Start with kb = 1 and Kf = Kt, then repeat until d stops changing:
```

| Iter | d assumed (mm) | kb     | q      | qs     | Kf    | Kfs   | Se (MPa) | d new (mm) |
|------|----------------|--------|--------|--------|-------|-------|----------|------------|
| 1    | 48.937         | 0.9096 | 0.7364 | 0.7874 | 1.839 | 2.575 | 190.6    | 47.362     |
| 2    | 47.362         | 0.9128 | 0.7332 | 0.7847 | 1.836 | 2.569 | 191.3    | 47.297     |
| 3    | 47.297         | 0.9129 | 0.7331 | 0.7845 | 1.836 | 2.569 | 191.3    | 47.294     |
| 4    | 47.294         | 0.9129 | 0.7331 | 0.7845 | 1.836 | 2.569 | 191.3    | 47.294     |

```text
  Fatigue diameter d_f                 = 47.294 mm
```

## Step 7 - First-cycle yield check (static, peak load)

```text
  sigma'_max = (16/(pi d^3)) sqrt(4(Kf Mmax)^2 + 3(Kfs Tmax)^2) <= Syt / n
  Peak bending moment |Mm| + Ma        = 600 N.m
  Peak torque |Tm| + Ta                = 600 N.m
  Yield diameter d_y                   = 40.519 mm
```

## Step 8 - Torsional rigidity (angle of twist constraint)

```text
  theta = T L / (G J),  J = pi d^4 / 32   =>   d = [32 T L / (pi G theta)]^(1/4)
  Allowable twist theta                = 1 deg = 0.0175 rad
  Rigidity diameter d_t                = 43.353 mm
```

## Step 9 - Required diameter, standard size and diameter constraint

```text
  Required d = max(d_f, d_y, d_t)      = 47.294 mm
  Governing requirement: fatigue
  Next standard shaft diameter         = 50 mm
  [ OK ] d = 50 mm <= d_max = 80 mm
```

## Step 10 - Verification of the standard shaft

```text
  kb, Kf, Kfs at final d               = 0.9075, 1.842, 2.578
  Endurance limit Se                   = 190.2 MPa
  Alternating bending stress sigma_a   = Kf 32 Ma/(pi d^3) = 30.018 MPa
  Mean bending stress sigma_m          = Kf 32 Mm/(pi d^3) = 60.035 MPa
  Alternating shear stress tau_a       = Kfs 16 Ta/(pi d^3) = 21.011 MPa
  Mean shear stress tau_m              = Kfs 16 Tm/(pi d^3) = 42.022 MPa
  von Mises alternating sigma'_a       = sqrt(sa^2 + 3 ta^2) = 47.174 MPa
  von Mises mean sigma'_m              = sqrt(sm^2 + 3 tm^2) = 94.349 MPa
  Fatigue factor of safety (DE-Soderberg) = 2.347
  Yield factor of safety Syt/sigma'_max = 3.745
  Angle of twist                       = 0.5652 deg
  [ OK ] Fatigue FoS 2.347 >= required 2
  [ OK ] Yield FoS 3.745 >= required 2
  [ OK ] Twist 0.5652 deg <= allowed 1 deg
  [ OK ] Diameter 50 mm <= d_max 80 mm
```

## FINAL OUTPUT

```text
  Standard shaft: diameter 50 mm, AISI 1045 cold-drawn (45C8)
```

| Output                    | Value                       |
|---------------------------|-----------------------------|
| Shaft diameter (standard) | 50 mm                       |
| Material                  | AISI 1045 cold-drawn (45C8) |
| Sut / Syt                 | 630 / 530 MPa               |
| Fatigue factor of safety  | 2.347                       |
| Yield factor of safety    | 3.745                       |
| Angle of twist            | 0.5652 deg over 800 mm      |
| Mass per metre            | 15.413 kg/m                 |
| Governing requirement     | fatigue                     |

