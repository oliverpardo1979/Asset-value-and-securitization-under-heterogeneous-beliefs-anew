# Revision report

## Executive summary

I converted the manuscript from the old `ectaart` format to standard `article`, restored the motivating example to the active text, cleaned several drafting errors, updated the literature review, and corrected a mathematical typo in the proof of the equivalence between iterated securitization and a direct tranching.

The paper still reads as a promising theory paper, but it needs one more full pass before journal submission: the main novelty should be stated more sharply against Fostel-Geanakoplos, Simsek, DeMarzo, and the recent credit-sentiment literature, and Lemma `prp:nUcon` should be expanded into a more formal proof.

## Files changed

- `main.tex`
- `Bibliography.bib`
- `REVISION_REPORT.md`

## Main code and LaTeX changes

- Replaced `\documentclass{ectaart}` with `\documentclass[11pt]{article}`.
- Removed old `frontmatter`, `aug`, `thankstext`, `printead`, `startlocaldefs`, and `hypernat` dependencies.
- Added standard packages and metadata compatible with common LaTeX installations.
- Added JEL codes and keywords under the abstract.
- Restored the motivating example, which had been hidden inside a `comment` environment even though later sections referenced it.
- Changed the bibliography style to `plainnat` and placed `\bibliographystyle{plainnat}` before `\bibliography{Bibliography}`.
- Cleaned duplicate/commented labels that confused static checks.
- Verified active labels, references, and citations with static checks.

## Writing changes

- Rewrote the abstract in cleaner, more direct English.
- Tightened the introduction and literature review.
- Removed duplicated paragraphs in the introduction.
- Corrected drafting errors such as "return of none", "the any owner", "many motivation", "right hand side", "lesser", "in turns", "can be show", and "demand of".
- Improved wording in the model setup, equilibrium discussion, and conclusion.
- Clarified that the set of theories is finite.

## Literature added

I added only papers with a clear connection to the mechanism in the manuscript: heterogeneous beliefs, collateralized promises, financial innovation, tranching/security design, credit sentiment, and neglected risk.

- Geanakoplos and Zame (2014), "Collateral Equilibrium: I: A Basic Framework", Economic Theory. Useful for positioning the model in collateral-equilibrium theory. DOI: https://doi.org/10.1007/s00199-013-0797-4
- Fostel and Geanakoplos (2016), "Financial Innovation, Collateral, and Investment", AEJ: Macroeconomics. Directly connected to financial innovation and collateralizable promises. DOI: https://doi.org/10.1257/mac.20130183
- Gennaioli, Shleifer and Vishny (2012), "Neglected Risks, Financial Innovation, and Financial Fragility", Journal of Financial Economics. Older than the requested ten-year window, but directly connected to financial innovation and neglected risk. DOI: https://doi.org/10.1016/j.jfineco.2011.05.005 ; NBER: https://www.nber.org/papers/w16068
- Baron and Xiong (2017), "Credit Expansion and Neglected Crash Risk", Quarterly Journal of Economics. Supports the neglected-risk/credit-boom motivation. DOI: https://doi.org/10.1093/qje/qjx004 ; NBER: https://www.nber.org/papers/w22695
- Lopez-Salido, Stein and Zakrajsek (2017), "Credit-Market Sentiment and the Business Cycle", Quarterly Journal of Economics. Supports the empirical link between credit-market sentiment and subsequent reversals. DOI: https://doi.org/10.1093/qje/qjx014 ; NBER: https://www.nber.org/papers/w21879
- Bordalo, Gennaioli and Shleifer (2018), "Diagnostic Expectations and Credit Cycles", Journal of Finance. Useful behavioral-credit-cycle reference. DOI: https://doi.org/10.1111/jofi.12586 ; NBER: https://www.nber.org/papers/w22266
- Greenwood, Hanson, Shleifer and Sorensen (2022), "Predictable Financial Crises", Journal of Finance. Connects rapid credit and asset-price growth to subsequent financial crises. DOI: https://doi.org/10.1111/jofi.13105 ; NBER: https://www.nber.org/papers/w27396
- Maxted (2024), "A Macro-Finance Model with Sentiment", Review of Economic Studies. Connects diagnostic expectations, financial intermediation, neglected risk, and boom-bust investment cycles. DOI: https://doi.org/10.1093/restud/rdad023
- Krishnamurthy and Li (2025), "Dissecting Mechanisms of Financial Crises: Intermediation and Sentiment", Journal of Political Economy. Useful for separating intermediary balance-sheet channels from sentiment channels. DOI: https://doi.org/10.1086/733423 ; NBER: https://www.nber.org/papers/w27088
- Krishnamurthy and Muir (2025), "How Credit Cycles across a Financial Crisis", Journal of Finance. Shows that low pre-crisis spreads and rapid credit growth precede severe reversals. DOI: https://doi.org/10.1111/jofi.13431 ; NBER: https://www.nber.org/papers/w23850
- Bordalo, Gennaioli, Shleifer and Terry (2026), "Real Credit Cycles", American Economic Review. Very recent and directly relevant to diagnostic expectations, risky debt, credit cycles, bond returns, and investment reversals. DOI: https://doi.org/10.1257/aer.20211820 ; NBER: https://www.nber.org/papers/w28416
- Begley and Purnanandam (2017), "Design of Financial Securities: Empirical Evidence from Private-Label RMBS Deals", Review of Financial Studies. Direct empirical evidence on RMBS deal design and tranching. DOI: https://doi.org/10.1093/rfs/hhw056
- DeMarzo (2005), "The Pooling and Tranching of Securities", Review of Financial Studies. Older classic, but central for any paper on tranching. DOI: https://doi.org/10.1093/rfs/hhi008

