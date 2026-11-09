# CODING 2 - DESIGN OF A RIGID FLANGED COUPLING (STATIC TORQUE)

## Step 0 - Input data

| Item                           | Value              |
|--------------------------------|--------------------|
| Torque to be transmitted       | 15 kW at 900 rpm   |
| Service factor                 | 1.350              |
| FoS steel parts / flange       | 3 / 6              |
| Shaft material                 | 1030-HR            |
| Key / bolt material            | same / same        |
| Flange material                | FG200              |
| Constraint: max shaft diameter | 100 mm             |
| Constraint: max angle of twist | 5 deg over 1000 mm |

## Step 1 - Design torque

```text
  Rated torque T                       = 60 x 10^6 P / (2 pi n) / 10^3 = 159.2 N.m
  Design torque Td                     = 1.350 x T = 214.9 N.m
```

## Step 2 - Shaft material and permissible stresses

| Part   | Material                               | Sut / Syt (MPa) | Permissible stresses (MPa) | Source         |
|--------|----------------------------------------|-----------------|----------------------------|----------------|
| Shaft  | AISI 1030 hot-rolled (30C8)            | 470 / 260       | tau = 40                   | user specified |
| Key    | AISI 1030 hot-rolled (30C8)            | 470 / 260       | tau = 40, sigma_c = 80     | user specified |
| Bolts  | AISI 1030 hot-rolled (30C8)            | 470 / 260       | tau = 40, sigma_c = 80     | user specified |
| Flange | Grey cast iron FG 200 (FG200 (IS 210)) | 200 / -         | tau = 8                    | user specified |

```text
  Ductile parts: tau = 0.5 Syt / n (max. shear stress theory), sigma_c = Syt / n.
  Cast-iron flange: tau = 0.5 Sut / n_flange (no yield point).
```

## Step 3 - Shaft diameter

```text
  Strength: d = (16 Td / (pi tau))^(1/3) = 30.132 mm
  Rigidity: d = (32 Td L / (pi G theta))^(1/4) = 23.714 mm
  Required diameter                    = 30.132 mm
  Standard shaft diameter d            = 35 mm
  [ OK ] d = 35 mm <= d_max = 100 mm
  Shear stress in shaft                = 16 Td/(pi d^3) = 25.522 MPa
  [ OK ] tau = 25.522 MPa <= 40 MPa
  Angle of twist                       = 1.054 deg
  [ OK ] theta = 1.054 deg <= 5 deg
```

## Step 4 - Hub (D = 2d, L = 1.5d)

```text
  Hub outer diameter D                 = 2d = 70 mm
  Hub as hollow shaft: tau             = 16 Td D / (pi (D^4 - d^4)) = 3.403 MPa
  [ OK ] hub tau = 3.403 MPa <= 8 MPa
```

## Step 5 - Key (parallel key, IS 2048)

```text
  Key width x height (from table)      = 10 x 8 mm
  Length for shear  2Td/(d b tau)      = 30.694 mm
  Length for crushing  4Td/(d h sigma_c) = 38.368 mm
  Hub length = key length              = max(1.5d, 30.694, 38.368) -> standard = 56 mm
  Key shear stress                     = 21.924 MPa
  Key crushing stress                  = 54.811 MPa
  [ OK ] key tau = 21.924 MPa <= 40 MPa
  [ OK ] key sigma_c = 54.811 MPa <= 80 MPa
```

## Step 6 - Flange

```text
  Pitch circle diameter of bolts D1    = 3d = 105 mm
  Outer diameter of flange D2          = 4d = 140 mm
  Flange thickness t                   = 0.5d = 18 mm
  Protective rim thickness t1          = 0.25d = 9 mm
  Flange shear at hub  2Td/(pi D^2 t)  = 1.551 MPa
  [ OK ] flange tau = 1.551 MPa <= 8 MPa
```

## Step 7 - Bolts (fitted in reamed holes, shank in shear)

```text
  Rule: N = 3 for d <= 40 mm, 4 for d <= 100 mm, 6 for d <= 180 mm, else 8
  Number of bolts N                    = 3
  Bolt diameter for shear              = sqrt(8 Td / (pi tau N D1)) = 6.590 mm
  Smallest first-choice ISO coarse bolt >= required size (minimum M6), crushing checked:
  Selected bolt                        = M8 (pitch 1.250 mm)
  Bolt shear stress                    = 27.140 MPa
  Bolt crushing stress  2Td/(N d1 t D1) = 9.474 MPa
  [ OK ] bolt tau = 27.140 MPa <= 40 MPa
  [ OK ] bolt sigma_c = 9.474 MPa <= 80 MPa
  [ OK ] room for bolt head between hub and PCD: 17.500 mm >= 7.506 mm
  [ OK ] room for bolt head between PCD and flange OD: 17.500 mm >= 7.506 mm
  Bolt length  2t + washer + nut + 2P  = 46.900 mm
  Standard bolt length                 = 50 mm
```

## FINAL OUTPUT - Dimensions of the coupling

| Part   | Dimension                   | Value                       |
|--------|-----------------------------|-----------------------------|
| Shaft  | Diameter d                  | 35 mm  (1030-HR / 30C8)     |
| Hub    | Outer diameter D            | 70 mm                       |
| Hub    | Length L                    | 56 mm                       |
| Key    | b x h x l                   | 10 x 8 x 56 mm  (1030-HR)   |
| Flange | Pitch circle diameter D1    | 105 mm                      |
| Flange | Outer diameter D2           | 140 mm                      |
| Flange | Thickness t                 | 18 mm  (FG200)              |
| Flange | Protective rim thickness t1 | 9 mm                        |
| Bolts  | Number x size               | 3 x M8 x 50 long  (1030-HR) |
| Torque | Design torque Td            | 214.9 N.m                   |

```text
  All checks passed: YES
```
