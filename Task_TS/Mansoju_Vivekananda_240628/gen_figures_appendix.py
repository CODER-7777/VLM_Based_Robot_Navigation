import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm

plt.rcParams.update({"font.size": 10, "axes.grid": True,
                      "grid.alpha": 0.3, "figure.dpi": 150})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"figures/{name}.png")
    plt.close(fig)

# To geT Fig 1: logit vs probit link functions
z = np.linspace(-6, 6, 400)
fig, ax = plt.subplots(figsize=(5, 3.3))
ax.plot(z, 1/(1+np.exp(-z)), label="Logistic CDF (logit)",
        color="#1f77b4", lw=2)
ax.plot(z, norm.cdf(z), label="Normal CDF (probit)",
        color="#d62728", lw=2)
ax.set(xlabel=r"$\eta=X\beta$", ylabel=r"$P(y=1\mid\eta)$",
       title="Logit vs. Probit Link Functions")
ax.legend(fontsize=8)
save(fig, "link_comparison")

# To get Fig 2: latent-variable view of probit
x = np.linspace(-4, 4, 400)
density = norm.pdf(x, loc=1.2, scale=1.0)
fig, ax = plt.subplots(figsize=(5, 3.2))
ax.plot(x, density, color="#2ca02c", lw=2)
ax.fill_between(x, 0, density, where=(x >= 0), alpha=0.3,
                color="#2ca02c", label=r"$y=1$ ($y^*>0$)")
ax.fill_between(x, 0, density, where=(x < 0), alpha=0.15,
                color="gray", label=r"$y=0$ ($y^*\leq 0$)")
ax.axvline(0, color="black", ls="--", lw=1)
ax.set(xlabel=r"$y^*=X\beta+\varepsilon,\ \varepsilon\sim N(0,1)$",
       ylabel="Density", title="Latent-Variable View of Probit")
ax.legend(fontsize=8, loc="upper left")
save(fig, "latent_variable")

# To get Fig 3: illustrative IRLS convergence
iters = np.arange(7)
loglik = [-13.86, -8.12, -6.05, -5.41, -5.30, -5.29, -5.29]
fig, ax = plt.subplots(figsize=(5, 3.2))
ax.plot(iters, loglik, marker="o", color="#9467bd", lw=2)
ax.set(xlabel="IRLS Iteration", ylabel="Log-likelihood",
       title="Typical IRLS Convergence")
save(fig, "irls_convergence")

# To get Fig 4: Bayesian prior -> Laplace-approx posterior
beta = np.linspace(-3, 5, 400)
fig, ax = plt.subplots(figsize=(5, 3.2))
ax.plot(beta, norm.pdf(beta, 0, 1.5), "--", color="#7f7f7f",
        lw=2, label=r"Prior $p(\beta)$")
ax.plot(beta, norm.pdf(beta, 1.8, 0.5), color="#e377c2",
        lw=2, label=r"Posterior $p(\beta\mid y)$")
ax.set(xlabel=r"$\beta_1$", ylabel="Density",
       title="Bayesian Update: Prior vs. Posterior")
ax.legend(fontsize=8)
save(fig, "bayes_prior_posterior")
