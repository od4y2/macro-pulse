# S12 live source verification - payment-outage episodes and China healthcare geography

- Date: 2026-08-29
- Method: every registry entry below was verified against its official
  source document via live web retrieval; quotes are verbatim from the
  documents (Chinese originals). PDF figures were machine-extracted with
  `pypdf` from the official PDFs (extraction output preserved in this
  file). Sources that could NOT be verified are listed at the end and
  are excluded from the registry - no-fabrication discipline.

## A. Payment-outage episodes (all external-labelled, citation-mandatory)

### yn-mi-2024-rollover - 48h year-end suspension

- Source: Kunming Municipal Medical Security Bureau,
  "昆明市医疗保障局关于2024年医保信息平台计息和业务结转工作停机的通告"
  (notice signed 2024-12-26; posted 2024-12-27)
- URL: https://ybj.km.gov.cn/c/2024-12-27/4929546.shtml
- Window (verbatim): "2024年12月31日20:00至2025年1月2日20:00" — "共计停机48小时"
- Reason (verbatim): "为做好医保个人账户年度计息和业务结转工作"， carried
  out "按照云南省医疗保障局统一安排"
- Affected (verbatim): "全市职工基本医疗保险、城乡居民基本医疗保险的所有
  医保业务将暂停办理"… settlement at hospitals and pharmacies plus
  "跨省和省内异地就医医保结算等业务"; "医保码展码、'云南医保'微信/支付宝
  小程序、云南医疗保障公共服务平台网上服务大厅、一部手机办事通医保专区、
  云南省政务服务平台医保相关服务等公共服务渠道"

### yn-mi-2025-rollover - 48h year-end suspension

- Source: Yunnan Provincial Medical Security Bureau,
  "关于2025年云南省医保信息平台计息和业务结转工作停机的公告"
  (signed 云南省医疗保障局 2025年12月23日)
- URL: https://ylbz.yn.gov.cn/index.php?c=show&id=5863
- Window (verbatim): "2025年12月31日20:00至2026年1月2日20:00，共计停机
  时间48小时。"
- Reason: 2025 medical-insurance personal-account annual interest
  crediting and year-end business rollover
- Affected (verbatim): "全省范围内定点医疗机构、定点零售药店无法办理医保联
  网结算"… "跨省及省内异地就医直接结算、医保码展码、'云南医保'微信/支付
  宝小程序/APP、云南省医保公共服务网上服务大厅、一部手机办事通医保专区、
  云南省政务服务平台医保相关服务等将暂停服务"

### yn-mi-2026-03-maintenance - 8h upgrade window

- Source: Yunnan Provincial Medical Security Bureau,
  "云南省医疗保障信息平台升级维护公告" (dated 2026年3月20日)
- URL: https://ylbz.yn.gov.cn/index.php?c=show&id=6072
- Window (verbatim): "2026年3月24日（星期二）22:00至3月25日（星期三）6:00"
  — "共计8小时"
- Reason (verbatim): "为持续完善优化云南省医疗保障信息平台业务功能，
  进一步提升医保服务能力"
- Affected (verbatim): "定点医疗机构、定点零售药店无法办理医保联网结算"…
  "跨省异地及省内异地就医直接结算"… "医保码展码"… "云南医保"微信和支付
  宝小程序… 云南省医保公共服务平台网上服务大厅

### yn-mi-2026-06-maintenance - 2h upgrade window

- Source: Yunnan Provincial Medical Security Bureau,
  "云南省医疗保障信息平台升级维护公告" (dated 2026年6月12日)
- URL: https://ylbz.yn.gov.cn/index.php?c=show&id=6254
- Window (verbatim): "2026年6月12日（星期五）23:00-6月13日（星期六）1:00
  （共计2小时）"
- Reason (verbatim): "为持续完善优化云南省医疗保障信息平台业务功能，
  进一步提升服务能力"
- Affected (verbatim): "云南省医保刷脸结算、医保电子钱包、跨省医保直接结算
  相关等业务将暂停使用" — with in-province offsite direct settlement
  explicitly unaffected

