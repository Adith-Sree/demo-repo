# CODING 2 - DESIGN OF A RIGID FLANGED COUPLING (STATIC TORQUE)

## Step 0 - Input data

| Item                           | Value               |
|--------------------------------|---------------------|
| Torque to be transmitted       | 1000 N.m            |
| Service factor                 | 1.250               |
| FoS steel parts / flange       | 3 / 6               |
| Shaft material                 | automatic selection |
| Key / bolt material            | same / same         |
| Flange material                | FG200               |
| Constraint: max shaft diameter | 80 mm               |
| Constraint: max angle of twist | 1 deg over 1000 mm  |

## Step 1 - Design torque

```text
  Rated torque T                       = 1000 N.m
  Design torque Td                     = 1.250 x T = 1250 N.m
```

## Step 2 - Shaft material and permissible stresses

```text
  Each shaft material is sized for strength and twist; the cheapest feasible one is chosen.
```

| Material   | IS           | Syt  | tau perm | d strength | d twist | d std | Feasible | Cost idx |
|------------|--------------|------|----------|------------|---------|-------|----------|----------|
| 1020-HR    | 20C8         | 210  | 35       | 56.659     | 55.073  | 60    | yes      | 22.195   |
| 1030-HR    | 30C8         | 260  | 43.333   | 52.766     | 55.073  | 60    | yes      | 23.305   |
| 1020-CD    | 20C8         | 390  | 65       | 46.095     | 55.073  | 60    | yes      | 24.415   |
| 1040-HR    | 40C8         | 290  | 48.333   | 50.880     | 55.073  | 60    | yes      | 24.415   |
| 1030-CD    | 30C8         | 440  | 73.333   | 44.278     | 55.073  | 60    | yes      | 25.525   |
| 1045-HR    | 45C8         | 310  | 51.667   | 49.761     | 55.073  | 60    | yes      | 25.525   |
| 1035-CD    | 35C8         | 460  | 76.667   | 43.627     | 55.073  | 60    | yes      | 26.191   |
| 1040-CD    | 40C8         | 490  | 81.667   | 42.718     | 55.073  | 60    | yes      | 26.634   |
| 1045-CD    | 45C8         | 530  | 88.333   | 41.615     | 55.073  | 60    | yes      | 27.744   |
| 1060-HR    | 60C4         | 370  | 61.667   | 46.911     | 55.073  | 60    | yes      | 27.744   |
| 1050-CD    | 50C4         | 580  | 96.667   | 40.383     | 55.073  | 60    | yes      | 28.854   |
| 4140-N     | 42Cr4Mo2     | 655  | 109.2    | 38.779     | 55.073  | 60    | yes      | 44.391   |
| 4340-QT540 | 40Ni2Cr1Mo28 | 1080 | 180      | 32.825     | 55.073  | 60    | yes      | 62.147   |
| SS304      | X04Cr18Ni10  | 205  | 34.167   | 57.116     | 56.206  | 60    | yes      | 101.8    |

| Part   | Material                               | Sut / Syt (MPa) | Permissible stresses (MPa) | Source        |
|--------|----------------------------------------|-----------------|----------------------------|---------------|
| Shaft  | AISI 1020 hot-rolled (20C8)            | 380 / 210       | tau = 35                   | from material |
| Key    | AISI 1020 hot-rolled (20C8)            | 380 / 210       | tau = 35, sigma_c = 70     | from material |
| Bolts  | AISI 1020 hot-rolled (20C8)            | 380 / 210       | tau = 35, sigma_c = 70     | from material |
| Flange | Grey cast iron FG 200 (FG200 (IS 210)) | 200 / -         | tau = 16.667               | from material |

```text
  Ductile parts: tau = 0.5 Syt / n (max. shear stress theory), sigma_c = Syt / n.
  Cast-iron flange: tau = 0.5 Sut / n_flange (no yield point).
```

## Step 3 - Shaft diameter

