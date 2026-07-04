# One-sample Kolmogorov-Smirnov normality checks at a tighter alpha.
alpha 0.01

test batch_a ks_normal
sample 9.8 10.1 9.9 10.3 10.0 9.7 10.2 9.6 10.4 10.0 9.9 10.1
mu 10.0
sigma 0.25
end

test batch_b ks_normal
sample 1.2 4.8 2.1 9.9 0.3 7.7 5.5 3.3 8.8 6.1
mu 5.0
sigma 1.0
end
