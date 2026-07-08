# Replicate combination

`combine` combines replicate determinations before calibration. It has fields:

```json
{
  "kind": "combine",
  "determinations": [
    {
      "age_bp": 2110.0,
      "sigma": 25.0,
      "reservoir_age": 20.0,
      "reservoir_sigma": 8.0
    }
  ]
}
```

There must be between 1 and 11 determinations. For each determination:

```text
corrected_age = age_bp - reservoir_age
combined_variance = sigma^2 + reservoir_sigma^2
```

`sigma` must be greater than zero and `reservoir_sigma` must be zero or greater.
The output age is the inverse-variance weighted mean of the corrected ages. The
output sigma is `sqrt(1 / sum(weights))`, where each weight is
`1 / combined_variance`.

For multiple determinations, report:

```text
chi_square = sum(weight_i * (corrected_age_i - weighted_mean)^2)
dof = number_of_determinations - 1
```

The `passes` field is true when `chi_square` is no larger than the 95% chi-square
critical value for `dof`. For one determination, `chi_square` is 0, `dof` is 0,
and `passes` is true.

Critical values:

```text
dof 1:  3.841458820694124
dof 2:  5.991464547107979
dof 3:  7.814727903251179
dof 4:  9.487729036781154
dof 5:  11.070497693516351
dof 6:  12.591587243743977
dof 7:  14.067140449340169
dof 8:  15.50731305586545
dof 9:  16.918977604620448
dof 10: 18.307038053275146
```

The output is:

```json
{"age_bp": 2091.4, "sigma": 14.1, "chi_square": 1.2, "dof": 2, "passes": true}
```