**Registry pattern**: the year-end 48-hour suspension is RECURRING (the
same rollover window each year-end, per provincial unified arrangement).
A 2023-dated notice exists (transmitted by Kunming Medical University,
https://www.kmmc.cn/upload/20231221/2023122109095100.pdf) but the PDF is
a scanned image with no machine-extractable text, so its window could
not be verified verbatim - it is therefore NOT in the registry. Only
machine-verified episodes are recorded.

## B. China healthcare geography records (PDF text extraction)

### National (CHN), 2023 - NHC 2023 statistical bulletin

- Source: National Health Commission (China), "2023年我国卫生健康事业
  发展统计公报" (PDF created 2024-08-26 per document metadata)
- URL: https://www.nhc.gov.cn/wjw/c100178/202408/1de460738f81464280e9ed
  3277630e33/files/1734002454304_67772.pdf
- Extraction (pypdf, verbatim):
  - "2023 年末，全国医疗卫生机构总数 1070785 个" (1,070,785 institutions)
  - "全国医疗卫生机构床位 1017.4[万张]" (10,174,000 beds)
  - "每千人口医疗卫生机构床位数由 2022 年 6.92 张增加到 2023 年 7.23 张。"
    (beds per 1,000 population: 6.92 -> 7.23)
  - "2023 年，每千人口执业（助理）医师 3.40 人" (physicians per 1,000: 3.40)

### Beijing, 2023 - Beijing 2023 health development statistical bulletin

- Source: Beijing Municipal Health Commission, "2023年北京市卫生健康事业
  发展统计公报" (PDF, upload path dated 2024-08-19)
- URL: http://www.phic.org.cn/tjsj/wstjgb/202408/P020240819586687344254.pdf
- Extraction (pypdf, verbatim):
  - "机构数达 12518 家，其中医疗机构 12298 家" (12,518 institutions)
  - "全市医疗机构编制床位总数达 149971 张" (149,971 AUTHORIZED beds)
  - "每千常住人口医疗机构编制床位 6.87 张，每千常住人口医疗机构实有床位
    6.35 张" (6.87 authorized / 6.35 actual beds per 1,000)
  - "实有床位总数达138825 张" (138,825 actual beds)

### Yunnan, 2023 - Yunnan Daily reporting provincial health statistics

- Source: Yunnan Daily, "筑基强本守护人民健康" (2024-09-25)
- URL: https://www.yndaily.com/html/2024/yaowenyunnan_0925/129208.html
- Quote (verbatim): "截至2023年，全省共有医疗卫生机构28765个、医疗卫生
  机构拥有床位数35.99万张" (28,765 institutions; 359,900 beds)
- Note: Yunnan's own 2024 statistical bulletin PDF
  (http://ynswsjkw.yn.gov.cn/.../20251104055541675.pdf) was unreachable
  (SSL handshake failure), so the newspaper-of-record citation is used
  and the at-2024 figures are NOT recorded.

### Payment profile inputs (real, live World Bank API, 2026-08-29)

- `g20.any` (digital payments, % adults): CHN latest 2024 = 88.72
  (n=4 waves); KOR 2021 = 97.94; USA 2021 = 92.97
- `SH.XPD.CHEX.GD.ZS` (health expenditure, % GDP): CHN 2023 = 5.944;
  KOR 2024 = 8.677; USA 2023 = 16.69
- Asymmetry found live: CHN's Findex 2024 wave exists, but health
  expenditure stops at 2023 - a common-period profile (2021) and a
  latest-wave profile (2024, health expenditure named
  `not_observed_at_period`) are BOTH shown in the demo rather than one
  silently picked.

## C. Sources that failed verification (excluded from the registry)

| Intended source | Failure mode | Consequence |
|---|---|---|
| Yunnan 2023 rollover notice (kmmc.cn PDF) | scanned image, no text layer | episode not recorded |
| Gansu health statistics yearbook 2024 (wsjk.gansu.gov.cn) | endpoint returned HTML, not the PDF | Gansu not recorded |
| Anhui 2023 bulletin (Xinhua mirror) | TLS cert mismatch on mirror | Anhui not recorded |
| Yunnan 2024 bulletin (ynswsjkw.yn.gov.cn) | SSL handshake failure | at-2024 Yunnan figures not recorded |

29 of 31 provinces have no verified record and are explicitly listed as
unrecorded by `unrecorded_provinces()` - named missingness, never
imputed.
