# Ricochet contract

When a layer stops the projectile (`depth < thickness`), compute the reflected velocity:

```
v_out = v - 2 × dot(v, n) × n
```

where **v** is the incident velocity toward the stack and **n** is the stack normal.

Export:

- `incident_angle_deg` — angle between **v** and **−n**
- `exit_angle_deg` — angle between **v_out** and **n**
- `velocity_out` — components of **v_out**

Do not export the incident vector as the exit vector. Angles are rounded to three decimal places in JSON.
