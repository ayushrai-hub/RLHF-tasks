# A suite mixing both test kinds, with comments and blank lines between blocks.

test categories chisq_gof
ddof 0
observed 30 28 34 26 32
expected 30 30 30 30 30
end


# Fitted model consumed two parameters, so drop two extra degrees of freedom.
test model_fit chisq_gof
ddof 2
observed 9 14 20 22 18 12 5
expected 7 13 21 24 17 10 8
end

test ab_compare welch_t
sample_a 5.1 4.9 6.2 5.7 5.5 6.0 5.3
sample_b 4.2 4.8 3.9 4.5 4.1 4.7
end

# Is this sample consistent with N(5, 0.7)?
test normality ks_normal
sample 4.1 5.2 4.8 6.0 5.5 4.9 5.1 5.8 4.4 5.0 6.2 4.7
mu 5.0
sigma 0.7
end