I did not add every recent securitization, credit-cycle, or heterogeneous-beliefs paper. For example, I did not add Malamud's moral-hazard securitization paper because it is less directly tied to the paper's main heterogeneous-beliefs and waterfall-tranching results. I also left out some strong but more lateral collateral-boom papers, such as Asriyan, Laeven and Martin (2022), because they are about collateral and information production rather than belief disagreement and securitized cash-flow slicing.

## Mathematical and proof review

I found and corrected one real mathematical typo:

- In the proof of the equivalence between iterated securitization and direct tranching, the attachment point for a terminal security should add the lower endpoints along the branch. The old expression effectively subtracted the terminal lower endpoint. The corrected expression is
  `sum_{n in b(z)} inf(tau_n) + inf(tau_z)`.

I also made several proof-consistency edits:

- The equilibrium definition now refers consistently to a tranching `T` and tranche prices `p_tau`.
- The fixed-point map `Psi_T` now matches the equilibrium definition.
- The dominance condition is stated for `d phi_tau`-almost every point in a tranche, which is the economically relevant condition for the payoff integral and avoids irrelevant boundary failures.
- Lemma `Urefine` now evaluates refinements at the equilibrium price `q_T`, which is what the proof uses.
- The integration-by-parts step now notes how to handle unbounded tranches by truncating above `max_x q_T(x)`.
- The proof of Lemma `prp:nUcon` was made more transparent, but it remains the part most worth expanding before submission.

No fatal mathematical contradiction was found in the main fixed-point/existence argument. The remaining risk is expositional rigor, not an obvious false theorem.

## Journal recommendations

Best-fit targets:

1. Journal of Economic Theory - good fit if the proof of the issuer-optimal characterization is made fully formal and the novelty over collateral-equilibrium models is sharpened.
2. Review of Finance - plausible finance-theory outlet if the introduction and literature positioning are strengthened.
3. Journal of Financial Intermediation - strong thematic fit because the paper is about securitization, tranching, and intermediation.
4. Economic Theory - good if the paper is positioned as a collateral/security-design theory paper.
5. Games and Economic Behavior - plausible if the emphasis is on heterogeneous beliefs and equilibrium structure rather than crisis finance.

More aspirational:

- Review of Financial Studies, Journal of Finance, or Journal of Financial Economics would require a larger repositioning, a sharper contribution relative to Fostel-Geanakoplos/Simsek/DeMarzo, and probably either a very polished theory innovation or an empirical/calibration component.

Less ideal:

- Journal of Banking and Finance could be a fallback, but the paper should then be made more applied or institutional.

## Other recommendations

- State the contribution in one sentence using the paper's strongest result: waterfall tranching increases asset values exactly when no belief first-order stochastically dominates on the relevant tranche payoffs, and it can worsen realized returns for some agents.
- Rename the existing citation key `EysterPiccione2014` to `EysterPiccione2013` eventually. The metadata already says 2013, so this is not technically broken, but the key is confusing.
- Consider moving old commented blocks out of `main.tex` into an archive file. They do not break the document, but they make maintenance harder.
- Add a short roadmap paragraph before the theorem on issuer-optimal tranching explaining why the stochastic-dominance condition is the right object.
- If targeting a theory journal, expand Lemma `prp:nUcon` into a standalone constructive proof with named subintervals and explicit use of finiteness of `X` and `F`.
- If targeting a finance journal, add a clearer crisis narrative that distinguishes this mechanism from neglected risk, rating arbitrage, and standard collateral leverage.

## Verification

Completed:

- No active duplicate `\label` values.
- No active missing `\ref` or `\eqref` targets.
- No active missing BibTeX entries.
- No remaining active `ectaart`/frontmatter dependencies.

Not completed:

- Full PDF compilation. This machine does not have `pdflatex`, `bibtex`, `xelatex`, `lualatex`, or `tectonic` available, so the final compile test still needs to be run in a LaTeX environment.
