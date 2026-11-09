"""Notebook cell of the reference list that closes the notebook."""

from __future__ import annotations

import nbformat

from .common import md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 参考文献

本文中の（著者, 年）は、次の文献を指す。

- Angrist, J. D., & Pischke, J.-S. (2009). *Mostly Harmless Econometrics: An Empiricist's Companion*. Princeton University Press.
- Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. *Journal of Human Resources*, 50(2), 317–372. https://doi.org/10.3368/jhr.50.2.317
- Cattaneo, M. D., Crump, R. K., Farrell, M. H., & Feng, Y. (2024). On binscatter. *American Economic Review*, 114(5), 1488–1514. https://doi.org/10.1257/aer.20221576
- Csikszentmihalyi, M. (1990). *Flow: The Psychology of Optimal Experience*. Harper & Row.
- Curran, P. J., & Bauer, D. J. (2011). The disaggregation of within-person and between-person effects in longitudinal models of change. *Annual Review of Psychology*, 62, 583–619. https://doi.org/10.1146/annurev.psych.093008.100356
- Deschênes, O., & Greenstone, M. (2011). Climate change, mortality, and adaptation: Evidence from annual fluctuations in weather in the US. *American Economic Journal: Applied Economics*, 3(4), 152–185. https://doi.org/10.1257/app.3.4.152
- Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present*. Arco / Batsford.
- Fieller, E. C. (1954). Some problems in interval estimation. *Journal of the Royal Statistical Society: Series B*, 16(2), 175–185. https://doi.org/10.1111/j.2517-6161.1954.tb00159.x
- Glickman, M. E. (2022). *Example of the Glicko-2 system*（2022年3月22日版）. http://www.glicko.net/glicko/glicko2.pdf
- Haans, R. F. J., Pieters, C., & He, Z.-L. (2016). Thinking about U: Theorizing and testing U- and inverted U-shaped relationships in strategy research. *Strategic Management Journal*, 37(7), 1177–1195. https://doi.org/10.1002/smj.2399
- Ito, R.（伊藤 黎） (2026). AI対戦相手の難易度と再訪：オンラインチェス内のプレイヤー再訪行動の縦断的分析. 人工知能学会研究会資料.
- James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021). *An Introduction to Statistical Learning: With Applications in R* (2nd ed.). Springer. https://doi.org/10.1007/978-1-0716-1418-1
- Lind, J. T., & Mehlum, H. (2010). With or without U? The appropriate test for a U-shaped relationship. *Oxford Bulletin of Economics and Statistics*, 72(1), 109–118. https://doi.org/10.1111/j.1468-0084.2009.00569.x
- Oehlert, G. W. (1992). A note on the delta method. *The American Statistician*, 46(1), 27–29. https://doi.org/10.1080/00031305.1992.10475842
- Royston, P., Altman, D. G., & Sauerbrei, W. (2006). Dichotomizing continuous predictors in multiple regression: A bad idea. *Statistics in Medicine*, 25(1), 127–141. https://doi.org/10.1002/sim.2331
- Simonsohn, U. (2018). Two lines: A valid alternative to the invalid testing of U-shaped relationships with quadratic regressions. *Advances in Methods and Practices in Psychological Science*, 1(4), 538–555. https://doi.org/10.1177/2515245918805755
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953
- Wood, S. N. (2017). *Generalized Additive Models: An Introduction with R* (2nd ed.). Chapman & Hall/CRC. https://doi.org/10.1201/9781315370279
- Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data* (2nd ed.). MIT Press.
""",
    ),
]
"""The cells, in notebook order."""