```text
  Strength: d = (16 Td / (pi tau))^(1/3) = 56.659 mm
  Rigidity: d = (32 Td L / (pi G theta))^(1/4) = 55.073 mm
  Required diameter                    = 56.659 mm
  Standard shaft diameter d            = 60 mm
  [ OK ] d = 60 mm <= d_max = 80 mm
  Shear stress in shaft                = 16 Td/(pi d^3) = 29.473 MPa
  [ OK ] tau = 29.473 MPa <= 35 MPa
  Angle of twist                       = 0.7098 deg
  [ OK ] theta = 0.7098 deg <= 1 deg
```

## Step 4 - Hub (D = 2d, L = 1.5d)

```text
  Hub outer diameter D                 = 2d = 120 mm
  Hub as hollow shaft: tau             = 16 Td D / (pi (D^4 - d^4)) = 3.930 MPa
  [ OK ] hub tau = 3.930 MPa <= 16.667 MPa
```

## Step 5 - Key (parallel key, IS 2048)

```text
  Key width x height (from table)      = 18 x 11 mm
  Length for shear  2Td/(d b tau)      = 66.138 mm
  Length for crushing  4Td/(d h sigma_c) = 108.2 mm
  Hub length = key length              = max(1.5d, 66.138, 108.2) -> standard = 110 mm
  Key shear stress                     = 21.044 MPa
  Key crushing stress                  = 68.871 MPa
  [ OK ] key tau = 21.044 MPa <= 35 MPa
  [ OK ] key sigma_c = 68.871 MPa <= 70 MPa
```

## Step 6 - Flange

```text
  Pitch circle diameter of bolts D1    = 3d = 180 mm
  Outer diameter of flange D2          = 4d = 240 mm
  Flange thickness t                   = 0.5d = 30 mm
  Protective rim thickness t1          = 0.25d = 15 mm
  Flange shear at hub  2Td/(pi D^2 t)  = 1.842 MPa
  [ OK ] flange tau = 1.842 MPa <= 16.667 MPa
```

## Step 7 - Bolts (fitted in reamed holes, shank in shear)

```text
  Rule: N = 3 for d <= 40 mm, 4 for d <= 100 mm, 6 for d <= 180 mm, else 8
  Number of bolts N                    = 4
  Bolt diameter for shear              = sqrt(8 Td / (pi tau N D1)) = 11.239 mm
  Smallest first-choice ISO coarse bolt >= required size (minimum M6), crushing checked:
  Selected bolt                        = M12 (pitch 1.750 mm)
  Bolt shear stress                    = 30.701 MPa
  Bolt crushing stress  2Td/(N d1 t D1) = 9.645 MPa
  [ OK ] bolt tau = 30.701 MPa <= 35 MPa
  [ OK ] bolt sigma_c = 9.645 MPa <= 70 MPa
  [ OK ] room for bolt head between hub and PCD: 30 mm >= 10.392 mm
  [ OK ] room for bolt head between PCD and flange OD: 30 mm >= 10.392 mm
  Bolt length  2t + washer + nut + 2P  = 76.800 mm
  Standard bolt length                 = 80 mm
```

## FINAL OUTPUT - Dimensions of the coupling

| Part   | Dimension                   | Value                        |
|--------|-----------------------------|------------------------------|
| Shaft  | Diameter d                  | 60 mm  (1020-HR / 20C8)      |
| Hub    | Outer diameter D            | 120 mm                       |
| Hub    | Length L                    | 110 mm                       |
| Key    | b x h x l                   | 18 x 11 x 110 mm  (1020-HR)  |
| Flange | Pitch circle diameter D1    | 180 mm                       |
| Flange | Outer diameter D2           | 240 mm                       |
| Flange | Thickness t                 | 30 mm  (FG200)               |
| Flange | Protective rim thickness t1 | 15 mm                        |
| Bolts  | Number x size               | 4 x M12 x 80 long  (1020-HR) |
| Torque | Design torque Td            | 1250 N.m                     |

```text
  All checks passed: YES
```
